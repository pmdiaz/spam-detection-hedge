"""Etapa 10: Jev como sexto experto, sobre exactamente el mismo experimento.

Reutiliza sin tocar nada el corpus, las semillas, los cinco expertos cacheados,
el adversario calibrado contra Naive Bayes, Hedge y SGD online. Lo unico nuevo
es un experto mas, Jev, que es zero-shot: no ve el warm-up ni el ataque.

Cuatro preguntas, cada una con su panel en el dashboard:

  P1. ¿El ataque que tumba a Naive Bayes tumba tambien a Jev? Es un ataque
      dirigido contra el vocabulario de ESTE corpus; Jev no lo comparte.
  P2. ¿Que hace Hedge con un sexto experto asi? Cuanto peso se lleva, cuan
      rapido despues del ataque, y si "combinar" alcanza ahora a "reentrenar".
  P3. ¿Las probabilidades de Jev estan calibradas, antes y despues del ataque?
      El fabricante dice que si; aca se mide con un diagrama de confiabilidad.
  P4. Etiquetado guiado. El trabajo midio que pasa cuando el usuario reporta
      cada mensaje al azar con probabilidad rho. Con un experto calibrado se
      puede pedir la etiqueta donde Jev duda. Con el MISMO presupuesto rho:
      ¿baja el error?

DECISION en P4: la politica guiada pide la etiqueta de la ronda t con
probabilidad q_t = q_min + c * u_t, con u_t = 1 - |2 p_t - 1| la duda de Jev
(1 en p = 0,5, 0 en p = 0 o 1). c se ajusta para que la media de q_t sea rho:
mismo presupuesto esperado que la politica al azar. q_t se decide ANTES de ver
la etiqueta, con informacion que el filtro tiene en ese momento. Hedge usa el
estimador perdida / q_t, que sigue siendo insesgado (Auer et al., 2002), y el
piso q_min = rho / 4 acota su varianza en 4 / rho. SGD no repondera, igual que
en sgd_online.py.

Uso:
  python experimento_jev.py                  20 semillas, Jev real (TYPESAFE_API_KEY)
  python experimento_jev.py --semillas 0 1   solo esas semillas
  python experimento_jev.py --simular        Jev FALSO, solo para probar el pipeline
"""

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from adversario import construir_stream_atacado
from algoritmos import (
    cota_peor_caso,
    eta_etiqueta_parcial,
    eta_teorico,
    matriz_de_perdidas,
    regret_acumulado,
    sortear_rondas_con_etiqueta,
)
from cache_expertos import obtener_expertos
from datos import cargar_corpus, dividir_warmup_y_stream
from estatico import INDICE_MODELO_ESTATICO
from experto_jev import DIRECTORIO_JEV, MODELO, CacheJev, ExpertoJev, completar_cache
from expertos import construir_vectorizador
from metricas import blocked_hams, mcc, spam_caught
from sgd_online import ALPHA_FIJO, _construir_sgd, correr_sgd_online

SEMILLAS = list(range(20))
SEMILLAS_MUESTREO = 20
SEMILLAS_MUESTREO_PRESUPUESTO = 5
SEMILLAS_MUESTREO_SGD = 2
VALORES_RHO = [0.5, 0.2, 0.1, 0.05]
PUNTOS_CURVA = 160
BINS_HISTOGRAMA = 50
BINS_CALIBRACION = 10


def directorio_semillas(simulado):
    return DIRECTORIO_JEV / ("semillas_SIMULADO" if simulado else "semillas")


# --- Piezas nuevas -------------------------------------------------------------

def correr_hedge_q(perdidas, predicciones, etiquetas, eta, mascara, q, semilla):
    """Hedge randomizado con probabilidad de etiqueta q_t por ronda.

    Con q constante igual a rho y la mascara de sortear_rondas_con_etiqueta es
    exactamente correr_hedge de algoritmos.py; se reescribe solo para aceptar
    un q distinto en cada ronda.
    """
    cantidad_expertos, cantidad_rondas = perdidas.shape
    generador = np.random.default_rng(semilla)
    pesos = np.full(cantidad_expertos, 1.0 / cantidad_expertos)
    perdidas_jugador = np.zeros(cantidad_rondas)
    for ronda in range(cantidad_rondas):
        experto = generador.choice(cantidad_expertos, p=pesos)
        perdidas_jugador[ronda] = float(predicciones[experto, ronda] != etiquetas[ronda])
        if mascara[ronda]:
            pesos = pesos * np.exp(-eta * perdidas[:, ronda] / q[ronda])
            pesos = pesos / pesos.sum()
    return perdidas_jugador


def probabilidades_guiadas(p_jev, rho):
    """q_t = q_min + c * duda_t, con c tal que la media de q_t sea rho."""
    duda = 1.0 - np.abs(2.0 * p_jev - 1.0)
    q_min = rho / 4.0

    def media(c):
        return np.clip(q_min + c * duda, q_min, 1.0).mean()

    bajo, alto = 0.0, 1e4
    for _ in range(80):
        medio = (bajo + alto) / 2
        if media(medio) < rho:
            bajo = medio
        else:
            alto = medio
    return np.clip(q_min + bajo * duda, q_min, 1.0)


def sgd_con_mascara(warmup, stream, mascara):
    """correr_sgd_online, pero con una mascara de rondas etiquetadas arbitraria."""
    vectorizador = construir_vectorizador()
    modelo = _construir_sgd(ALPHA_FIJO)
    modelo.fit(vectorizador.transform(warmup["texto"].tolist()), warmup["etiqueta"].to_numpy())
    matriz = vectorizador.transform(stream["texto"].tolist())
    etiquetas = stream["etiqueta"].to_numpy()
    predicciones = np.zeros(len(etiquetas), dtype=int)
    for ronda in range(len(etiquetas)):
        predicciones[ronda] = modelo.predict(matriz[ronda])[0]
        if mascara[ronda]:
            modelo.partial_fit(matriz[ronda], etiquetas[ronda:ronda + 1])
    return predicciones


def metricas(predicciones, etiquetas, inicio):
    salida = {}
    for nombre, tramo in (("primera", slice(0, inicio)), ("segunda", slice(inicio, None))):
        y, p = etiquetas[tramo], predicciones[tramo]
        salida[nombre] = {
            "errores": int((p != y).sum()),
            "sc": float(spam_caught(y, p)),
            "bh": float(blocked_hams(y, p)),
            "mcc": float(mcc(y, p)),
        }
    return salida


def desde_perdidas(perdidas_jugador, etiquetas):
    predicciones = etiquetas.copy()
    errores = perdidas_jugador == 1
    predicciones[errores] = 1 - etiquetas[errores]
    return predicciones


def submuestrear(serie, indices):
    return np.round(np.asarray(serie)[..., indices], 4).tolist()


def histograma_por_clase(probabilidades, etiquetas):
    bordes = np.linspace(0, 1, BINS_HISTOGRAMA + 1)
    return {
        "spam": np.histogram(probabilidades[etiquetas == 1], bordes)[0].tolist(),
        "ham": np.histogram(probabilidades[etiquetas == 0], bordes)[0].tolist(),
    }


def calibracion(probabilidades, etiquetas):
    indice = np.minimum((probabilidades * BINS_CALIBRACION).astype(int), BINS_CALIBRACION - 1)
    return {
        "n": np.bincount(indice, minlength=BINS_CALIBRACION).tolist(),
        "suma_p": np.round(np.bincount(indice, probabilidades, BINS_CALIBRACION), 4).tolist(),
        "suma_y": np.bincount(indice, etiquetas, BINS_CALIBRACION).astype(int).tolist(),
    }


def palabras_con_cambios(original, atacado):
    """[(palabra, cambio)] alineando por espacios: el ataque no cambia el conteo."""
    a, b = original.split(), atacado.split()
    salida = [[palabra, palabra != (a[i] if i < len(a) else None)] for i, palabra in enumerate(b)]
    return salida


# --- Una semilla ---------------------------------------------------------------

def procesar_semilla(semilla, simulado):
    destino = directorio_semillas(simulado) / f"semilla_{semilla}.json"
    if destino.exists():
        return semilla, "ya estaba"
    inicio_reloj = time.time()

    warmup, stream, expertos = obtener_expertos(semilla, verboso=False)
    atacado, inicio = construir_stream_atacado(warmup, stream, semilla=semilla)
    textos = atacado["texto"].tolist()
    etiquetas = atacado["etiqueta"].to_numpy()
    cantidad_rondas = len(etiquetas)

    jev = ExpertoJev(CacheJev(simulado))
    p_jev = jev.probabilidades(textos)
    todos = expertos + [jev]
    perdidas6, predicciones6 = matriz_de_perdidas(todos, textos, etiquetas)
    perdidas5, predicciones5 = perdidas6[:5], predicciones6[:5]

    naive_bayes = expertos[INDICE_MODELO_ESTATICO]
    p_nb = naive_bayes.clasificador.predict_proba(naive_bayes.vectorizador.transform(textos))[:, 1]

    indices = np.linspace(0, cantidad_rondas - 1, PUNTOS_CURVA).astype(int)
    r = {
        "semilla": semilla, "rondas": cantidad_rondas, "inicio": inicio,
        "expertos": [e.nombre for e in todos],
        "indices_curva": indices.tolist(),
        "errores_expertos": {
            "primera": perdidas6[:, :inicio].sum(axis=1).astype(int).tolist(),
            "segunda": perdidas6[:, inicio:].sum(axis=1).astype(int).tolist(),
        },
    }
    competidores = {}
    acumulados = {}

    # Estatico, Jev solo y SGD con todas las etiquetas.
    for nombre, prediccion in (
        ("estatico", predicciones6[INDICE_MODELO_ESTATICO]),
        ("jev", predicciones6[5]),
    ):
        competidores[nombre] = metricas(prediccion, etiquetas, inicio)
        acumulados[nombre] = np.cumsum(prediccion != etiquetas)
    prediccion_sgd, _ = correr_sgd_online(warmup, atacado, alpha=ALPHA_FIJO)
    competidores["sgd"] = metricas(prediccion_sgd, etiquetas, inicio)
    acumulados["sgd"] = np.cumsum(prediccion_sgd != etiquetas)

    # Hedge con 5 expertos (el del paper) y con 6 (mas Jev).
    unos = np.ones(cantidad_rondas, dtype=bool)
    for nombre, perdidas, predicciones in (
        ("hedge5", perdidas5, predicciones5),
        ("hedge6", perdidas6, predicciones6),
    ):
        k = perdidas.shape[0]
        eta = eta_teorico(cantidad_rondas, k)
        lista_metricas, suma_errores, suma_pesos, regrets = [], np.zeros(cantidad_rondas), 0, []
        for s in range(SEMILLAS_MUESTREO):
            generador = np.random.default_rng(s)
            pesos = np.full(k, 1.0 / k)
            historial = np.zeros((k, cantidad_rondas))
            perdidas_jugador = np.zeros(cantidad_rondas)
            for ronda in range(cantidad_rondas):
                historial[:, ronda] = pesos
                experto = generador.choice(k, p=pesos)
                perdidas_jugador[ronda] = float(predicciones[experto, ronda] != etiquetas[ronda])
                pesos = pesos * np.exp(-eta * perdidas[:, ronda])
                pesos /= pesos.sum()
            lista_metricas.append(metricas(desde_perdidas(perdidas_jugador, etiquetas), etiquetas, inicio))
            suma_errores += perdidas_jugador
            suma_pesos = suma_pesos + historial
            regrets.append(regret_acumulado(perdidas_jugador, perdidas)[0])
        competidores[nombre] = {
            mitad: {m: float(np.mean([x[mitad][m] for x in lista_metricas])) for m in lista_metricas[0][mitad]}
            for mitad in ("primera", "segunda")
        }
        acumulados[nombre] = np.cumsum(suma_errores / SEMILLAS_MUESTREO)
        r[f"pesos_{nombre}"] = submuestrear(suma_pesos / SEMILLAS_MUESTREO, indices)
        regret_medio = np.mean(regrets, axis=0)
        r[f"regret_{nombre}"] = submuestrear(regret_medio, indices)
        r[f"cota_{nombre}"] = float(cota_peor_caso(cantidad_rondas, k))

    r["competidores"] = competidores
    r["acumulados"] = {n: submuestrear(a, indices) for n, a in acumulados.items()}

    # P1 y P3: distribuciones de probabilidad y calibracion, por mitad.
    r["histogramas"] = {}
    r["calibracion"] = {}
    for mitad, tramo in (("primera", slice(0, inicio)), ("segunda", slice(inicio, None))):
        r["histogramas"][mitad] = {
            "jev": histograma_por_clase(p_jev[tramo], etiquetas[tramo]),
            "nb": histograma_por_clase(p_nb[tramo], etiquetas[tramo]),
        }
        r["calibracion"][mitad] = calibracion(p_jev[tramo], etiquetas[tramo])

    # El mismo spam, antes y despues del ataque.
    originales = stream["texto"].tolist()
    atacados_idx = [i for i in range(inicio, cantidad_rondas)
                    if etiquetas[i] == 1 and textos[i] != originales[i]]
    textos_orig = [originales[i] for i in atacados_idx]
    p_nb_orig = naive_bayes.clasificador.predict_proba(
        naive_bayes.vectorizador.transform(textos_orig))[:, 1] if textos_orig else np.array([])
    p_jev_orig = jev.probabilidades(textos_orig)
    r["pares"] = {
        "nb_antes": np.round(p_nb_orig, 3).tolist(),
        "nb_despues": np.round(p_nb[atacados_idx], 3).tolist(),
        "jev_antes": np.round(p_jev_orig, 3).tolist(),
        "jev_despues": np.round(p_jev[atacados_idx], 3).tolist(),
    }
    if semilla == 0 and atacados_idx:
        caida = p_nb_orig - p_nb[atacados_idx]
        orden = np.argsort(-caida)[:14]
        r["galeria"] = [{
            "original": textos_orig[j],
            "atacado": palabras_con_cambios(textos_orig[j], textos[atacados_idx[j]]),
            "nb": [round(float(p_nb_orig[j]), 3), round(float(p_nb[atacados_idx[j]]), 3)],
            "jev": [round(float(p_jev_orig[j]), 3), round(float(p_jev[atacados_idx[j]]), 3)],
            "tipo": jev.tipos([textos_orig[j]])[0],
        } for j in orden]

    tipos_spam = jev.tipos([t for t, y in zip(stream["texto"], stream["etiqueta"]) if y == 1])
    r["tipos_spam"] = {t: tipos_spam.count(t) for t in set(tipos_spam)}

    # P4: etiquetado al azar contra guiado por la duda de Jev, mismo presupuesto.
    presupuesto = []
    segunda = slice(inicio, None)
    for rho in VALORES_RHO:
        eta = eta_etiqueta_parcial(cantidad_rondas, 6, rho)
        q_guiado = probabilidades_guiadas(p_jev, rho)
        fila = {"rho": rho, "hedge_azar": [], "hedge_guiado": [], "sgd_azar": [], "sgd_guiado": [],
                "etiquetas_azar": [], "etiquetas_guiado": [], "spam_en_etiquetas_guiado": []}
        for s in range(SEMILLAS_MUESTREO_PRESUPUESTO):
            mascara_azar = sortear_rondas_con_etiqueta(cantidad_rondas, rho, s)
            mascara_guiada = np.random.default_rng([s, 2]).random(cantidad_rondas) < q_guiado
            for politica, mascara, q in (("azar", mascara_azar, np.full(cantidad_rondas, rho)),
                                         ("guiado", mascara_guiada, q_guiado)):
                pj = correr_hedge_q(perdidas6, predicciones6, etiquetas, eta, mascara, q, s)
                fila[f"hedge_{politica}"].append(float(pj[segunda].sum()))
                fila[f"etiquetas_{politica}"].append(int(mascara.sum()))
                if s < SEMILLAS_MUESTREO_SGD:
                    prediccion = sgd_con_mascara(warmup, atacado, mascara)
                    fila[f"sgd_{politica}"].append(float((prediccion[segunda] != etiquetas[segunda]).sum()))
            fila["spam_en_etiquetas_guiado"].append(float(etiquetas[mascara_guiada].mean()))
        presupuesto.append(fila)
    r["presupuesto"] = presupuesto
    r["segundos"] = round(time.time() - inicio_reloj, 1)

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(r), encoding="utf-8")
    return semilla, f"{r['segundos']:.0f}s"


# --- Recoleccion de textos para Jev --------------------------------------------

def recolectar_textos(semillas):
    """Todos los textos que Jev va a necesitar: el corpus y el spam atacado de cada semilla."""
    corpus = cargar_corpus()
    textos = corpus["texto"].tolist()
    etiquetas = corpus["etiqueta"].tolist()
    atacados = [False] * len(textos)
    for semilla in semillas:
        warmup, stream = dividir_warmup_y_stream(corpus, semilla=semilla)
        atacado, inicio = construir_stream_atacado(warmup, stream, semilla=semilla)
        for i in range(inicio, len(atacado)):
            if atacado["etiqueta"].iloc[i] == 1:
                textos.append(atacado["texto"].iloc[i])
                etiquetas.append(1)
                atacados.append(True)
    return textos, etiquetas, atacados


def main():
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--semillas", type=int, nargs="*", default=SEMILLAS)
    argumentos.add_argument("--simular", action="store_true",
                            help="Jev FALSO para probar el pipeline sin API key")
    argumentos.add_argument("--procesos", type=int, default=6)
    a = argumentos.parse_args()

    print(f"=== Etapa 10: Jev ({'SIMULADO' if a.simular else MODELO}) ===")
    print("Recolectando textos (corpus + spam atacado de cada semilla)...")
    completar_cache(*recolectar_textos(a.semillas), simulado=a.simular)

    print(f"Corriendo {len(a.semillas)} semillas con {a.procesos} procesos...", flush=True)
    inicio = time.time()
    with ProcessPoolExecutor(max_workers=a.procesos) as ejecutor:
        futuros = [ejecutor.submit(procesar_semilla, s, a.simular) for s in a.semillas]
        for n, futuro in enumerate(as_completed(futuros), 1):
            semilla, estado = futuro.result()
            print(f"  semilla {semilla:>2} lista ({estado}) [{n}/{len(a.semillas)}, "
                  f"{(time.time() - inicio) / 60:.1f} min]", flush=True)

    from dashboard_jev import agregar_y_generar
    agregar_y_generar(simulado=a.simular)


if __name__ == "__main__":
    main()
