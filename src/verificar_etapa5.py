"""Verificacion de la etapa 5: estatico, Hedge y SGD online sobre la misma secuencia.

Criterio del plan (§8): los tres competidores corren sobre la misma secuencia.

Es la primera vez que los tres se comparan, asi que ademas de verificar el
criterio se reporta la respuesta preliminar a la pregunta 1 del paper, con una
sola semilla: cuanto de la brecha entre el estatico y el reentrenamiento cubre
Hedge sin reentrenar nada.

Configuracion de Hedge segun las recomendaciones de §9: randomizado (el que
tiene garantia) y eta sintonizado por T (el unico que no requiere informacion de
oraculo). El deterministico se reporta al lado.
"""

import hashlib

import numpy as np

from adversario import construir_stream_atacado
from algoritmos import correr_hedge, eta_teorico, matriz_de_perdidas
from cache_expertos import obtener_expertos, obtener_indice_estatico
from metricas import blocked_hams, mcc, spam_caught
from sgd_online import correr_sgd_online

SEMILLA = 0
CANTIDAD_SEMILLAS_MUESTREO = 20
TRAMOS_POST_ATAQUE = [(0, 500), (500, 1000), (1000, None)]


def huella(textos, etiquetas):
    """Hash de la secuencia, para comprobar que todos ven exactamente la misma."""
    contenido = "\n".join(f"{etiqueta}\t{texto}" for texto, etiqueta in zip(textos, etiquetas))
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()[:16]


def predicciones_desde_perdidas(perdidas_jugador, etiquetas):
    """Recupera las predicciones de Hedge a partir de sus perdidas 0-1.

    Si el jugador acerto, predijo la etiqueta; si erro, predijo la contraria.
    """
    predicciones = etiquetas.copy()
    errores = perdidas_jugador == 1
    predicciones[errores] = 1 - etiquetas[errores]
    return predicciones


def resumen(predicciones, etiquetas, indice_inicio):
    """Errores por mitad, metricas de la mitad atacada y SC por tramo post-ataque."""
    primera = slice(0, indice_inicio)
    segunda = slice(indice_inicio, None)

    tramos = []
    for desde, hasta in TRAMOS_POST_ATAQUE:
        fin = None if hasta is None else indice_inicio + hasta
        tramo = slice(indice_inicio + desde, fin)
        tramos.append(spam_caught(etiquetas[tramo], predicciones[tramo]))

    return {
        "errores_primera": int((predicciones[primera] != etiquetas[primera]).sum()),
        "errores_segunda": int((predicciones[segunda] != etiquetas[segunda]).sum()),
        "sc": spam_caught(etiquetas[segunda], predicciones[segunda]),
        "bh": blocked_hams(etiquetas[segunda], predicciones[segunda]),
        "mcc": mcc(etiquetas[segunda], predicciones[segunda]),
        "tramos": tramos,
    }


def promediar(resumenes):
    """Promedia una lista de resumenes (para las semillas de muestreo de Hedge)."""
    promedio = {}
    for clave in ["errores_primera", "errores_segunda", "sc", "bh", "mcc"]:
        promedio[clave] = float(np.mean([r[clave] for r in resumenes]))
    promedio["desvio_segunda"] = float(np.std([r["errores_segunda"] for r in resumenes]))
    promedio["tramos"] = list(np.mean([r["tramos"] for r in resumenes], axis=0))
    return promedio


def main():
    warmup, stream, expertos = obtener_expertos(semilla=SEMILLA)
    indice_estatico = obtener_indice_estatico(semilla=SEMILLA)

    atacado, indice_inicio = construir_stream_atacado(warmup, stream, semilla=SEMILLA)
    textos = atacado["texto"].tolist()
    etiquetas = atacado["etiqueta"].to_numpy()

    print("=== Criterio: los tres competidores ven la misma secuencia ===")
    print(f"  T = {len(etiquetas)} rondas, ataque desde t = {indice_inicio}")
    print(f"  Huella de la secuencia atacada: {huella(textos, etiquetas)}")
    print("  Estatico, Hedge y SGD online se calculan a partir de este mismo DataFrame.\n")

    # --- Estatico: la columna del experto elegido por CV ---
    perdidas, predicciones_expertos = matriz_de_perdidas(expertos, textos, etiquetas)
    predicciones_estatico = predicciones_expertos[indice_estatico]
    resultado_estatico = resumen(predicciones_estatico, etiquetas, indice_inicio)

    # --- Hedge ---
    cantidad_expertos, cantidad_rondas = perdidas.shape
    eta = eta_teorico(cantidad_rondas, cantidad_expertos)

    resumenes_hedge = []
    for semilla_muestreo in range(CANTIDAD_SEMILLAS_MUESTREO):
        perdidas_hedge, _ = correr_hedge(
            perdidas, predicciones_expertos, etiquetas, eta,
            randomizado=True, semilla=semilla_muestreo,
        )
        predicciones_hedge = predicciones_desde_perdidas(perdidas_hedge, etiquetas)
        resumenes_hedge.append(resumen(predicciones_hedge, etiquetas, indice_inicio))
    resultado_hedge = promediar(resumenes_hedge)

    perdidas_deterministico, _ = correr_hedge(
        perdidas, predicciones_expertos, etiquetas, eta, randomizado=False
    )
    resultado_deterministico = resumen(
        predicciones_desde_perdidas(perdidas_deterministico, etiquetas), etiquetas, indice_inicio
    )

    # --- SGD online ---
    predicciones_sgd, alpha_sgd = correr_sgd_online(warmup, atacado)
    resultado_sgd = resumen(predicciones_sgd, etiquetas, indice_inicio)

    print(f"Estatico: {expertos[indice_estatico].nombre} | "
          f"Hedge: eta = {eta:.4f}, {CANTIDAD_SEMILLAS_MUESTREO} semillas de muestreo | "
          f"SGD online: alpha = {alpha_sgd}\n")

    encabezado = (f"{'competidor':<24} {'err 1ra':>8} {'err 2da':>13} {'SC':>7} {'BH':>6} {'MCC':>6}"
                  f"   SC por tramo post-ataque")
    print(encabezado)
    print(f"{'':<24} {'':>8} {'(atacada)':>13} {'':>7} {'':>6} {'':>6}"
          f"   {'0-500':>7} {'500-1000':>9} {'1000-fin':>9}")
    print("-" * (len(encabezado) + 10))

    filas = [
        ("estatico", resultado_estatico, None),
        ("Hedge randomizado", resultado_hedge, resultado_hedge["desvio_segunda"]),
        ("Hedge deterministico", resultado_deterministico, None),
        ("SGD online", resultado_sgd, None),
    ]
    for nombre, resultado, desvio in filas:
        errores_segunda = f"{resultado['errores_segunda']:.0f}"
        if desvio is not None:
            errores_segunda += f" +/-{desvio:.0f}"
        tramos = resultado["tramos"]
        print(f"{nombre:<24} {resultado['errores_primera']:>8.0f} {errores_segunda:>13} "
              f"{resultado['sc']:>6.1f}% {resultado['bh']:>5.1f}% {resultado['mcc']:>6.3f}"
              f"   {tramos[0]:>6.1f}% {tramos[1]:>8.1f}% {tramos[2]:>8.1f}%")

    brecha_total = resultado_estatico["errores_segunda"] - resultado_sgd["errores_segunda"]
    cubierto_por_hedge = resultado_estatico["errores_segunda"] - resultado_hedge["errores_segunda"]

    print("\n=== Respuesta preliminar a la pregunta 1 (una sola semilla) ===")
    print(f"  Brecha estatico -> reentrenar : {brecha_total:.0f} errores en la mitad atacada")
    print(f"  Hedge cubre, sin reentrenar   : {cubierto_por_hedge:.0f} errores "
          f"({100 * cubierto_por_hedge / brecha_total:.0f}% de la brecha)")


if __name__ == "__main__":
    main()
