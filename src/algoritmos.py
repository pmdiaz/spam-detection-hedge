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


def sortear_rondas_con_etiqueta(cantidad_rondas, probabilidad_etiqueta, semilla):
    """Decide en que rondas el usuario reporta la etiqueta (variante B, §3).

    Hedge y SGD online usan esta misma funcion con la misma semilla, asi que en
    cada corrida ven EXACTAMENTE las mismas rondas etiquetadas: la comparacion
    entre combinar y reentrenar no depende de a quien le tocaron mas etiquetas.

    Con rho = 1 todas las rondas tienen etiqueta y no se sortea nada.
    """
    if probabilidad_etiqueta >= 1.0:
        return np.ones(cantidad_rondas, dtype=bool)

    generador_etiquetas = np.random.default_rng([semilla, 1])
    return generador_etiquetas.random(cantidad_rondas) < probabilidad_etiqueta


def correr_hedge(perdidas, predicciones, etiquetas, eta, randomizado, semilla=0,
                 probabilidad_etiqueta=1.0):
    """Corre Hedge sobre el stream y devuelve el historial de la corrida.

    Los pesos arrancan UNIFORMES en 1/K (slide 72). No se arrastran del warm-up:
    la cota supone prior uniforme --el termino ln K es en realidad -ln w_1(i) en
    Freund & Schapire-- y arrancar tibio sesgaria hacia los expertos lexicos, que
    son los que mejor andan antes del ataque.

    randomizado=False  -> voto pesado deterministico (slide 71).
    randomizado=True   -> se muestrea un experto I_t ~ w_t y se juega su prediccion,
                          que es la version para la que vale la cota.

    probabilidad_etiqueta (rho) modela la etiqueta escasa (variante B, §3 del
    plan): el usuario reporta cada mensaje con probabilidad rho. En las rondas
    sin etiqueta el jugador igual predice y sufre su perdida real, pero NO puede
    actualizar. En las rondas con etiqueta se usa el estimador insesgado
    perdida/rho, el mismo truco de importance sampling de EXP3 (Auer et al.):
    en esperanza, cada experto recibe la misma actualizacion que con rho = 1.

    El sorteo de que rondas tienen etiqueta usa un generador aparte, para que
    con rho = 1 la corrida sea identica a la version sin etiqueta parcial.
    """
    cantidad_expertos, cantidad_rondas = perdidas.shape
    generador = np.random.default_rng(semilla)
    rondas_con_etiqueta = sortear_rondas_con_etiqueta(
        cantidad_rondas, probabilidad_etiqueta, semilla
    )

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

        # La perdida del jugador se cuenta siempre, haya etiqueta o no.
        perdidas_jugador[ronda] = 1.0 if prediccion != etiquetas[ronda] else 0.0

        if not rondas_con_etiqueta[ronda]:
            continue
        perdidas_estimadas = perdidas[:, ronda] / probabilidad_etiqueta

        # Actualizacion multiplicativa de la slide 72, con renormalizacion.
        pesos = pesos * np.exp(-eta * perdidas_estimadas)
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


def eta_etiqueta_parcial(cantidad_rondas, cantidad_expertos, probabilidad_etiqueta):
    """eta para la variante con etiqueta parcial: el de peor caso escalado por sqrt(rho).

    Con rho = 1 coincide con eta_teorico, asi que el barrido arranca exactamente
    en la configuracion del experimento principal. Achicar eta con rho compensa
    que las perdidas estimadas pueden valer hasta 1/rho.
    """
    return np.sqrt(probabilidad_etiqueta) * eta_teorico(cantidad_rondas, cantidad_expertos)


def cota_etiqueta_parcial(cantidad_rondas, cantidad_expertos, probabilidad_etiqueta, eta):
    """Cota del regret esperado con etiqueta parcial, para un eta dado.

        E[R_T] <= ln K / eta + eta * T / (2 rho)

    Con rho < 1 las perdidas estimadas ya no estan en [0, 1] (pueden valer
    1/rho), asi que la cota de la slide 73 no aplica. Esta es la version basada
    en la varianza del estimador, la misma tecnica de Auer et al. (2002) para
    EXP3: usa e^{-x} <= 1 - x + x^2/2 y que E[perdida_estimada^2] <= 1/rho.

    Optimizada en eta escala como sqrt(T ln K / rho): de ahi la prediccion de
    que el regret crece como 1/sqrt(rho). Con rho = 1 es mas floja que
    sqrt(2 T ln K), porque no aprovecha que las perdidas estan acotadas por 1.
    """
    logaritmo = np.log(cantidad_expertos)
    return logaritmo / eta + eta * cantidad_rondas / (2.0 * probabilidad_etiqueta)
