"""Los cinco expertos base del esquema de Hedge.

La slide 71 define a los expertos como funciones FIJAS f^(1), ..., f^(K) que
predicen en {0,1}. Por eso cada experto se entrena una sola vez sobre el warm-up
y despues queda congelado: Hedge no los modifica, solo cambia cuanto le cree a
cada uno.

Cuatro de los cinco son lexicos (miran las palabras) y por eso el ataque de
ofuscacion los degrada. El quinto usa features estructurales y es inmune al
ataque lexico: sin el, el drift romperia a todos los expertos y la garantia de
Hedge quedaria vacia, porque Hedge solo compite contra el mejor experto fijo.

Preprocesamiento segun Almeida et al. (2011), seccion 3.1: sin stemming, sin
eliminacion de stopwords y sin reduccion de dimensionalidad, porque los mensajes
son muy cortos.
"""

import re
import warnings

import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import make_scorer, matthews_corrcoef
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.tree import DecisionTreeClassifier

# Espacio de hashing amplio para que los tokens ofuscados (v1agra) caigan en
# buckets nuevos y no colisionen con vocabulario legitimo. alternate_sign=False
# porque Naive Bayes multinomial necesita features no negativas.
CANTIDAD_BUCKETS = 2 ** 18


def construir_vectorizador():
    """Vectorizador comun a los expertos lexicos.

    Usamos hashing y no un vocabulario fijo por dos razones: en streaming no se
    puede fijar el vocabulario mirando datos futuros, y los tokens ofuscados
    deben poder aparecer sin romper el vectorizador.
    """
    return HashingVectorizer(
        n_features=CANTIDAD_BUCKETS,
        alternate_sign=False,
        lowercase=True,
    )


def seleccionar_por_cv(construir_modelo, grilla, matriz, etiquetas):
    """Elige un hiperparametro por validacion cruzada SOBRE EL WARM-UP.

    Nunca mira el stream: el stream es la secuencia sobre la que se mide el
    regret y tocarla para elegir hiperparametros seria hacer trampa.

    El scorer es MCC y no accuracy, por el mismo motivo por el que no reportamos
    accuracy: con 13,40% de spam, accuracy premia al clasificador que nunca marca
    nada. Almeida et al. (2011) tambien ordenan sus resultados por MCC.

    Entre valores estadisticamente indistinguibles elegimos el mas regularizado,
    con la regla del error estandar: nos quedamos con el candidato mas
    conservador cuyo puntaje llegue al maximo menos un error estandar. Sin esto,
    en mesetas planas el argmax persigue ruido.

    La grilla se recorre de mas regularizado a menos, asi que alcanza con
    devolver el primero que supera el umbral.
    """
    validacion = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    scorer = make_scorer(matthews_corrcoef)

    promedios = []
    errores_estandar = []
    for valor in grilla:
        # Algunos valores de la grilla (los menos regularizados) no convergen y
        # scikit-learn avisa con un ConvergenceWarning. Son justamente valores
        # que esta seleccion evalua para descartarlos, asi que el aviso es ruido.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ConvergenceWarning)
            puntajes = cross_val_score(
                construir_modelo(valor), matriz, etiquetas, cv=validacion, scoring=scorer
            )
        promedios.append(puntajes.mean())
        errores_estandar.append(puntajes.std() / np.sqrt(len(puntajes)))

    indice_mejor = int(np.argmax(promedios))
    umbral = promedios[indice_mejor] - errores_estandar[indice_mejor]

    for indice, promedio in enumerate(promedios):
        if promedio >= umbral:
            return grilla[indice], promedios[indice]

    return grilla[indice_mejor], promedios[indice_mejor]


class ExpertoLexico:
    """Vectorizador de hashing mas un clasificador de scikit-learn."""

    def __init__(self, nombre, clasificador, construir_modelo=None, grilla=None):
        self.nombre = nombre
        self.clasificador = clasificador
        self.vectorizador = construir_vectorizador()
        # Si se pasan, el hiperparametro se elige por CV sobre el warm-up.
        self.construir_modelo = construir_modelo
        self.grilla = grilla
        self.hiperparametro_elegido = None

    def entrenar(self, textos, etiquetas):
        matriz = self.vectorizador.transform(textos)

        if self.grilla is not None:
            valor, puntaje = seleccionar_por_cv(
                self.construir_modelo, self.grilla, matriz, etiquetas
            )
            self.hiperparametro_elegido = (valor, puntaje)
            self.clasificador = self.construir_modelo(valor)

        self.clasificador.fit(matriz, etiquetas)

    def predecir(self, textos):
        matriz = self.vectorizador.transform(textos)
        return self.clasificador.predict(matriz)


class ExpertoReglas:
    """Reglas por keywords: marca spam si el mensaje contiene varias palabras delatoras.

    La lista de keywords no se elige a mano: se deriva del warm-up tomando los
    tokens con mayor cociente entre su frecuencia en spam y en ham. Una vez
    derivada queda congelada, igual que los demas expertos.
    """

    def __init__(self, cantidad_keywords=40, minimo_apariciones=3, umbral=1):
        self.nombre = "reglas por keywords"
        self.cantidad_keywords = cantidad_keywords
        self.minimo_apariciones = minimo_apariciones
        self.umbral = umbral
        self.keywords = []

    def _tokenizar(self, texto):
        return re.findall(r"[a-z0-9]+", texto.lower())

    def entrenar(self, textos, etiquetas):
        conteo_spam = {}
        conteo_ham = {}

        for texto, etiqueta in zip(textos, etiquetas):
            for token in set(self._tokenizar(texto)):
                if etiqueta == 1:
                    conteo_spam[token] = conteo_spam.get(token, 0) + 1
                else:
                    conteo_ham[token] = conteo_ham.get(token, 0) + 1

        # Cociente spam/ham con suavizado, para no premiar tokens que aparecen
        # una sola vez. Es el mismo criterio que usa un filtro bayesiano simple.
        puntajes = []
        for token, apariciones_spam in conteo_spam.items():
            if apariciones_spam < self.minimo_apariciones:
                continue
            apariciones_ham = conteo_ham.get(token, 0)
            puntaje = apariciones_spam / (apariciones_ham + 1)
            puntajes.append((puntaje, token))

        puntajes.sort(reverse=True)
        self.keywords = [token for _, token in puntajes[: self.cantidad_keywords]]

    def predecir(self, textos):
        predicciones = []
        for texto in textos:
            tokens = set(self._tokenizar(texto))
            encontradas = sum(1 for keyword in self.keywords if keyword in tokens)
            predicciones.append(1 if encontradas >= self.umbral else 0)
        return np.array(predicciones)


class ExpertoEstructural:
    """Usa solo features de FORMATO del mensaje, no que palabras aparecen.

    Version enriquecida. La primera version tenia cinco features (longitud,
    proporcion de digitos, de mayusculas, links y exclamaciones) y alcanzaba
    solo ~30% de Spam Caught. Medido contra el ataque, eso rompia el
    experimento: despues del ataque el estructural seguia siendo peor que el
    modelo estatico danado (222 contra 193 errores en la mitad atacada), asi que
    Hedge nunca le transferia peso y "combinar" no tenia nada que combinar.

    Se agregan cuatro patrones de formato tipicos del spam por SMS:
      - telefonos y codigos cortos ("Call 09061701461", "text to 87121"),
      - simbolos de moneda ("£1000"),
      - tarifas ("150p", "p/msg", "/min"),
      - palabras enteras en mayuscula ("FREE", "WINNER").

    La longitud sigue teniendo respaldo en Almeida et al. (2011), Tabla 2: el
    spam promedia 23,48 tokens y el ham 13,18.

    Declaracion necesaria para el paper: este experto es robusto al ataque en
    buena medida POR CONSTRUCCION, porque la ofuscacion duplica vocales y no
    toca digitos ni simbolos. No es un experto robusto en general, es robusto a
    ESTE ataque. Aun asi no es inmune: la ofuscacion convierte "150p" en "150pp"
    y eso rompe el patron de tarifas.
    """

    def __init__(self):
        self.nombre = "features estructurales"
        self.clasificador = LogisticRegression(max_iter=3000)

    def _extraer_features(self, textos):
        filas = []
        for texto in textos:
            cantidad_caracteres = max(len(texto), 1)
            texto_minusculas = texto.lower()
            palabras = texto.split()

            cantidad_tokens = len(palabras)
            cantidad_digitos = sum(1 for caracter in texto if caracter.isdigit())
            cantidad_mayusculas = sum(1 for caracter in texto if caracter.isupper())
            cantidad_links = len(re.findall(r"http|www\.|\.com|\.co\.uk", texto_minusculas))
            cantidad_exclamaciones = texto.count("!")

            # Telefonos de 10-11 digitos que empiezan con 0, o codigos cortos de 5.
            cantidad_telefonos = len(re.findall(r"\b0\d{9,10}\b|\b\d{5}\b", texto))

            tiene_moneda = 1 if ("£" in texto or "$" in texto or "€" in texto) else 0

            cantidad_tarifas = len(re.findall(r"\b\d+p\b|\bp/?msg|/min", texto_minusculas))

            palabras_en_mayuscula = 0
            for palabra in palabras:
                if len(palabra) > 2 and palabra.isupper():
                    palabras_en_mayuscula += 1

            filas.append([
                cantidad_tokens,
                cantidad_digitos / cantidad_caracteres,
                cantidad_mayusculas / cantidad_caracteres,
                cantidad_links,
                cantidad_exclamaciones,
                cantidad_telefonos,
                tiene_moneda,
                cantidad_tarifas,
                palabras_en_mayuscula,
            ])
        return np.array(filas, dtype=float)

    def entrenar(self, textos, etiquetas):
        self.clasificador.fit(self._extraer_features(textos), etiquetas)

    def predecir(self, textos):
        return self.clasificador.predict(self._extraer_features(textos))


def _construir_naive_bayes(alpha):
    return MultinomialNB(alpha=alpha)


def _construir_regresion_logistica(C):
    return LogisticRegression(max_iter=2000, C=C)


def construir_expertos():
    """Devuelve los cinco expertos sin entrenar, en el orden del plan."""
    # Naive Bayes y la regresion logistica necesitan elegir un hiperparametro,
    # porque sus valores por defecto interactuan mal con el espacio de hashing:
    # con alpha=1 el suavizado de Laplace agrega 2^18 pseudo-conteos contra los
    # ~600 conteos reales del warm-up y el modelo colapsa al prior. El arbol no
    # tiene un parametro sensible a esa escala, asi que va con sus defaults.
    grilla_alpha = [1.0, 0.5, 0.1, 0.05, 0.01, 0.005, 0.001, 0.0001]
    grilla_C = [0.1, 1.0, 5.0, 10.0, 50.0, 100.0, 300.0, 1000.0]

    return [
        ExpertoLexico(
            "naive bayes multinomial",
            MultinomialNB(),
            construir_modelo=_construir_naive_bayes,
            grilla=grilla_alpha,
        ),
        ExpertoLexico(
            "regresion logistica",
            LogisticRegression(max_iter=2000),
            construir_modelo=_construir_regresion_logistica,
            grilla=grilla_C,
        ),
        ExpertoLexico("arbol de decision", DecisionTreeClassifier(random_state=0)),
        ExpertoReglas(),
        ExpertoEstructural(),
    ]


def entrenar_expertos(expertos, warmup):
    """Entrena cada experto sobre el warm-up y los deja congelados."""
    textos = warmup["texto"].tolist()
    etiquetas = warmup["etiqueta"].to_numpy()

    for experto in expertos:
        experto.entrenar(textos, etiquetas)

    return expertos
