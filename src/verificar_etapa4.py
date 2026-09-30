"""Verificacion de la etapa 4: Hedge deterministico y randomizado.

Criterio del plan (§8): sin ataque, el regret del randomizado crece
sublinealmente y queda bajo ambas cotas.

Dos aclaraciones que surgieron al implementar:

1. CADA COTA VALE PARA SU PROPIO ETA. La cota de peor caso sqrt(2 T ln K) es
   para eta = sqrt(8 ln K / T). La cota small-loss de Freund & Schapire es para
   beta = 1/(1 + sqrt(2 ln N / L~)). Son dos configuraciones del mismo
   algoritmo, y exigirle a una el cumplimiento de la cota de la otra es un error.

2. LA BRECHA DETERMINISTICO/RANDOMIZADO NO SE VE EN ESTE STREAM. El ataque de
   spam esta dirigido al modelo estatico, no al jugador, asi que no explota que
   el jugador sea predecible. Para mostrar el punto hace falta una construccion
   dirigida, que va al final de este script.
"""

import numpy as np

from algoritmos import (
    construir_secuencia_adversaria,
    correr_hedge,
    cota_peor_caso,
    cota_small_loss,
    eta_small_loss,
    eta_teorico,
    matriz_de_perdidas,
    regret_acumulado,
)
from cache_expertos import obtener_expertos

CANTIDAD_SEMILLAS_MUESTREO = 20


def correr_variantes(perdidas, predicciones, etiquetas, eta):
    """Devuelve (regret determinista, media y desvio del randomizado)."""
    perdidas_determinista, _ = correr_hedge(
        perdidas, predicciones, etiquetas, eta, randomizado=False
    )
    regret_determinista, indice_mejor = regret_acumulado(perdidas_determinista, perdidas)

    regrets = []
    for semilla in range(CANTIDAD_SEMILLAS_MUESTREO):
        perdidas_random, _ = correr_hedge(
            perdidas, predicciones, etiquetas, eta, randomizado=True, semilla=semilla
        )
        regret_random, _ = regret_acumulado(perdidas_random, perdidas)
        regrets.append(regret_random)

    regrets = np.array(regrets)
    return regret_determinista, regrets.mean(axis=0), regrets.std(axis=0), indice_mejor


def main():
    warmup, stream, expertos = obtener_expertos(semilla=0)

    etiquetas = stream["etiqueta"].to_numpy()
    perdidas, predicciones = matriz_de_perdidas(expertos, stream["texto"].tolist(), etiquetas)
    cantidad_expertos, cantidad_rondas = perdidas.shape

    perdidas_acumuladas = perdidas.sum(axis=1)
    perdida_mejor = perdidas_acumuladas.min()
    indice_mejor = int(np.argmin(perdidas_acumuladas))

    print(f"K = {cantidad_expertos} expertos, T = {cantidad_rondas} rondas (stream SIN ataque)")
    print("\nErrores totales de cada experto:")
    for indice, experto in enumerate(expertos):
        marca = "  <- mejor experto fijo" if indice == indice_mejor else ""
        print(f"  {experto.nombre:<26} {perdidas_acumuladas[indice]:>6.0f}{marca}")

    eta_por_horizonte = eta_teorico(cantidad_rondas, cantidad_expertos)
    eta_por_perdida = eta_small_loss(perdida_mejor, cantidad_expertos)
    cota_pc = cota_peor_caso(cantidad_rondas, cantidad_expertos)
    cota_sl = cota_small_loss(perdida_mejor, cantidad_expertos)

    print(f"\n{'configuracion':<34} {'eta':>8} {'R det.':>9} {'R rand.':>16} {'su cota':>9}")
    print("-" * 80)

    resultados = {}
    for nombre, eta, cota in [
        ("sintonizado por T (peor caso)", eta_por_horizonte, cota_pc),
        ("sintonizado por L_best (small-loss)", eta_por_perdida, cota_sl),
    ]:
        determinista, media, desvio, _ = correr_variantes(
            perdidas, predicciones, etiquetas, eta
        )
        resultados[nombre] = (determinista[-1], media, desvio, cota)
        print(f"{nombre:<34} {eta:>8.4f} {determinista[-1]:>9.1f} "
              f"{media[-1]:>9.1f} +/-{desvio[-1]:<4.1f} {cota:>9.1f}")

    print("\n=== Criterio: el randomizado queda bajo SU cota ===")
    for nombre, (_, media, _, cota) in resultados.items():
        print(f"  {nombre:<34} {'SI' if media[-1] <= cota else 'NO'}")

    print("\n=== Criterio: el regret crece sublinealmente ===")
    media = resultados["sintonizado por T (peor caso)"][1]
    print(f"  {'T parcial':>10} {'regret':>9} {'regret/T':>10}")
    for fraccion in [0.25, 0.5, 0.75, 1.0]:
        indice = int(cantidad_rondas * fraccion) - 1
        print(f"  {indice + 1:>10} {media[indice]:>9.1f} {media[indice] / (indice + 1):>10.4f}")

    indices = np.arange(int(cantidad_rondas * 0.1), cantidad_rondas)
    valores = media[indices]
    positivos = valores > 0
    exponente = np.polyfit(np.log(indices[positivos] + 1), np.log(valores[positivos]), 1)[0]
    print(f"\n  Exponente ajustado R_T ~ T^p : p = {exponente:.3f}  (sublineal si p < 1)")

    print("\n=== Deterministico vs randomizado EN ESTE STREAM ===")
    determinista_T = resultados["sintonizado por T (peor caso)"][0]
    print(f"  Regret del deterministico: {determinista_T:.1f}")
    print("  Es NEGATIVO: el voto pesado le gana al mejor experto individual, como")
    print("  cualquier ensamble sobre una secuencia benigna. No contradice nada: la")
    print("  garantia es sobre el peor caso, no sobre esta secuencia en particular.")

    print("\n=== La construccion que si exhibe la brecha ===")
    print("  Adversario oblivious que simula offline al jugador deterministico y")
    print("  etiqueta lo contrario. Puede hacerlo porque el jugador es predecible.")
    print(f"\n  {'T':>7} {'R det.':>9} {'R det./T':>10} {'R rand.':>9} {'cota':>8}")
    print("  " + "-" * 46)
    for horizonte in [500, 1000, 2000, 4000, 8000]:
        eta = eta_teorico(horizonte, 2)
        perdidas_adv, predicciones_adv, etiquetas_adv = construir_secuencia_adversaria(
            horizonte, eta
        )
        determinista, media_adv, _, _ = correr_variantes(
            perdidas_adv, predicciones_adv, etiquetas_adv, eta
        )
        print(f"  {horizonte:>7} {determinista[-1]:>9.0f} {determinista[-1] / horizonte:>10.3f} "
              f"{media_adv[-1]:>9.1f} {cota_peor_caso(horizonte, 2):>8.1f}")
    print("\n  El deterministico tiene regret T/2: LINEAL, y viola la cota por lejos.")
    print("  El randomizado se mantiene sublineal y bajo la cota.")


if __name__ == "__main__":
    main()
