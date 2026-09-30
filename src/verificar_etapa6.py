"""Verificacion de la etapa 6: barrido de rho (etiqueta parcial).

Criterio del plan (§8): el regret crece al bajar rho, de forma compatible con
1/sqrt(rho).

Pregunta 2 del paper: cuanta etiqueta hace falta. El usuario reporta cada
mensaje con probabilidad rho; en las rondas sin etiqueta nadie actualiza.

Se suma SGD online al barrido porque une las dos preguntas del paper: para
recuperarse, reentrenar tiene que aprender del orden de un peso por token nuevo,
mientras que Hedge solo aprende K = 5 pesos. Con pocas etiquetas lo primero no
alcanza y lo segundo si. Hedge y SGD ven EXACTAMENTE las mismas rondas
etiquetadas en cada semilla (sortear_rondas_con_etiqueta).

Se corre sobre el stream ATACADO del experimento principal, que es donde la
etiqueta importa: sin etiquetas nadie puede enterarse de que el modelo estatico
se rompio.
"""

import numpy as np

from adversario import construir_stream_atacado
from algoritmos import (
    correr_hedge,
    cota_etiqueta_parcial,
    eta_etiqueta_parcial,
    matriz_de_perdidas,
    regret_acumulado,
)
from cache_expertos import obtener_expertos
from estatico import INDICE_MODELO_ESTATICO
from sgd_online import ALPHA_FIJO, correr_sgd_online

SEMILLA = 0
CANTIDAD_SEMILLAS_MUESTREO = 20
VALORES_RHO = [1.0, 0.5, 0.2, 0.05]


def main():
    warmup, stream, expertos = obtener_expertos(semilla=SEMILLA)
    indice_estatico = INDICE_MODELO_ESTATICO
    atacado, indice_inicio = construir_stream_atacado(warmup, stream, semilla=SEMILLA)

    etiquetas = atacado["etiqueta"].to_numpy()
    perdidas, predicciones = matriz_de_perdidas(expertos, atacado["texto"].tolist(), etiquetas)
    cantidad_expertos, cantidad_rondas = perdidas.shape

    perdidas_totales = perdidas.sum(axis=1)
    indice_mejor = int(np.argmin(perdidas_totales))
    errores_estatico = perdidas[indice_estatico, indice_inicio:].sum()
    techo_sin_aprender = perdidas_totales.mean() - perdidas_totales.min()
    alpha_sgd = ALPHA_FIJO

    print(f"Stream atacado: T = {cantidad_rondas}, ataque desde t = {indice_inicio}")
    print(f"Mejor experto fijo en retrospectiva: {expertos[indice_mejor].nombre} "
          f"({perdidas_totales[indice_mejor]:.0f} errores)")
    print(f"Estatico ({expertos[indice_estatico].nombre}): {errores_estatico:.0f} errores "
          f"en la mitad atacada, no depende de rho")
    print(f"Techo de regret si Hedge nunca aprendiera (pesos uniformes): {techo_sin_aprender:.1f}\n")

    print("=== Hedge randomizado ===")
    encabezado = (f"{'rho':>5} {'eta':>8} {'regret':>15} {'cota':>7} "
                  f"{'R/R(1)':>7} {'1/sqrt(rho)':>12}")
    print(encabezado)
    print("-" * len(encabezado))

    regrets_medios = []
    errores_hedge = []
    errores_sgd = []
    for rho in VALORES_RHO:
        eta = eta_etiqueta_parcial(cantidad_rondas, cantidad_expertos, rho)

        regrets = []
        errores_hedge_rho = []
        errores_sgd_rho = []
        for semilla_muestreo in range(CANTIDAD_SEMILLAS_MUESTREO):
            perdidas_jugador, _ = correr_hedge(
                perdidas, predicciones, etiquetas, eta,
                randomizado=True, semilla=semilla_muestreo, probabilidad_etiqueta=rho,
            )
            regret, _ = regret_acumulado(perdidas_jugador, perdidas)
            regrets.append(regret[-1])
            errores_hedge_rho.append(perdidas_jugador[indice_inicio:].sum())

            # SGD online con rho = 1 es deterministico: alcanza con una corrida.
            if rho < 1.0 or semilla_muestreo == 0:
                predicciones_sgd, _ = correr_sgd_online(
                    warmup, atacado, alpha=alpha_sgd,
                    probabilidad_etiqueta=rho, semilla=semilla_muestreo,
                )
                errores_sgd_rho.append(
                    (predicciones_sgd[indice_inicio:] != etiquetas[indice_inicio:]).sum()
                )

        regret_medio = float(np.mean(regrets))
        regrets_medios.append(regret_medio)
        errores_hedge.append((np.mean(errores_hedge_rho), np.std(errores_hedge_rho)))
        errores_sgd.append((np.mean(errores_sgd_rho), np.std(errores_sgd_rho)))
        cota = cota_etiqueta_parcial(cantidad_rondas, cantidad_expertos, rho, eta)

        print(f"{rho:>5} {eta:>8.4f} {regret_medio:>8.1f} +/-{np.std(regrets):<4.1f} {cota:>7.1f} "
              f"{regret_medio / regrets_medios[0]:>7.2f} {1 / np.sqrt(rho):>12.2f}")

    print("\n=== Criterio 1: el regret crece al bajar rho ===")
    crece = all(regrets_medios[i] < regrets_medios[i + 1] for i in range(len(regrets_medios) - 1))
    print(f"  Monotono creciente: {'SI' if crece else 'NO'}")

    print("\n=== Criterio 2: compatible con 1/sqrt(rho) ===")
    print("  Si R ~ rho^p, la teoria predice p = -0.5.")
    pendiente = np.polyfit(np.log(VALORES_RHO), np.log(regrets_medios), 1)[0]
    print(f"  Pendiente ajustada en log-log: p = {pendiente:.2f}")
    print(f"  Con rho chico el regret se acerca al techo de no aprender "
          f"({techo_sin_aprender:.1f}) y satura por debajo de la ley 1/sqrt(rho).")

    print("\n=== Criterio 3: el regret queda bajo su cota en todos los rho ===")
    for rho, regret_medio in zip(VALORES_RHO, regrets_medios):
        eta = eta_etiqueta_parcial(cantidad_rondas, cantidad_expertos, rho)
        cota = cota_etiqueta_parcial(cantidad_rondas, cantidad_expertos, rho, eta)
        print(f"  rho = {rho:<5} regret {regret_medio:>6.1f} <= cota {cota:>6.1f}: "
              f"{'SI' if regret_medio <= cota else 'NO'}")

    print("\n=== Combinar vs. reentrenar con etiqueta escasa ===")
    print("  Errores en la mitad atacada (mismas rondas etiquetadas para ambos)")
    print(f"  {'rho':>5} {'Hedge':>14} {'SGD online':>14} {'estatico':>9}   gana")
    print("  " + "-" * 56)
    for rho, (media_hedge, desvio_hedge), (media_sgd, desvio_sgd) in zip(
        VALORES_RHO, errores_hedge, errores_sgd
    ):
        if media_hedge < media_sgd:
            ganador = "combinar"
        else:
            ganador = "reentrenar"
        print(f"  {rho:>5} {media_hedge:>7.1f} +/-{desvio_hedge:<4.1f} "
              f"{media_sgd:>7.1f} +/-{desvio_sgd:<4.1f} {errores_estatico:>9.0f}   {ganador}")


if __name__ == "__main__":
    main()
