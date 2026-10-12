"""Agrega las semillas de experimento_jev.py y genera el dashboard HTML.

Salidas:
  resultados/jev/dashboard_datos.json   numeros agregados (lo que lee el HTML)
  figuras/dashboard_jev.html            dashboard autocontenido: se abre con doble clic

El HTML lleva los datos adentro; solo carga Chart.js y dos fuentes de CDNs
publicos. Si los resultados vienen del Jev simulado, el dashboard lo dice en una
franja roja fija arriba de todo.

Uso:  python dashboard_jev.py [--simular]
"""

import argparse
import datetime
import json
from pathlib import Path

import numpy as np

from experto_jev import DIRECTORIO_JEV, MODELO

RAIZ = Path(__file__).resolve().parent.parent
COMPETIDORES = ["estatico", "sgd", "hedge5", "hedge6", "jev"]


def _resumen(valores):
    v = np.asarray(valores, dtype=float)
    return {"media": float(np.nanmean(v)), "p10": float(np.nanpercentile(v, 10)),
            "p90": float(np.nanpercentile(v, 90))}


def agregar(simulado):
    carpeta = DIRECTORIO_JEV / ("semillas_SIMULADO" if simulado else "semillas")
    semillas = sorted((json.loads(p.read_text()) for p in carpeta.glob("semilla_*.json")),
                      key=lambda r: r["semilla"])
    if not semillas:
        raise SystemExit(f"No hay semillas en {carpeta}. Corre experimento_jev.py primero.")
    base = next((r for r in semillas if r["semilla"] == 0), semillas[0])

    d = {
        "meta": {
            "simulado": simulado, "modelo": "SIMULADO" if simulado else MODELO,
            "semillas": len(semillas), "rondas": base["rondas"], "inicio": base["inicio"],
            "expertos": base["expertos"], "generado": datetime.date.today().isoformat(),
        },
        "x": base["indices_curva"],
    }

    d["competidores"] = {
        c: {mitad: {m: _resumen([r["competidores"][c][mitad][m] for r in semillas])
                    for m in ("errores", "sc", "bh", "mcc")}
            for mitad in ("primera", "segunda")}
        for c in COMPETIDORES
    }
    d["errores_expertos"] = {
        mitad: np.mean([r["errores_expertos"][mitad] for r in semillas], axis=0).round(1).tolist()
        for mitad in ("primera", "segunda")
    }

    d["acumulados"] = {}
    for c in COMPETIDORES:
        m = np.array([r["acumulados"][c] for r in semillas])
        d["acumulados"][c] = {"media": m.mean(0).round(2).tolist(),
                              "p10": np.percentile(m, 10, 0).round(2).tolist(),
                              "p90": np.percentile(m, 90, 0).round(2).tolist()}

    for k in ("hedge5", "hedge6"):
        d[f"pesos_{k}"] = np.mean([r[f"pesos_{k}"] for r in semillas], axis=0).round(4).tolist()
        d[f"regret_{k}"] = np.mean([r[f"regret_{k}"] for r in semillas], axis=0).round(2).tolist()
        d[f"cota_{k}"] = base[f"cota_{k}"]

    d["histogramas"] = {
        mitad: {modelo: {clase: np.sum([r["histogramas"][mitad][modelo][clase] for r in semillas], 0).tolist()
                         for clase in ("spam", "ham")}
                for modelo in ("jev", "nb")}
        for mitad in ("primera", "segunda")
    }

    d["calibracion"] = {}
    for mitad in ("primera", "segunda"):
        n = np.sum([r["calibracion"][mitad]["n"] for r in semillas], 0)
        sp = np.sum([r["calibracion"][mitad]["suma_p"] for r in semillas], 0)
        sy = np.sum([r["calibracion"][mitad]["suma_y"] for r in semillas], 0)
        con = n > 0
        d["calibracion"][mitad] = [
            {"p": float(sp[i] / n[i]), "frecuencia": float(sy[i] / n[i]), "n": int(n[i])}
            for i in range(len(n)) if con[i]
        ]
        # Error de calibracion esperado (ECE), ponderado por mensajes por bin.
        d["calibracion"][f"ece_{mitad}"] = float(np.sum(np.abs(sp - sy)) / n.sum())

    pares_todos = {k: sum((r["pares"][k] for r in semillas), []) for k in base["pares"]}
    d["pares"] = base["pares"]
    d["pares_resumen"] = {
        k: {"atrapados": float(np.mean(np.array(v) >= 0.5)) if v else None,
            "mediana": float(np.median(v)) if v else None}
        for k, v in pares_todos.items()
    }
    d["pares_resumen"]["cantidad"] = len(pares_todos["nb_antes"])
    d["galeria"] = base.get("galeria", [])
    d["tipos_spam"] = base["tipos_spam"]

    d["presupuesto"] = []
    for i, fila in enumerate(base["presupuesto"]):
        salida = {"rho": fila["rho"]}
        for serie in ("hedge_azar", "hedge_guiado", "sgd_azar", "sgd_guiado",
                      "etiquetas_azar", "etiquetas_guiado", "spam_en_etiquetas_guiado"):
            valores = sum((r["presupuesto"][i][serie] for r in semillas), [])
            salida[serie] = {"media": float(np.mean(valores)), "desvio": float(np.std(valores))}
        d["presupuesto"].append(salida)
    return d


def generar_html(datos):
    plantilla = (Path(__file__).resolve().parent / "plantilla_dashboard_jev.html").read_text(encoding="utf-8")
    datos_json = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return plantilla.replace("/*__DATOS__*/null", datos_json)


def agregar_y_generar(simulado=False):
    datos = agregar(simulado)
    sufijo = "_SIMULADO" if simulado else ""
    (DIRECTORIO_JEV / f"dashboard_datos{sufijo}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    destino = RAIZ / "figuras" / f"dashboard_jev{sufijo}.html"
    destino.write_text(generar_html(datos), encoding="utf-8")
    print(f"Dashboard: {destino}")
    return destino


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser()
    argumentos.add_argument("--simular", action="store_true")
    agregar_y_generar(argumentos.parse_args().simular)
