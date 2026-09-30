"""Metricas de evaluacion.

No reportamos accuracy. En este corpus el 13,40% de los mensajes son spam, asi
que el clasificador trivial que dice "todo es ham" alcanza 86,95% de accuracy
(Almeida et al., Tabla 7, fila trivial rejection) sin hacer nada.

Usamos las tres metricas del paper del dataset:
  - Spam Caught (SC): que fraccion del spam se atrapa.
  - Blocked Hams (BH): que fraccion del correo legitimo se bloquea por error.
  - MCC: coeficiente de correlacion de Matthews, robusto al desbalance.
"""

import numpy as np


def spam_caught(etiquetas, predicciones):
    """Porcentaje del spam real que fue correctamente marcado como spam."""
    es_spam = etiquetas == 1
    if es_spam.sum() == 0:
        return float("nan")
    return 100.0 * (predicciones[es_spam] == 1).sum() / es_spam.sum()


def blocked_hams(etiquetas, predicciones):
    """Porcentaje del correo legitimo que fue bloqueado por error."""
    es_ham = etiquetas == 0
    if es_ham.sum() == 0:
        return float("nan")
    return 100.0 * (predicciones[es_ham] == 1).sum() / es_ham.sum()


def mcc(etiquetas, predicciones):
    """Coeficiente de correlacion de Matthews, entre -1 y +1."""
    verdaderos_positivos = int(((etiquetas == 1) & (predicciones == 1)).sum())
    verdaderos_negativos = int(((etiquetas == 0) & (predicciones == 0)).sum())
    falsos_positivos = int(((etiquetas == 0) & (predicciones == 1)).sum())
    falsos_negativos = int(((etiquetas == 1) & (predicciones == 0)).sum())

    numerador = (verdaderos_positivos * verdaderos_negativos) - (falsos_positivos * falsos_negativos)
    denominador = np.sqrt(
        float(verdaderos_positivos + falsos_positivos)
        * float(verdaderos_positivos + falsos_negativos)
        * float(verdaderos_negativos + falsos_positivos)
        * float(verdaderos_negativos + falsos_negativos)
    )

    if denominador == 0:
        return 0.0
    return numerador / denominador


def accuracy(etiquetas, predicciones):
    """Solo para mostrar que es enganosa. No se reporta en el paper."""
    return 100.0 * (etiquetas == predicciones).mean()
