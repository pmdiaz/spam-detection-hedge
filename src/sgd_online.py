"""El competidor que REENTRENA: un unico modelo actualizado en cada ronda.

Es el "remedio" que proponen Lowd & Meek (2005): *"the only remedy we know of is
frequent retraining"*. Frente a Hedge aisla el otro efecto: Hedge combina
expertos congelados sin reentrenar nada; este competidor no combina nada, pero
reentrena. Separar los dos efectos es el aporte central del trabajo (§3 del plan).

Protocolo de la slide 57, en el orden correcto: en cada ronda el modelo PRIMERO
predice x_t, y recien DESPUES ve la etiqueta y_t y se actualiza con ella. Al
reves seria hacer trampa: estaria prediciendo con la respuesta.

Decisiones:
  - Regresion logistica entrenada por SGD (loss="log_loss"), sobre el mismo
    vectorizador de hashing que los expertos lexicos. Puede aprender tokens
    nuevos como "viiagra" porque caen en buckets que antes tenian peso cero.
  - Arranca entrenado sobre el warm-up, igual que los expertos: la comparacion
    tiene que partir del mismo conocimiento.
  - alpha (regularizacion) se elige por CV sobre el warm-up con el mismo
    criterio que los expertos: MCC y regla de un error estandar.
  - Learning rate: el esquema por defecto de scikit-learn ("optimal"), con paso
    1/(alpha*(t+t0)). Se temia que al decaer tardara en reaccionar al drift, pero
    medido fue el mejor: los pasos constantes probados (0.01, 0.1, 1.0) andan
    peor incluso antes del ataque. Usar el default evita una sintonia a mano.
"""

import numpy as np
from sklearn.linear_model import SGDClassifier

from expertos import construir_vectorizador, seleccionar_por_cv

GRILLA_ALPHA = [1e-3, 1e-4, 1e-5, 1e-6]


def _construir_sgd(alpha):
    return SGDClassifier(loss="log_loss", alpha=alpha, max_iter=1000, random_state=0)


def correr_sgd_online(warmup, stream):
    """Devuelve (predicciones sobre el stream, alpha elegido).

    El stream que se pasa es el mismo, ya atacado, que ven los demas
    competidores.
    """
    vectorizador = construir_vectorizador()
    matriz_warmup = vectorizador.transform(warmup["texto"].tolist())
    etiquetas_warmup = warmup["etiqueta"].to_numpy()

    alpha, _ = seleccionar_por_cv(_construir_sgd, GRILLA_ALPHA, matriz_warmup, etiquetas_warmup)

    modelo = _construir_sgd(alpha)
    modelo.fit(matriz_warmup, etiquetas_warmup)

    matriz_stream = vectorizador.transform(stream["texto"].tolist())
    etiquetas_stream = stream["etiqueta"].to_numpy()

    predicciones = np.zeros(len(etiquetas_stream), dtype=int)
    for ronda in range(len(etiquetas_stream)):
        # Primero se predice...
        predicciones[ronda] = modelo.predict(matriz_stream[ronda])[0]
        # ...y recien despues se ve la etiqueta y se actualiza.
        modelo.partial_fit(matriz_stream[ronda], etiquetas_stream[ronda:ronda + 1])

    return predicciones, alpha
