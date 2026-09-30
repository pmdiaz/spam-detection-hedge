"""Etapa 7: el experimento completo con 20 semillas de permutacion.

Cada semilla fija un orden distinto del corpus, y con el un warm-up, un stream,
unos expertos entrenados, un modelo estatico y un ataque distintos. Repetir sobre
20 semillas da las bandas de dispersion del paper y cierra dos preguntas que una
sola semilla no puede contestar (§9 del plan):

  - si el modelo estatico sigue siendo Naive Bayes en todas las semillas, y
  - donde esta realmente el cruce entre combinar y reentrenar al bajar rho.

Las semillas son independientes y se corren en paralelo. Cada una guarda su
resultado en resultados/semillas/ apenas termina, asi que si la corrida se
interrumpe, al relanzarla se retoma desde donde quedo.

Por semilla se guardan dos archivos:
  semilla_<s>.json  numeros resumen (tablas del paper)
  semilla_<s>.npz   series temporales (figuras F1, F2 y F3)

Configuracion segun las recomendaciones de §9: Hedge randomizado con eta
sintonizado por T como competidor principal. El deterministico y el eta
small-loss se guardan como referencia.

Dos decisiones que salieron de la primera corrida con 20 semillas (ver los
docstrings de estatico.py y sgd_online.py): el estatico es Naive Bayes por
diseno, y el alpha de SGD online esta fijo en 1e-5. En ambos casos se registra
tambien lo que habria elegido la CV.
"""

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from adversario import construir_stream_atacado
from algoritmos import (
    correr_hedge,
    cota_etiqueta_parcial,
    cota_peor_caso,
    cota_small_loss,
    eta_etiqueta_parcial,
    eta_small_loss,
    eta_teorico,
    matriz_de_perdidas,
    regret_acumulado,
)
from cache_expertos import obtener_expertos, obtener_indice_estatico
from estatico import INDICE_MODELO_ESTATICO
from metricas import blocked_hams, mcc, spam_caught
from sgd_online import ALPHA_FIJO, correr_sgd_online, elegir_alpha

SEMILLAS = list(range(20))
SEMILLAS_MUESTREO_PRINCIPAL = 20
SEMILLAS_MUESTREO_RHO = 5
VALORES_RHO = [1.0, 0.5, 0.2, 0.05]
CANTIDAD_PROCESOS = 6

DIRECTORIO_RESULTADOS = Path(__file__).resolve().parent.parent / "resultados" / "semillas"


def predicciones_desde_perdidas(perdidas_jugador, etiquetas):
    """Si el jugador acerto, predijo la etiqueta; si erro, la contraria."""
    predicciones = etiquetas.copy()
    errores = perdidas_jugador == 1
    predicciones[errores] = 1 - etiquetas[errores]
    return predicciones


def metricas_por_mitad(predicciones, etiquetas, indice_inicio):
    """Errores de cada mitad y SC, BH y MCC de la mitad atacada."""
    primera = slice(0, indice_inicio)
    segunda = slice(indice_inicio, None)
    return {
        "errores_primera": int((predicciones[primera] != etiquetas[primera]).sum()),
        "errores_segunda": int((predicciones[segunda] != etiquetas[segunda]).sum()),
        "sc_segunda": float(spam_caught(etiquetas[segunda], predicciones[segunda])),
        "bh_segunda": float(blocked_hams(etiquetas[segunda], predicciones[segunda])),
        "mcc_segunda": float(mcc(etiquetas[segunda], predicciones[segunda])),
    }


def promediar_metricas(lista):
    """Promedio de una lista de diccionarios de metricas_por_mitad."""
    promedio = {}
    for clave in lista[0]:
        promedio[clave] = float(np.mean([elemento[clave] for elemento in lista]))
    return promedio


def procesar_semilla(semilla):
    """Corre todo el experimento para una semilla de permutacion y lo guarda."""
    archivo_json = DIRECTORIO_RESULTADOS / f"semilla_{semilla}.json"
    archivo_npz = DIRECTORIO_RESULTADOS / f"semilla_{semilla}.npz"
    if archivo_json.exists() and archivo_npz.exists():
        return semilla, "ya estaba"

    inicio = time.time()

    warmup, stream, expertos = obtener_expertos(semilla, verboso=False)
    atacado, indice_inicio = construir_stream_atacado(warmup, stream, semilla=semilla)

    # El estatico es Naive Bayes por diseno (estatico.py). Lo que habria elegido
    # la CV se registra solo para reportarlo.
    indice_estatico = INDICE_MODELO_ESTATICO
    indice_estatico_cv = obtener_indice_estatico(semilla, verboso=False)

    etiquetas = atacado["etiqueta"].to_numpy()
    perdidas, predicciones = matriz_de_perdidas(expertos, atacado["texto"].tolist(), etiquetas)
    cantidad_expertos, cantidad_rondas = perdidas.shape

    perdidas_totales = perdidas.sum(axis=1)
    indice_mejor = int(np.argmin(perdidas_totales))
    perdida_mejor = float(perdidas_totales[indice_mejor])

    resultado = {
        "semilla": semilla,
        "cantidad_rondas": cantidad_rondas,
        "indice_inicio": indice_inicio,
        "expertos": [experto.nombre for experto in expertos],
        "indice_estatico": indice_estatico,
        "indice_estatico_cv": indice_estatico_cv,
        "indice_mejor_experto": indice_mejor,
        "errores_expertos_primera": perdidas[:, :indice_inicio].sum(axis=1).tolist(),
        "errores_expertos_segunda": perdidas[:, indice_inicio:].sum(axis=1).tolist(),
    }

    # --- Estatico ---
    predicciones_estatico = predicciones[indice_estatico]
    resultado["estatico"] = metricas_por_mitad(predicciones_estatico, etiquetas, indice_inicio)

    # --- Hedge randomizado, eta de peor caso (competidor principal) ---
    eta_peor_caso = eta_teorico(cantidad_rondas, cantidad_expertos)
    metricas_hedge = []
    regrets_hedge = []
    suma_errores_por_ronda = np.zeros(cantidad_rondas)
    suma_pesos = np.zeros((cantidad_expertos, cantidad_rondas))
    for semilla_muestreo in range(SEMILLAS_MUESTREO_PRINCIPAL):
        perdidas_jugador, historial_pesos = correr_hedge(
            perdidas, predicciones, etiquetas, eta_peor_caso,
            randomizado=True, semilla=semilla_muestreo,
        )
        prediccion_hedge = predicciones_desde_perdidas(perdidas_jugador, etiquetas)
        metricas_hedge.append(metricas_por_mitad(prediccion_hedge, etiquetas, indice_inicio))
        regret, _ = regret_acumulado(perdidas_jugador, perdidas)
        regrets_hedge.append(regret)
        suma_errores_por_ronda += perdidas_jugador
        suma_pesos += historial_pesos

    resultado["hedge"] = promediar_metricas(metricas_hedge)
    resultado["hedge"]["desvio_errores_segunda"] = float(
        np.std([m["errores_segunda"] for m in metricas_hedge])
    )
    regret_peor_caso_medio = np.mean(regrets_hedge, axis=0)

    # --- Hedge randomizado, eta small-loss (referencia de oraculo para F3) ---
    eta_oraculo = eta_small_loss(perdida_mejor, cantidad_expertos)
    regrets_oraculo = []
    for semilla_muestreo in range(SEMILLAS_MUESTREO_PRINCIPAL):
        perdidas_jugador, _ = correr_hedge(
            perdidas, predicciones, etiquetas, eta_oraculo,
            randomizado=True, semilla=semilla_muestreo,
        )
        regret, _ = regret_acumulado(perdidas_jugador, perdidas)
        regrets_oraculo.append(regret)
    regret_oraculo_medio = np.mean(regrets_oraculo, axis=0)

    # --- Hedge deterministico ---
    perdidas_deterministico, _ = correr_hedge(
        perdidas, predicciones, etiquetas, eta_peor_caso, randomizado=False
    )
    resultado["hedge_deterministico"] = metricas_por_mitad(
        predicciones_desde_perdidas(perdidas_deterministico, etiquetas), etiquetas, indice_inicio
    )
    regret_deterministico, _ = regret_acumulado(perdidas_deterministico, perdidas)

    resultado["regret"] = {
        "perdida_mejor_experto": perdida_mejor,
        "eta_peor_caso": float(eta_peor_caso),
        "eta_small_loss": float(eta_oraculo),
        "hedge_peor_caso": float(regret_peor_caso_medio[-1]),
        "hedge_small_loss": float(regret_oraculo_medio[-1]),
        "hedge_deterministico": float(regret_deterministico[-1]),
        "cota_peor_caso": float(cota_peor_caso(cantidad_rondas, cantidad_expertos)),
        "cota_small_loss": float(cota_small_loss(perdida_mejor, cantidad_expertos)),
    }

    # --- SGD online con todas las etiquetas ---
    # alpha fijo (sgd_online.py); lo que habria elegido la CV se registra aparte.
    alpha_sgd = ALPHA_FIJO
    predicciones_sgd, _ = correr_sgd_online(warmup, atacado, alpha=alpha_sgd)
    resultado["alpha_sgd"] = alpha_sgd
    resultado["alpha_sgd_cv"] = elegir_alpha(warmup)
    resultado["sgd"] = metricas_por_mitad(predicciones_sgd, etiquetas, indice_inicio)

    # --- Barrido de rho: Hedge y SGD con las mismas rondas etiquetadas ---
    barrido = []
    for rho in VALORES_RHO:
        eta_rho = eta_etiqueta_parcial(cantidad_rondas, cantidad_expertos, rho)
        regrets_rho = []
        errores_hedge_rho = []
        errores_sgd_rho = []
        for semilla_muestreo in range(SEMILLAS_MUESTREO_RHO):
            perdidas_jugador, _ = correr_hedge(
                perdidas, predicciones, etiquetas, eta_rho,
                randomizado=True, semilla=semilla_muestreo, probabilidad_etiqueta=rho,
            )
            regret, _ = regret_acumulado(perdidas_jugador, perdidas)
            regrets_rho.append(float(regret[-1]))
            errores_hedge_rho.append(float(perdidas_jugador[indice_inicio:].sum()))

            if rho >= 1.0:
                prediccion_sgd_rho = predicciones_sgd
            else:
                prediccion_sgd_rho, _ = correr_sgd_online(
                    warmup, atacado, alpha=alpha_sgd,
                    probabilidad_etiqueta=rho, semilla=semilla_muestreo,
                )
            errores_sgd_rho.append(
                float((prediccion_sgd_rho[indice_inicio:] != etiquetas[indice_inicio:]).sum())
            )

        barrido.append({
            "rho": rho,
            "eta": float(eta_rho),
            "regret_hedge": regrets_rho,
            "cota_hedge": float(cota_etiqueta_parcial(cantidad_rondas, cantidad_expertos, rho, eta_rho)),
            "errores_segunda_hedge": errores_hedge_rho,
            "errores_segunda_sgd": errores_sgd_rho,
        })
    resultado["barrido_rho"] = barrido
    resultado["segundos"] = round(time.time() - inicio, 1)

    DIRECTORIO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        archivo_npz,
        etiquetas=etiquetas.astype(np.int8),
        perdidas_expertos=perdidas.astype(np.int8),
        prediccion_estatico=predicciones_estatico.astype(np.int8),
        prediccion_sgd=predicciones_sgd.astype(np.int8),
        error_hedge_medio=(suma_errores_por_ronda / SEMILLAS_MUESTREO_PRINCIPAL).astype(np.float32),
        pesos_hedge_medio=(suma_pesos / SEMILLAS_MUESTREO_PRINCIPAL).astype(np.float32),
        regret_hedge_peor_caso=regret_peor_caso_medio.astype(np.float32),
        regret_hedge_small_loss=regret_oraculo_medio.astype(np.float32),
        regret_hedge_deterministico=regret_deterministico.astype(np.float32),
    )
    # El json se escribe al final: su existencia marca que la semilla esta completa.
    archivo_json.write_text(json.dumps(resultado, indent=2), encoding="utf-8")

    return semilla, f"{resultado['segundos']:.0f}s"


def main():
    semillas = SEMILLAS
    if len(sys.argv) > 1:
        semillas = [int(valor) for valor in sys.argv[1:]]

    DIRECTORIO_RESULTADOS.mkdir(parents=True, exist_ok=True)
    print(f"Corriendo {len(semillas)} semillas con {CANTIDAD_PROCESOS} procesos...", flush=True)
    inicio = time.time()

    with ProcessPoolExecutor(max_workers=CANTIDAD_PROCESOS) as ejecutor:
        futuros = [ejecutor.submit(procesar_semilla, semilla) for semilla in semillas]
        completadas = 0
        for futuro in as_completed(futuros):
            semilla, estado = futuro.result()
            completadas += 1
            minutos = (time.time() - inicio) / 60
            print(f"  semilla {semilla:>2} lista ({estado})  "
                  f"[{completadas}/{len(semillas)}, {minutos:.1f} min]", flush=True)

    print(f"Terminado en {(time.time() - inicio) / 60:.1f} minutos.", flush=True)


if __name__ == "__main__":
    main()
