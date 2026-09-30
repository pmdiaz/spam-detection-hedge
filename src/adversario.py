"""El adversario: un spammer que adapta sus mensajes para evadir el filtro.

Operacionaliza la slide 67 ("el spammer se adapta a nuestro clasificador"), que
la teorica enuncia sin experimentar. Es un passive good word attack en el sentido
de Lowd & Meek (2005) --el atacante arma la lista sin feedback del filtro--
extendido con ofuscacion lexica, que es lo que ellos dejan como trabajo futuro.

El ataque tiene dos mecanismos y la jerarquia entre ellos es deliberada:

  PRIMARIO   ofuscacion lexica de los tokens mas delatores, duplicando una
             vocal interna (viagra -> viiagra). Preserva el conteo de tokens y
             no introduce digitos. Ver ofuscar_token() para por que NO usamos
             leetspeak, que fue la primera version y contaminaba el experimento.

  SECUNDARIO inyeccion acotada de palabras frecuentes en ham.
             Alarga el mensaje, asi que va topeada.

Por que la ofuscacion es primaria: Lowd & Meek necesitan ~150 palabras para
partir al medio la deteccion, pero eso es en email. Un SMS de este corpus
promedia 23,48 tokens (Almeida et al., Tabla 2); inyectar decenas de palabras lo
llevaria a 50-170 tokens, que no es un SMS plausible. El mensaje atacado quedaria
separable por longitud, lo que arruinaria el realismo y ademas contaminaria al
experto estructural, que mide justamente longitud y proporciones.

Los pesos por token se calculan en espacio de TOKENS y no de buckets de hashing,
porque el ataque necesita strings para reescribir. Es ademas como Lowd & Meek
describen un filtro estadistico: un conjunto de pesos por feature mas un umbral.
"""

import re

import numpy as np

VOCALES = "aeiou"


def tokenizar(texto):
    """Tokenizador simple, coherente con el del experto de reglas."""
    return re.findall(r"[a-z0-9]+", texto.lower())


def calcular_pesos_tokens(textos, etiquetas, suavizado=1.0):
    """Peso log-odds de cada token: positivo indica spam, negativo indica ham.

    Es el peso de un filtro bayesiano, que es como Lowd & Meek (2005) modelan el
    filtro a atacar. Se calcula SOLO sobre el warm-up: el adversario conoce el
    modelo desplegado, no el futuro del stream.
    """
    conteo_spam = {}
    conteo_ham = {}

    for texto, etiqueta in zip(textos, etiquetas):
        for token in tokenizar(texto):
            if etiqueta == 1:
                conteo_spam[token] = conteo_spam.get(token, 0) + 1
            else:
                conteo_ham[token] = conteo_ham.get(token, 0) + 1

    vocabulario = set(conteo_spam) | set(conteo_ham)
    total_spam = sum(conteo_spam.values())
    total_ham = sum(conteo_ham.values())
    tamano_vocabulario = len(vocabulario)

    pesos = {}
    for token in vocabulario:
        probabilidad_spam = (conteo_spam.get(token, 0) + suavizado) / (
            total_spam + suavizado * tamano_vocabulario
        )
        probabilidad_ham = (conteo_ham.get(token, 0) + suavizado) / (
            total_ham + suavizado * tamano_vocabulario
        )
        pesos[token] = np.log(probabilidad_spam / probabilidad_ham)

    return pesos


def tokens_mas_delatores(pesos, cantidad):
    """Los tokens con mayor peso hacia spam: los que el ataque va a ofuscar."""
    ordenados = sorted(pesos.items(), key=lambda par: par[1], reverse=True)
    return [token for token, _ in ordenados[:cantidad]]


def palabras_mas_legitimas(pesos, cantidad, minimo_largo=3):
    """Los tokens con peso mas negativo: las good words que el ataque inyecta.

    Se piden de al menos tres caracteres para que sean palabras y no residuos
    de tokenizacion.
    """
    candidatos = [(peso, token) for token, peso in pesos.items() if len(token) >= minimo_largo]
    candidatos.sort()
    return [token for _, token in candidatos[:cantidad]]


def ofuscar_token(token):
    """Duplica la primera vocal interna del token: viagra -> viiagra.

    POR QUE NO LEETSPEAK. La primera version usaba sustitucion leetspeak
    (a->4, i->1, o->0, e->3, s->5). Medido, ese esquema rompia el experimento:
    al introducir digitos subia la proporcion de digitos del mensaje de 11,5% a
    21,2%, y como en SMS los digitos correlacionan con spam (telefonos, precios,
    codigos), el experto estructural pasaba de 32% a 62% de Spam Caught. El
    ataque, que debia ser puramente lexico, terminaba MEJORANDO al experto que
    es justamente el salvavidas del experimento.

    La duplicacion de vocal logra la misma evasion sin ese efecto lateral:
      - No agrega digitos: la proporcion queda en 11,5%.
      - No cambia el conteo de tokens: sigue siendo un token.
      - Es mas efectiva contra el modelo estatico (55,7% de SC contra 66,1%).

    Es ademas una evasion realista: los spammers escriben "viaagra", "vi agra",
    "v-i-a-g-r-a".
    """
    for posicion, caracter in enumerate(token):
        if posicion > 0 and caracter in VOCALES:
            return token[:posicion] + caracter + token[posicion:]

    # Tokens sin vocal interna (por ejemplo '150' o '500'): se duplica el ultimo
    # caracter, que cumple la misma funcion de cambiar el token sin agregar
    # digitos nuevos ni alterar el conteo.
    return token + token[-1] if token else token


def es_ofuscable(token):
    return ofuscar_token(token) != token


class Adversario:
    """Reescribe mensajes de spam para evadir el filtro estatico.

    Es un adversario OBLIVIOUS: la lista de tokens a ofuscar y las good words se
    fijan de antemano contra el modelo estatico, y no se adaptan a cada
    competidor. Asi los cuatro competidores ven la misma secuencia y el regret
    es comparable entre ellos y contra la cota.
    """

    def __init__(self, tokens_a_ofuscar, palabras_buenas, cantidad_inyectada):
        self.tokens_a_ofuscar = set(tokens_a_ofuscar)
        self.palabras_buenas = list(palabras_buenas)
        self.cantidad_inyectada = cantidad_inyectada

    def atacar_texto(self, texto, generador):
        """Ofusca los tokens delatores y agrega unas pocas good words."""
        def reemplazar(coincidencia):
            palabra = coincidencia.group(0)
            if palabra.lower() in self.tokens_a_ofuscar:
                return ofuscar_token(palabra.lower())
            return palabra

        atacado = re.sub(r"[A-Za-z0-9]+", reemplazar, texto)

        if self.cantidad_inyectada > 0 and self.palabras_buenas:
            elegidas = generador.choice(
                self.palabras_buenas,
                size=min(self.cantidad_inyectada, len(self.palabras_buenas)),
                replace=False,
            )
            atacado = atacado + " " + " ".join(elegidas)

        return atacado

    def atacar_stream(self, stream, indice_inicio, semilla=0):
        """Devuelve una copia del stream con el spam atacado desde indice_inicio.

        El ham no se toca: el adversario controla sus propios mensajes, no los
        de los usuarios legitimos.
        """
        generador = np.random.default_rng(semilla)
        atacado = stream.copy()
        textos = atacado["texto"].tolist()

        for indice in range(indice_inicio, len(atacado)):
            if atacado["etiqueta"].iloc[indice] == 1:
                textos[indice] = self.atacar_texto(textos[indice], generador)

        atacado["texto"] = textos
        return atacado


# Calibracion fijada en la etapa 3 (ver §5 del plan): ofuscacion de los 800
# tokens mas delatores mas una good word inyectada. Lleva el Spam Caught del
# modelo estatico de 86,5% a 38,1% sin violar la restriccion de longitud.
CANTIDAD_TOKENS_OFUSCADOS = 800
CANTIDAD_PALABRAS_INYECTADAS = 1
TAMANO_LISTA_PALABRAS_BUENAS = 200


def construir_stream_atacado(warmup, stream, semilla):
    """Arma el adversario calibrado sobre el warm-up y ataca la segunda mitad.

    Es la UNICA secuencia que ven todos los competidores: estatico, Hedge y SGD
    online reciben exactamente este mismo DataFrame. Eso es lo que hace
    comparable el regret entre ellos (adversario oblivious, §5).

    Devuelve (stream atacado, indice de la primera ronda atacada).
    """
    pesos = calcular_pesos_tokens(warmup["texto"].tolist(), warmup["etiqueta"].to_numpy())

    adversario = Adversario(
        tokens_mas_delatores(pesos, CANTIDAD_TOKENS_OFUSCADOS),
        palabras_mas_legitimas(pesos, TAMANO_LISTA_PALABRAS_BUENAS),
        CANTIDAD_PALABRAS_INYECTADAS,
    )

    indice_inicio = len(stream) // 2
    atacado = adversario.atacar_stream(stream, indice_inicio, semilla=semilla)
    return atacado, indice_inicio
