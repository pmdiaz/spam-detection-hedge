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
  - alpha (regularizacion) FIJO en 1e-5. Ver abajo por que no se elige por CV.
  - Learning rate: el esquema por defecto de scikit-learn ("optimal"), con paso
    1/(alpha*(t+t0)). Se temia que al decaer tardara en reaccionar al drift, pero
    medido fue el mejor: los pasos constantes probados (0.01, 0.1, 1.0) andan
    peor incluso antes del ataque. Usar el default evita una sintonia a mano.

POR QUE alpha NO SE ELIGE POR CV. La primera version lo elegia como a los
expertos: CV sobre el warm-up, MCC y regla de un error estandar. Con 20 semillas
eso rompio la comparacion. La CV eligio 1e-5 en 11 semillas y ahi SGD cometio
65-83 errores en la mitad atacada; eligio 1e-4 en 8 y ahi cometio 125-153. Las
semillas donde "Hedge le ganaba a reentrenar con todas las etiquetas" eran
exactamente las de alpha = 1e-4.

La CV mide que tan bien clasifica el modelo ANTES del ataque, y ahi 1e-4 y 1e-5
dan casi lo mismo. Lo que importa para este competidor es que tan rapido SE
ADAPTA, y eso la CV no lo puede ver porque en el warm-up no hay drift. Con alpha
mas grande el paso es diez veces mas chico y la penalizacion L2 frena el
aprendizaje de los tokens nuevos. La regla del error estandar empeora las cosas
porque prefiere justamente el modelo mas regularizado: es la regla correcta para
generalizar y la equivocada para un modelo que tiene que adaptarse.

Se fija el valor que eligio la CV en la semilla 0, donde se desarrollo el
diseno; las otras 19 semillas lo evaluan fuera de muestra. Un SGD mal sintonizado
favoreceria injustamente a Hedge: este competidor representa el "reentrenar" de
Lowd & Meek y tiene que ser una version razonable de eso.
"""

import numpy as np
from sklearn.linear_model import SGDClassifier

from algoritmos import sortear_rondas_con_etiqueta
from expertos import construir_vectorizador, seleccionar_por_cv

ALPHA_FIJO = 1e-5
GRILLA_ALPHA = [1e-3, 1e-4, 1e-5, 1e-6]


def _construir_sgd(alpha):
    return SGDClassifier(loss="log_loss", alpha=alpha, max_iter=1000, random_state=0)


def elegir_alpha(warmup):
    """alpha por CV sobre el warm-up (MCC y regla de un error estandar).

    Ya no se usa para correr el competidor (ver ALPHA_FIJO). Se conserva para
    reportar que habria elegido la CV en cada semilla.
    """
    vectorizador = construir_vectorizador()
    matriz_warmup = vectorizador.transform(warmup["texto"].tolist())
    etiquetas_warmup = warmup["etiqueta"].to_numpy()
    alpha, _ = seleccionar_por_cv(_construir_sgd, GRILLA_ALPHA, matriz_warmup, etiquetas_warmup)
    return alpha


def correr_sgd_online(warmup, stream, alpha=None, probabilidad_etiqueta=1.0, semilla=0):
    """Devuelve (predicciones sobre el stream, alpha usado).

    El stream que se pasa es el mismo, ya atacado, que ven los demas
    competidores. Si no se pasa alpha, se usa ALPHA_FIJO.

    Con probabilidad_etiqueta < 1 el modelo solo se actualiza en las rondas en
    que el usuario reporta la etiqueta. Las rondas se sortean con la MISMA
    funcion y semilla que usa Hedge, asi que los dos ven exactamente las mismas
    etiquetas. A diferencia de Hedge, aca no se repondera por 1/rho: un modelo
    que reentrena simplemente aprende de los ejemplos que tiene, que es lo que
    haria un filtro real con los reportes de sus usuarios.
    """
    vectorizador = construir_vectorizador()
    matriz_warmup = vectorizador.transform(warmup["texto"].tolist())
    etiquetas_warmup = warmup["etiqueta"].to_numpy()

    if alpha is None:
        alpha = ALPHA_FIJO

    modelo = _construir_sgd(alpha)
    modelo.fit(matriz_warmup, etiquetas_warmup)

    matriz_stream = vectorizador.transform(stream["texto"].tolist())
    etiquetas_stream = stream["etiqueta"].to_numpy()
    rondas_con_etiqueta = sortear_rondas_con_etiqueta(
        len(etiquetas_stream), probabilidad_etiqueta, semilla
    )

    predicciones = np.zeros(len(etiquetas_stream), dtype=int)
    for ronda in range(len(etiquetas_stream)):
        # Primero se predice...
        predicciones[ronda] = modelo.predict(matriz_stream[ronda])[0]
        # ...y recien despues, si el usuario reporto la etiqueta, se actualiza.
        if rondas_con_etiqueta[ronda]:
            modelo.partial_fit(matriz_stream[ronda], etiquetas_stream[ronda:ronda + 1])

    return predicciones, alpha
