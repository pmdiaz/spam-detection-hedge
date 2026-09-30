"""Seleccion del modelo estatico: el clasificador unico que uno desplegaria.

Es la linea de base del experimento (§3 del plan) y tambien el modelo contra el
que el adversario dirige el ataque. Se elige por validacion cruzada sobre el
warm-up, igual que los hiperparametros: el stream nunca se mira.
"""

import numpy as np
from sklearn.model_selection import StratifiedKFold

from expertos import construir_expertos
from metricas import mcc


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
