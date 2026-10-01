"""Prueba de robustez: ¿SGD pierde con etiqueta escasa por no reponderar por 1/rho?

Surgio de una revision del paper. Hedge usa el estimador insesgado perdida/rho
en las rondas etiquetadas; SGD online, en cambio, aprende de los ejemplos que
tiene sin reponderar (sgd_online.py). La objecion: con rho = 0,05, SGD da pasos
veinte veces menos frecuentes, y su desventaja podria ser un artefacto de no
compensarlo.

Se corre SGD online con tres ponderaciones de cada ejemplo etiquetado (1, que
es la del experimento; 1/sqrt(rho); y 1/rho) sobre las MISMAS rondas
etiquetadas que vio Hedge en experimento.py (semillas de muestreo 0 a 4), para
las 20 semillas de permutacion. Con ponderacion 1 tiene que reproducir
exactamente los errores de SGD del experimento: es el control.

Resultado: reponderar empeora a SGD. Para Hedge el estimador perdida/rho hace
falta para que la COMPARACION entre expertos no tenga sesgo; para SGD
multiplicar el peso solo agranda los pasos, y con tan pocos ejemplos sobreajusta
cada uno. Sin reponderar es la mejor de las tres: el experimento le da a
"reentrenar" su mejor version.

Requiere haber corrido experimento.py (usa el cache de expertos y los json de
las semillas). Guarda resultados/reponderacion_sgd.json.
"""

import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from sklearn.linear_model import SGDClassifier

from adversario import construir_stream_atacado
from algoritmos import sortear_rondas_con_etiqueta
from cache_expertos import obtener_expertos
from expertos import construir_vectorizador
from sgd_online import ALPHA_FIJO

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_SEMILLAS = RAIZ / "resultados" / "semillas"
ARCHIVO_SALIDA = RAIZ / "resultados" / "reponderacion_sgd.json"

SEMILLAS = list(range(20))
SEMILLAS_MUESTREO = [0, 1, 2, 3, 4]  # las mismas del barrido de rho en experimento.py
VALORES_RHO = [0.2, 0.05]
PONDERACIONES = ["1", "1/sqrt(rho)", "1/rho"]
CANTIDAD_PROCESOS = 6


def peso_del_ejemplo(ponderacion, rho):
    if ponderacion == "1":
        return 1.0
    if ponderacion == "1/sqrt(rho)":
        return 1.0 / np.sqrt(rho)
    return 1.0 / rho


def correr_sgd_ponderado(matriz_warmup, etiquetas_warmup, matriz, etiquetas, rho, semilla_muestreo, peso):
    """Igual que correr_sgd_online, pero con un peso fijo para cada ejemplo etiquetado."""
    modelo = SGDClassifier(loss="log_loss", alpha=ALPHA_FIJO, max_iter=1000, random_state=0)
    modelo.fit(matriz_warmup, etiquetas_warmup)
    con_etiqueta = sortear_rondas_con_etiqueta(len(etiquetas), rho, semilla_muestreo)

    predicciones = np.zeros(len(etiquetas), dtype=int)
    for ronda in range(len(etiquetas)):
        predicciones[ronda] = modelo.predict(matriz[ronda])[0]
        if con_etiqueta[ronda]:
            modelo.partial_fit(matriz[ronda], etiquetas[ronda:ronda + 1], sample_weight=[peso])
    return predicciones


def procesar_semilla(semilla):
    warmup, stream, _ = obtener_expertos(semilla, verboso=False)
    atacado, indice_inicio = construir_stream_atacado(warmup, stream, semilla=semilla)

    vectorizador = construir_vectorizador()
    matriz_warmup = vectorizador.transform(warmup["texto"].tolist())
    etiquetas_warmup = warmup["etiqueta"].to_numpy()
    matriz = vectorizador.transform(atacado["texto"].tolist())
    etiquetas = atacado["etiqueta"].to_numpy()

    resultado = {"semilla": semilla, "sgd": {}, "hedge": {}}
    for rho in VALORES_RHO:
        for ponderacion in PONDERACIONES:
            errores = []
            for semilla_muestreo in SEMILLAS_MUESTREO:
                predicciones = correr_sgd_ponderado(
                    matriz_warmup, etiquetas_warmup, matriz, etiquetas,
                    rho, semilla_muestreo, peso_del_ejemplo(ponderacion, rho),
                )
                errores.append(int((predicciones[indice_inicio:] != etiquetas[indice_inicio:]).sum()))
            resultado["sgd"][f"{rho}|{ponderacion}"] = float(np.mean(errores))

    # Hedge y el estatico se leen del experimento, con las mismas semillas de muestreo.
    experimento = json.loads((DIRECTORIO_SEMILLAS / f"semilla_{semilla}.json").read_text(encoding="utf-8"))
    for fila in experimento["barrido_rho"]:
        if fila["rho"] in VALORES_RHO:
            resultado["hedge"][str(fila["rho"])] = float(np.mean(fila["errores_segunda_hedge"]))
            resultado["sgd_experimento_" + str(fila["rho"])] = float(np.mean(fila["errores_segunda_sgd"]))
    resultado["estatico"] = experimento["estatico"]["errores_segunda"]
    return resultado


def main():
    with ProcessPoolExecutor(max_workers=CANTIDAD_PROCESOS) as ejecutor:
        resultados = list(ejecutor.map(procesar_semilla, SEMILLAS))

    print("Errores en la mitad atacada (media ± desvio entre 20 semillas)\n")
    print(f"{'rho':>5} {'competidor':<26} {'errores':>16} {'gana Hedge en':>14}")
    resumen = {}
    for rho in VALORES_RHO:
        hedge = [r["hedge"][str(rho)] for r in resultados]
        print(f"{rho:>5} {'Hedge':<26} {np.mean(hedge):>8.1f} ± {np.std(hedge):<5.1f}")
        resumen[f"{rho}|hedge"] = [float(np.mean(hedge)), float(np.std(hedge))]
        for ponderacion in PONDERACIONES:
            sgd = [r["sgd"][f"{rho}|{ponderacion}"] for r in resultados]
            gana_hedge = sum(1 for h, g in zip(hedge, sgd) if h < g)
            print(f"{rho:>5} {'SGD, peso ' + ponderacion:<26} {np.mean(sgd):>8.1f} ± {np.std(sgd):<5.1f} "
                  f"{gana_hedge:>8}/20")
            resumen[f"{rho}|sgd|{ponderacion}"] = [float(np.mean(sgd)), float(np.std(sgd)), gana_hedge]

    print("\nControl: con peso 1, SGD tiene que coincidir con el del experimento.")
    for rho in VALORES_RHO:
        propio = [r["sgd"][f"{rho}|1"] for r in resultados]
        del_experimento = [r["sgd_experimento_" + str(rho)] for r in resultados]
        coincide = np.allclose(propio, del_experimento)
        print(f"  rho = {rho}: {'coincide' if coincide else 'NO COINCIDE'} "
              f"({np.mean(propio):.1f} contra {np.mean(del_experimento):.1f})")

    estatico = [r["estatico"] for r in resultados]
    print(f"\nEstatico: {np.mean(estatico):.1f} ± {np.std(estatico):.1f}")
    resumen["estatico"] = [float(np.mean(estatico)), float(np.std(estatico))]

    ARCHIVO_SALIDA.write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(f"Guardado en {ARCHIVO_SALIDA}")


if __name__ == "__main__":
    main()
