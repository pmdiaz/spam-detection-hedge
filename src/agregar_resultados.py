"""Agrega los resultados de las 20 semillas y contesta las preguntas abiertas.

Lee resultados/semillas/semilla_<s>.json y reporta, con media y desvio entre
semillas de permutacion:

  1. Si el modelo estatico es Naive Bayes en todas las semillas (§9, punto 3).
  2. Los tres competidores en la mitad atacada, y que fraccion de la brecha
     entre el estatico y reentrenar cubre Hedge (pregunta 1 del paper).
  3. El regret de Hedge contra sus cotas.
  4. El barrido de rho: donde se cruzan combinar y reentrenar (pregunta 2).

Guarda un resumen en resultados/resumen.json para las figuras y el paper.
"""

import json
from pathlib import Path

import numpy as np

DIRECTORIO = Path(__file__).resolve().parent.parent / "resultados"


def media_y_desvio(valores):
    return float(np.mean(valores)), float(np.std(valores))


def formatear(valores, decimales=1):
    media, desvio = media_y_desvio(valores)
    return f"{media:.{decimales}f} +/- {desvio:.{decimales}f}"


def main():
    archivos = sorted((DIRECTORIO / "semillas").glob("semilla_*.json"))
    resultados = [json.loads(archivo.read_text(encoding="utf-8")) for archivo in archivos]
    cantidad = len(resultados)
    print(f"Semillas completas: {cantidad}\n")

    nombres = resultados[0]["expertos"]
    resumen = {"cantidad_semillas": cantidad}

    # --- 1. Decisiones fijas y lo que habria elegido la CV ---
    print("=== 1. Decisiones fijas por diseno, y lo que habria elegido la CV ===")
    estaticos_usados = {nombres[r["indice_estatico"]] for r in resultados}
    print(f"  Modelo estatico usado: {', '.join(sorted(estaticos_usados))}")

    conteo_estatico_cv = {}
    for resultado in resultados:
        nombre_cv = nombres[resultado["indice_estatico_cv"]]
        conteo_estatico_cv[nombre_cv] = conteo_estatico_cv.get(nombre_cv, 0) + 1
    print("  La CV sobre el warm-up habria elegido como estatico:")
    for nombre, veces in conteo_estatico_cv.items():
        print(f"    {nombre:<24} {veces}/{cantidad}")

    alphas_usados = {r["alpha_sgd"] for r in resultados}
    print(f"  alpha de SGD online usado: {', '.join(str(a) for a in sorted(alphas_usados))}")
    conteo_alpha_cv = {}
    for resultado in resultados:
        clave_alpha = str(resultado["alpha_sgd_cv"])
        conteo_alpha_cv[clave_alpha] = conteo_alpha_cv.get(clave_alpha, 0) + 1
    print("  La CV sobre el warm-up habria elegido como alpha:")
    for valor, veces in sorted(conteo_alpha_cv.items()):
        print(f"    {valor:<24} {veces}/{cantidad}")

    conteo_mejor = {}
    for resultado in resultados:
        mejor = nombres[resultado["indice_mejor_experto"]]
        conteo_mejor[mejor] = conteo_mejor.get(mejor, 0) + 1
    print("  Mejor experto fijo en retrospectiva (stream atacado):")
    for nombre, veces in conteo_mejor.items():
        print(f"    {nombre:<24} {veces}/{cantidad}")

    resumen["estatico_cv"] = conteo_estatico_cv
    resumen["alpha_sgd_cv"] = conteo_alpha_cv
    resumen["mejor_experto"] = conteo_mejor

    # --- 2. Competidores en la mitad atacada ---
    print("\n=== 2. Competidores (media +/- desvio entre semillas) ===")
    print(f"  {'competidor':<22} {'err 1ra mitad':>16} {'err atacada':>16} {'SC atacada':>16} {'BH atacada':>14}")
    competidores = [
        ("estatico", "estatico"),
        ("Hedge randomizado", "hedge"),
        ("Hedge deterministico", "hedge_deterministico"),
        ("SGD online", "sgd"),
    ]
    resumen["competidores"] = {}
    for etiqueta, clave in competidores:
        primera = [r[clave]["errores_primera"] for r in resultados]
        segunda = [r[clave]["errores_segunda"] for r in resultados]
        sc = [r[clave]["sc_segunda"] for r in resultados]
        bh = [r[clave]["bh_segunda"] for r in resultados]
        print(f"  {etiqueta:<22} {formatear(primera):>16} {formatear(segunda):>16} "
              f"{formatear(sc):>15}% {formatear(bh, 2):>13}%")
        resumen["competidores"][clave] = {
            "errores_primera": media_y_desvio(primera),
            "errores_segunda": media_y_desvio(segunda),
            "sc_segunda": media_y_desvio(sc),
            "bh_segunda": media_y_desvio(bh),
        }

    fracciones = []
    for resultado in resultados:
        brecha = resultado["estatico"]["errores_segunda"] - resultado["sgd"]["errores_segunda"]
        cubierto = resultado["estatico"]["errores_segunda"] - resultado["hedge"]["errores_segunda"]
        if brecha > 0:
            fracciones.append(100 * cubierto / brecha)
    print(f"\n  Fraccion de la brecha estatico -> reentrenar que cubre Hedge: "
          f"{formatear(fracciones, 0)}%  (mediana {np.median(fracciones):.0f}%, "
          f"rango {min(fracciones):.0f}% a {max(fracciones):.0f}%)")
    resumen["fraccion_brecha_hedge"] = {
        "media": float(np.mean(fracciones)),
        "desvio": float(np.std(fracciones)),
        "mediana": float(np.median(fracciones)),
    }

    # --- 3. Regret contra las cotas ---
    print("\n=== 3. Regret de Hedge en el stream atacado ===")
    claves_regret = [
        ("randomizado, eta peor caso", "hedge_peor_caso", "cota_peor_caso"),
        ("randomizado, eta small-loss", "hedge_small_loss", "cota_small_loss"),
        ("deterministico", "hedge_deterministico", None),
    ]
    resumen["regret"] = {}
    for etiqueta, clave, clave_cota in claves_regret:
        valores = [r["regret"][clave] for r in resultados]
        linea = f"  {etiqueta:<30} {formatear(valores):>16}"
        if clave_cota is not None:
            cotas = [r["regret"][clave_cota] for r in resultados]
            bajo_cota = sum(1 for r in resultados if r["regret"][clave] <= r["regret"][clave_cota])
            linea += f"   cota {formatear(cotas):>16}   bajo su cota en {bajo_cota}/{cantidad}"
        print(linea)
        resumen["regret"][clave] = media_y_desvio(valores)

    # --- 4. Barrido de rho ---
    print("\n=== 4. Barrido de rho: errores en la mitad atacada ===")
    print(f"  {'rho':>5} {'Hedge':>16} {'SGD online':>16} {'Hedge gana en':>15} "
          f"{'regret Hedge':>16} {'R/R(1)':>7} {'1/sqrt(rho)':>12}")
    valores_rho = [b["rho"] for b in resultados[0]["barrido_rho"]]
    regret_referencia = None
    resumen["barrido_rho"] = []
    for indice, rho in enumerate(valores_rho):
        errores_hedge = []
        errores_sgd = []
        regrets = []
        victorias_hedge = 0
        for resultado in resultados:
            barrido = resultado["barrido_rho"][indice]
            media_hedge = float(np.mean(barrido["errores_segunda_hedge"]))
            media_sgd = float(np.mean(barrido["errores_segunda_sgd"]))
            errores_hedge.append(media_hedge)
            errores_sgd.append(media_sgd)
            regrets.append(float(np.mean(barrido["regret_hedge"])))
            if media_hedge < media_sgd:
                victorias_hedge += 1

        regret_medio = float(np.mean(regrets))
        if regret_referencia is None:
            regret_referencia = regret_medio
        print(f"  {rho:>5} {formatear(errores_hedge):>16} {formatear(errores_sgd):>16} "
              f"{victorias_hedge:>9}/{cantidad:<5} {formatear(regrets):>16} "
              f"{regret_medio / regret_referencia:>7.2f} {1 / np.sqrt(rho):>12.2f}")
        resumen["barrido_rho"].append({
            "rho": rho,
            "errores_hedge": media_y_desvio(errores_hedge),
            "errores_sgd": media_y_desvio(errores_sgd),
            "regret_hedge": media_y_desvio(regrets),
            "semillas_donde_gana_hedge": victorias_hedge,
        })

    regrets_por_rho = [b["regret_hedge"][0] for b in resumen["barrido_rho"]]
    pendiente = np.polyfit(np.log(valores_rho), np.log(regrets_por_rho), 1)[0]
    print(f"\n  Pendiente log-log del regret de Hedge: {pendiente:.2f}  (teoria: -0.5)")
    resumen["pendiente_rho"] = float(pendiente)

    tiempos = [r["segundos"] for r in resultados]
    print(f"\nTiempo por semilla (sin contar el cache): {formatear(tiempos, 0)} s")

    (DIRECTORIO / "resumen.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    print(f"Resumen guardado en {DIRECTORIO / 'resumen.json'}")


if __name__ == "__main__":
    main()
