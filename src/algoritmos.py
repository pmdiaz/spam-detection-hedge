"""Hedge en sus dos variantes, y el calculo del regret y sus cotas.

La slide 71 define la prediccion por VOTO PESADO DETERMINISTICO, pero la cota de
la slide 73 es la de Hedge, donde la perdida de la ronda es la de la MEZCLA y se
realiza muestreando un experto segun los pesos. No son el mismo algoritmo, y la
diferencia no es de notacion:

  Para un algoritmo deterministico no existe cota de regret sublineal en el peor
  caso. El adversario ve la prediccion antes de fijar la etiqueta, hace errar
  siempre al jugador, y el mejor experto fijo erra la mitad: regret lineal. La
  garantia clasica de Weighted Majority es MULTIPLICATIVA, del orden de
  2,41*(L_best + log2 K), no aditiva.

Por eso corremos las dos variantes y mostramos cual respeta la cota.

Como los expertos son funciones FIJAS (slide 71), sus predicciones sobre todo el
stream se pueden calcular una sola vez. El loop de Hedge queda operando sobre esa
matriz de perdidas, que es lo que hace barato repetir con muchas semillas.
"""

import numpy as np


def matriz_de_perdidas(expertos, textos, etiquetas):
    """Devuelve la matriz de perdidas 0-1 de forma (K expertos, T rondas).

    perdidas[i, t] = 1{f^(i)(x_t) != y_t}, que es la perdida del experto i en la
    ronda t segun la slide 71.
    """
    predicciones = np.array([experto.predecir(textos) for experto in expertos])
    return (predicciones != etiquetas).astype(float), predicciones


def eta_teorico(cantidad_rondas, cantidad_expertos):
    """Tasa de aprendizaje con la que vale la cota de la slide 73."""
    return np.sqrt(8.0 * np.log(cantidad_expertos) / cantidad_rondas)


def correr_hedge(perdidas, predicciones, etiquetas, eta, randomizado, semilla=0):
    """Corre Hedge sobre el stream y devuelve el historial de la corrida.

    Los pesos arrancan UNIFORMES en 1/K (slide 72). No se arrastran del warm-up:
    la cota supone prior uniforme --el termino ln K es en realidad -ln w_1(i) en
    Freund & Schapire-- y arrancar tibio sesgaria hacia los expertos lexicos, que
    son los que mejor andan antes del ataque.

    randomizado=False  -> voto pesado deterministico (slide 71).
    randomizado=True   -> se muestrea un experto I_t ~ w_t y se juega su prediccion,
                          que es la version para la que vale la cota.
    """
    cantidad_expertos, cantidad_rondas = perdidas.shape
    generador = np.random.default_rng(semilla)

    pesos = np.full(cantidad_expertos, 1.0 / cantidad_expertos)

    perdidas_jugador = np.zeros(cantidad_rondas)
    historial_pesos = np.zeros((cantidad_expertos, cantidad_rondas))

    for ronda in range(cantidad_rondas):
        historial_pesos[:, ronda] = pesos

        if randomizado:
            experto_jugado = generador.choice(cantidad_expertos, p=pesos)
            prediccion = predicciones[experto_jugado, ronda]
        else:
            # Voto pesado: se predice spam si la masa de expertos que dice spam
            # supera 1/2.
            voto = float(np.dot(pesos, predicciones[:, ronda]))
            prediccion = 1 if voto > 0.5 else 0

        perdidas_jugador[ronda] = 1.0 if prediccion != etiquetas[ronda] else 0.0

        # Actualizacion multiplicativa de la slide 72, con renormalizacion.
        pesos = pesos * np.exp(-eta * perdidas[:, ronda])
        pesos = pesos / pesos.sum()

    return perdidas_jugador, historial_pesos


def regret_acumulado(perdidas_jugador, perdidas_expertos):
    """R_t en cada ronda, contra el mejor experto fijo EN RETROSPECTIVA.

    El minimo se toma sobre la perdida acumulada al final del stream, no ronda a
    ronda: el mejor experto fijo es uno solo para toda la secuencia.
    """
    acumulada_jugador = np.cumsum(perdidas_jugador)
    acumuladas_expertos = np.cumsum(perdidas_expertos, axis=1)

    indice_mejor = int(np.argmin(acumuladas_expertos[:, -1]))
    return acumulada_jugador - acumuladas_expertos[indice_mejor], indice_mejor


def cota_peor_caso(cantidad_rondas, cantidad_expertos):
    """La cota de la slide 73: sqrt(2 T ln K). Solo crece con el horizonte."""
    return np.sqrt(2.0 * cantidad_rondas * np.log(cantidad_expertos))


def cota_small_loss(perdida_mejor_experto, cantidad_expertos):
    """Cota fina de Freund & Schapire (1997), Lema 4 / ec. 11.

        L_Hedge <= L_best + sqrt(2 * L_best * ln K) + ln K

    Depende de la perdida del mejor experto y no del horizonte, asi que se
    afloja cuando el ataque degrada a los expertos. Es la que puede reproducir
    el escalon del drift.
    """
    logaritmo = np.log(cantidad_expertos)
    return np.sqrt(2.0 * perdida_mejor_experto * logaritmo) + logaritmo


def eta_small_loss(perdida_mejor_experto, cantidad_expertos):
    """Tasa de aprendizaje con la que vale la cota small-loss de F&S.

    Freund & Schapire eligen beta = 1 / (1 + sqrt(2 ln N / L~)), con L~ una cota
    superior conocida de L_best. En terminos de eta = ln(1/beta) queda la
    expresion de abajo.

    OJO: la cota small-loss NO se aplica al eta sintonizado por T. Son dos
    configuraciones distintas del mismo algoritmo y cada cota vale para la suya.
    Usamos el L_best realizado, que es una cota post-hoc y hay que declararlo.
    """
    return np.log(1.0 + np.sqrt(2.0 * np.log(cantidad_expertos) / perdida_mejor_experto))


def construir_secuencia_adversaria(cantidad_rondas, eta):
    """Secuencia que fuerza regret LINEAL al Hedge deterministico.

    Demuestra por que la cota de la slide 73 no puede valer para el algoritmo de
    la slide 71. Dos expertos: uno dice siempre ham, el otro siempre spam.

    El adversario es OBLIVIOUS: fija toda la secuencia de antemano. Puede hacerlo
    porque el jugador es deterministico, asi que sus predicciones se pueden
    simular offline sin haber corrido nada. Ser predecible alcanza para que te
    ganen: no hace falta un adversario que reaccione en vivo.

    Contra el jugador randomizado la misma construccion no funciona, porque el
    adversario no puede anticipar que experto va a salir sorteado.
    """
    predicciones = np.zeros((2, cantidad_rondas), dtype=int)
    predicciones[1, :] = 1  # experto 0 dice siempre ham, experto 1 siempre spam

    etiquetas = np.zeros(cantidad_rondas, dtype=int)
    pesos = np.full(2, 0.5)

    for ronda in range(cantidad_rondas):
        voto = float(np.dot(pesos, predicciones[:, ronda]))
        prediccion_del_jugador = 1 if voto > 0.5 else 0

        # El adversario etiqueta lo contrario de lo que el jugador va a decir.
        etiquetas[ronda] = 1 - prediccion_del_jugador

        perdidas_ronda = (predicciones[:, ronda] != etiquetas[ronda]).astype(float)
        pesos = pesos * np.exp(-eta * perdidas_ronda)
        pesos = pesos / pesos.sum()

    perdidas = (predicciones != etiquetas).astype(float)
    return perdidas, predicciones, etiquetas
