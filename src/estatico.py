"""El modelo estatico: el clasificador unico que uno desplegaria.

Es la linea de base del experimento (§3 del plan) y tambien el modelo contra el
que el adversario dirige el ataque.

DECISION: el estatico es Naive Bayes POR DISENO, no por validacion cruzada.

La primera version lo elegia por CV sobre el warm-up. Con 20 semillas, la CV
eligio Naive Bayes en 14 y el experto estructural en 6. En esas 6 el diseno
quedaba incoherente: el adversario arma su ataque con los pesos log-odds de un
filtro bayesiano (adversario.py), asi que no atacaba al modelo desplegado, y el
"estatico" resultaba robusto al ataque por accidente. Fijarlo en Naive Bayes
hace que el estatico sea, siempre, el modelo que el spammer ataca. Tambien es el
filtro que estudian Lowd & Meek (2005).

La seleccion por CV se conserva (seleccionar_modelo_estatico) solo para
reportar que habria elegido un practicante: que en 6 de 20 semillas hubiera
desplegado un modelo robusto por azar es una observacion para la discusion.
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold

from expertos import construir_expertos
from metricas import mcc

# Posicion de Naive Bayes en la lista de construir_expertos().
INDICE_MODELO_ESTATICO = 0


def evaluar_experto_por_cv(indice_experto, textos, etiquetas, cantidad_folds=5):
    """MCC promedio de un experto en validacion cruzada sobre el warm-up.

    Se reconstruye el experto en cada fold para que el entrenamiento no arrastre
    informacion de los folds de validacion.
    """
    validacion = StratifiedKFold(n_splits=cantidad_folds, shuffle=True, random_state=0)
    textos = np.array(textos, dtype=object)

    puntajes = []
    for indices_entrenamiento, indices_validacion in validacion.split(textos, etiquetas):
        experto = construir_expertos()[indice_experto]
        experto.entrenar(
            textos[indices_entrenamiento].tolist(), etiquetas[indices_entrenamiento]
        )
        predicciones = experto.predecir(textos[indices_validacion].tolist())
        puntajes.append(mcc(etiquetas[indices_validacion], predicciones))

    return float(np.mean(puntajes))


def seleccionar_modelo_estatico(warmup):
    """Devuelve (indice, nombre, puntajes) del mejor experto por CV en el warm-up."""
    textos = warmup["texto"].tolist()
    etiquetas = warmup["etiqueta"].to_numpy()

    nombres = [experto.nombre for experto in construir_expertos()]
    puntajes = [
        evaluar_experto_por_cv(indice, textos, etiquetas) for indice in range(len(nombres))
    ]

    indice_mejor = int(np.argmax(puntajes))
    return indice_mejor, nombres[indice_mejor], dict(zip(nombres, puntajes))
