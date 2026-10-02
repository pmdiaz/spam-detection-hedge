"""Visuales para la presentacion: imagenes listas para ubicar en Canva.

Estilo "data story editorial": fondo transparente (se apoya sobre diapositivas
claras), tipografia Avenir Next, etiquetas directas sobre los datos y una sola
anotacion protagonista por grafico. Los colores identifican entidades y son los
mismos del paper (validados para daltonismo); los textos van en tinta neutra.

Exporta a presentacion/visuales/ en PNG al doble de la resolucion de una
diapositiva de Canva (288 px por pulgada de diapositiva de 13,33 x 7,5).

Lee los resultados guardados por src/experimento.py y src/reponderacion_sgd.py;
no vuelve a correr el experimento.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
from algoritmos import construir_secuencia_adversaria, correr_hedge, eta_teorico, regret_acumulado  # noqa: E402

SALIDA = Path(__file__).resolve().parent / "visuales"
DPI = 288

TINTA = "#1F2430"
TINTA_2 = "#5A6274"
TENUE = "#9AA1AE"
GRILLA = "#E6E8ED"
APAGADO = "#D9DCE2"
BURBUJA = "#EEF0F4"

ESTATICO = "#EB6834"
HEDGE = "#2A78D6"
SGD = "#1BAF7A"
ESTRUCTURAL = "#4A3AA7"
OTROS = "#008300"
DETERMINISTICO = "#E34948"
SMALL_LOSS = "#E87BA4"
ZONA_HEDGE = "#DCE9F9"

plt.rcParams.update({
    "font.family": "Avenir Next",
    "font.size": 14,
    "axes.edgecolor": APAGADO,
    "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2,
    "ytick.color": TINTA_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.spines.left": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRILLA,
    "grid.linewidth": 1.0,
    "axes.facecolor": "none",
    "figure.facecolor": "none",
    "savefig.transparent": True,
})


def guardar(figura, nombre):
    SALIDA.mkdir(exist_ok=True)
    figura.savefig(SALIDA / f"{nombre}.png", dpi=DPI)
    plt.close(figura)
    print(f"  visuales/{nombre}.png")


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def cargar():
    semillas = []
    for s in range(20):
        resultado = json.loads((RAIZ / f"resultados/semillas/semilla_{s}.json").read_text())
        series = np.load(RAIZ / f"resultados/semillas/semilla_{s}.npz")
        semillas.append((resultado, series))
    resumen = json.loads((RAIZ / "resultados/resumen.json").read_text())
    reponderacion = json.loads((RAIZ / "resultados/reponderacion_sgd.json").read_text())
    return semillas, resumen, reponderacion


def suma_movil(valores, ventana):
    acumulada = np.concatenate([[0.0], np.cumsum(valores)])
    return acumulada[ventana:] - acumulada[:-ventana]


def sc_movil(semillas, ventana=300):
    atrapados = {"estatico": 0.0, "hedge": 0.0, "sgd": 0.0}
    spams = 0.0
    for _, z in semillas:
        es_spam = (z["etiquetas"] == 1).astype(float)
        atrapados["estatico"] = atrapados["estatico"] + suma_movil(es_spam * (z["prediccion_estatico"] == 1), ventana)
        atrapados["sgd"] = atrapados["sgd"] + suma_movil(es_spam * (z["prediccion_sgd"] == 1), ventana)
        atrapados["hedge"] = atrapados["hedge"] + suma_movil(es_spam * (1 - z["error_hedge_medio"]), ventana)
        spams = spams + suma_movil(es_spam, ventana)
    rondas = np.arange(ventana, ventana + len(spams))
    return rondas, {k: 100 * v / spams for k, v in atrapados.items()}


# ---------------------------------------------------------------------------
# Utilidades de dibujo
# ---------------------------------------------------------------------------

def etiqueta_final(eje, x, y, texto, color, dx=60):
    """Etiqueta directa al final de una serie: punto de color + texto en tinta."""
    eje.plot([x], [y], "o", color=color, markersize=7, zorder=5, clip_on=False)
    eje.text(x + dx, y, texto, va="center", ha="left", fontsize=15, color=TINTA, fontweight="demibold")


def banda_ataque(eje, inicio, fin, texto=True):
    eje.axvspan(inicio, fin, color="#F4F5F8", zorder=0, lw=0)
    eje.axvline(inicio, color=TENUE, lw=1.2, ls=(0, (3, 3)), zorder=1)
    if texto:
        eje.text(inicio + 60, 0.03, "con ataque", transform=eje.get_xaxis_transform(),
                 fontsize=13, color=TINTA_2, va="bottom", fontweight="demibold")


def palabras_en_burbuja(figura, eje, x, y, ancho, palabras, tamano=17, interlinea=1.45):
    """Escribe palabras (texto, color, negrita) con salto de linea dentro de un ancho dado.

    Matplotlib no hace wrapping con varios colores, asi que se mide cada palabra
    y se la ubica a mano. Devuelve la altura usada, en unidades de datos.
    """
    renderer = figura.canvas.get_renderer()
    inversa = eje.transData.inverted()
    cursor_x, cursor_y = x, y
    alto_linea = None
    for texto, color, negrita in palabras:
        objeto = eje.text(cursor_x, cursor_y, texto + " ", fontsize=tamano, color=color,
                          fontweight="bold" if negrita else "regular", va="top", ha="left")
        caja = objeto.get_window_extent(renderer=renderer)
        (x0, y0), (x1, y1) = inversa.transform([(caja.x0, caja.y0), (caja.x1, caja.y1)])
        ancho_palabra = x1 - x0
        if alto_linea is None:
            alto_linea = (y1 - y0) * interlinea
        if cursor_x + ancho_palabra > x + ancho and cursor_x > x:
            cursor_x = x
            cursor_y -= alto_linea
            objeto.set_position((cursor_x, cursor_y))
        cursor_x += ancho_palabra
    return (y - cursor_y) + alto_linea


# ---------------------------------------------------------------------------
# 1. El ataque, en dos telefonos
# ---------------------------------------------------------------------------

def visual_ataque():
    original = "Reply to win £100 weekly! Where will the 2006 FIFA World Cup be held? Send STOP to 87239 to end service"
    atacado = "reeply to wiin £1000 weeekly! Where will the 2006 FIFA World cuup be held? Send stoop to 87239 to end seervice lol"
    palabras_o = original.split()
    palabras_a = atacado.split()

    figura = plt.figure(figsize=(11, 4.6))
    eje = figura.add_axes([0, 0, 1, 1])
    eje.set_xlim(0, 11)
    eje.set_ylim(0, 4.6)
    eje.axis("off")

    telefonos = [
        (0.9, "Antes", [(p, TINTA, False) for p in palabras_o], "Spam real del SMS Spam Collection"),
        (6.1, "Después del ataque", None, "7 palabras alteradas y 1 agregada"),
    ]
    atacadas = []
    for i, p in enumerate(palabras_a):
        if i >= len(palabras_o):
            atacadas.append((p, HEDGE, True))
        elif p != palabras_o[i]:
            atacadas.append((p, ESTATICO, True))
        else:
            atacadas.append((p, TINTA, False))

    for x, titulo, palabras, pie in telefonos:
        if palabras is None:
            palabras = atacadas
        marco = FancyBboxPatch((x, 0.75), 4.0, 3.7, boxstyle="round,pad=0,rounding_size=0.45",
                               facecolor=TINTA, edgecolor="none")
        pantalla = FancyBboxPatch((x + 0.14, 0.89), 3.72, 3.42, boxstyle="round,pad=0,rounding_size=0.34",
                                  facecolor="white", edgecolor="none")
        eje.add_patch(marco)
        eje.add_patch(pantalla)
        eje.add_patch(FancyBboxPatch((x + 1.55, 4.13), 0.9, 0.1, boxstyle="round,pad=0,rounding_size=0.05",
                                     facecolor=TINTA, edgecolor="none"))
        eje.text(x + 2.0, 3.8, "87239", ha="center", fontsize=13, color=TINTA_2, fontweight="demibold")
        eje.text(x + 2.0, 0.28, titulo, ha="center", fontsize=17, color=TINTA, fontweight="bold")
        alto = palabras_en_burbuja(figura, eje, x + 0.55, 3.3, 2.85, palabras, tamano=15)
        eje.add_patch(FancyBboxPatch((x + 0.38, 3.47 - alto - 0.2), 3.24, alto + 0.2,
                                     boxstyle="round,pad=0,rounding_size=0.22", facecolor=BURBUJA,
                                     edgecolor="none", zorder=0))
        eje.text(x + 0.45, 3.47 - alto - 0.45, pie, fontsize=12, color=TINTA_2, va="top")

    eje.annotate("", xy=(5.95, 2.6), xytext=(5.05, 2.6),
                 arrowprops=dict(arrowstyle="-|>", color=TENUE, lw=2, mutation_scale=22))
    guardar(figura, "01_ataque_telefonos")


# ---------------------------------------------------------------------------
# 2. Hallazgo 1 como una brecha recorrida
# ---------------------------------------------------------------------------

def visual_brecha(resumen):
    c = resumen["competidores"]
    estatico = c["estatico"]["errores_segunda"][0]
    hedge = c["hedge"]["errores_segunda"][0]
    sgd = c["sgd"]["errores_segunda"][0]
    fraccion = resumen["fraccion_brecha_hedge"]["media"]

    figura, eje = plt.subplots(figsize=(12, 3.9))
    figura.subplots_adjust(left=0.04, right=0.96, top=0.86, bottom=0.2)
    eje.set_xlim(205, 58)  # menos errores hacia la derecha: la brecha se recorre de izquierda a derecha
    eje.set_ylim(-1.2, 1.4)
    eje.axis("off")

    eje.plot([estatico, sgd], [0, 0], color=APAGADO, lw=16, solid_capstyle="round", zorder=1)
    eje.plot([estatico, hedge], [0, 0], color=HEDGE, lw=16, solid_capstyle="round", zorder=2)

    marcas = [
        (estatico, ESTATICO, "No adaptarse", "estático"),
        (hedge, HEDGE, "Combinar", "Hedge"),
        (sgd, SGD, "Reentrenar", "SGD online"),
    ]
    for x, color, rotulo, nombre in marcas:
        eje.plot([x], [0], "o", markersize=26, color="white", zorder=3)
        eje.plot([x], [0], "o", markersize=19, color=color, zorder=4)
        eje.text(x, 0.62, f"{x:.0f}", ha="center", fontsize=30, fontweight="bold", color=TINTA)
        eje.text(x, -0.62, rotulo, ha="center", fontsize=16, fontweight="demibold", color=TINTA, va="top")
        eje.text(x, -0.98, nombre, ha="center", fontsize=13, color=TINTA_2, va="top")

    eje.text((estatico + hedge) / 2, 0.62, f"{fraccion:.0f}% de la brecha", ha="center", fontsize=15,
             color=HEDGE, fontweight="bold")
    eje.text(estatico + 3, 1.32, "errores en la mitad atacada (menos es mejor)", fontsize=12, color=TINTA_2, va="top")
    guardar(figura, "02_brecha_hallazgo1")


# ---------------------------------------------------------------------------
# 3. Los 305 spams atacados, como puntos
# ---------------------------------------------------------------------------

def visual_puntos(resumen, semillas):
    spams_atacados = int(round(np.mean([(z["etiquetas"][r["indice_inicio"]:] == 1).sum() for r, z in semillas])))
    c = resumen["competidores"]
    paneles = [
        ("Estático", ESTATICO, c["estatico"]["sc_segunda"][0]),
        ("Hedge", HEDGE, c["hedge"]["sc_segunda"][0]),
        ("SGD online", SGD, c["sgd"]["sc_segunda"][0]),
    ]
    columnas, filas = 20, int(np.ceil(spams_atacados / 20))

    figura, ejes = plt.subplots(1, 3, figsize=(12, 5.0))
    figura.subplots_adjust(left=0.02, right=0.98, top=0.78, bottom=0.04, wspace=0.12)
    for eje, (nombre, color, sc) in zip(ejes, paneles):
        atrapados = int(round(spams_atacados * sc / 100))
        indices = np.arange(spams_atacados)
        xs = indices % columnas
        ys = filas - 1 - indices // columnas
        colores = [color if i < atrapados else APAGADO for i in indices]
        eje.scatter(xs, ys, s=34, c=colores, linewidths=0)
        eje.set_xlim(-0.8, columnas - 0.2)
        eje.set_ylim(-0.8, filas - 0.2)
        eje.set_aspect("equal")
        eje.axis("off")
        eje.text(0, 1.2, f"{sc:.0f}%", transform=eje.transAxes, fontsize=40, fontweight="bold", color=TINTA, va="bottom")
        eje.text(0, 1.08, f"{nombre}: atrapa {atrapados} de {spams_atacados}", transform=eje.transAxes,
                 fontsize=14, color=TINTA_2, va="bottom", fontweight="demibold")
    guardar(figura, "03_puntos_spam_atacado")
    return spams_atacados


# ---------------------------------------------------------------------------
# 4. La figura del paper, construida en tres pasos
# ---------------------------------------------------------------------------

def visual_sc_pasos(semillas):
    inicio = semillas[0][0]["indice_inicio"]
    T = len(semillas[0][1]["etiquetas"])
    rondas, sc = sc_movil(semillas)
    paso = 20
    series = [
        ("estatico", ESTATICO, "Estático", (0, (5, 2))),
        ("hedge", HEDGE, "Hedge", "-"),
        ("sgd", SGD, "SGD online", (0, (1, 1.4))),
    ]
    for cantidad in [1, 2, 3]:
        figura, eje = plt.subplots(figsize=(12, 5.4))
        figura.subplots_adjust(left=0.06, right=0.84, top=0.9, bottom=0.12)
        banda_ataque(eje, inicio, T)
        for clave, color, nombre, estilo in series[:cantidad]:
            y = sc[clave][::paso]
            x = rondas[::paso]
            eje.plot(x, y, color=color, lw=3.2, ls=estilo, solid_capstyle="round")
            etiqueta_final(eje, x[-1], y[-1], nombre, color)
        eje.set_xlim(0, T)
        eje.set_ylim(0, 100)
        eje.set_yticks([0, 25, 50, 75, 100])
        eje.set_yticklabels(["0", "25", "50", "75", "100%"])
        eje.set_xticks([0, 1000, 2000, 3000, 4000])
        eje.set_xticklabels(["0", "1.000", "2.000", "3.000", "4.000"])
        eje.set_xlabel("mensajes del stream", fontsize=13)
        eje.text(0, 1.03, "Spam atrapado, ventana de 300 mensajes", transform=eje.transAxes,
                 fontsize=14, color=TINTA_2, fontweight="demibold")
        eje.tick_params(length=0, labelsize=13)
        guardar(figura, f"04_spam_atrapado_paso{cantidad}")


# ---------------------------------------------------------------------------
# 5. Pesos de Hedge, con las dos lecturas anotadas
# ---------------------------------------------------------------------------

def visual_pesos(semillas):
    inicio = semillas[0][0]["indice_inicio"]
    W = np.mean([z["pesos_hedge_medio"] for _, z in semillas], axis=0)
    T = W.shape[1]
    rondas = np.arange(T)
    nb, estructural, otros = W[0], W[4], W[1:4].sum(axis=0)

    figura, eje = plt.subplots(figsize=(12, 5.4))
    figura.subplots_adjust(left=0.06, right=0.97, top=0.9, bottom=0.12)
    eje.stackplot(rondas, nb, estructural, otros, colors=[ESTATICO, ESTRUCTURAL, OTROS],
                  edgecolor="white", linewidth=1.0)
    eje.axvline(inicio, color="white", lw=2.5, ls=(0, (3, 3)))
    eje.set_xlim(0, T - 1)
    eje.set_ylim(0, 1)
    eje.grid(False)
    eje.set_yticks([0, 0.5, 1])
    eje.set_yticklabels(["0", "0,5", "1"])
    eje.set_xticks([0, 1000, 2000, 3000, 4000])
    eje.set_xticklabels(["0", "1.000", "2.000", "3.000", "4.000"])
    eje.tick_params(length=0, labelsize=13)
    eje.set_xlabel("mensajes del stream", fontsize=13)
    eje.text(0, 1.03, "Peso de cada experto en Hedge (media de 20 semillas)", transform=eje.transAxes,
             fontsize=14, color=TINTA_2, fontweight="demibold")

    eje.text(700, nb[700] / 2, "Naive Bayes", color="white", fontsize=16, fontweight="bold", ha="center", va="center")
    eje.text(3500, nb[3500] + estructural[3500] / 2, "Estructural", color="white", fontsize=18,
             fontweight="bold", ha="center", va="center")
    eje.text(600, nb[600] + estructural[600] + otros[600] / 2, "Otros léxicos", color="white", fontsize=16,
             fontweight="bold", ha="center", va="center")

    numeros = [("1", inicio, 0.5), ("2", inicio + 700, 0.5)]
    for n, x, y in numeros:
        eje.plot([x], [y], "o", markersize=30, color="white", zorder=6)
        eje.plot([x], [y], "o", markersize=25, color=TINTA, zorder=7)
        eje.text(x, y, n, color="white", fontsize=15, fontweight="bold", ha="center", va="center", zorder=8)
    guardar(figura, "05_pesos_hedge")


# ---------------------------------------------------------------------------
# 6. El cruce entre combinar y reentrenar
# ---------------------------------------------------------------------------

def visual_cruce(resumen):
    barrido = resumen["barrido_rho"]
    hedge = np.array([b["errores_hedge"][0] for b in barrido])
    hedge_desvio = np.array([b["errores_hedge"][1] for b in barrido])
    sgd = np.array([b["errores_sgd"][0] for b in barrido])
    sgd_desvio = np.array([b["errores_sgd"][1] for b in barrido])
    estatico = resumen["competidores"]["estatico"]["errores_segunda"][0]
    x = np.arange(4)

    # Cruce por interpolacion lineal entre las posiciones 2 (20%) y 3 (5%).
    d2 = hedge[2] - sgd[2]
    d3 = hedge[3] - sgd[3]
    cruce = 2 + d2 / (d2 - d3)

    figura, eje = plt.subplots(figsize=(8.2, 5.6))
    figura.subplots_adjust(left=0.1, right=0.78, top=0.88, bottom=0.17)
    eje.axvspan(cruce, 3.35, color=ZONA_HEDGE, lw=0, zorder=0)
    eje.text((cruce + 3.35) / 2, 58, "acá\ncombinar\ngana", ha="center", va="bottom", fontsize=13,
             color=HEDGE, fontweight="bold", linespacing=1.15)
    eje.axhline(estatico, color=ESTATICO, lw=2, ls=(0, (5, 3)), zorder=1)
    eje.text(3.42, estatico, f"Estático  {estatico:.0f}", va="center", fontsize=14, color=TINTA, fontweight="demibold")
    eje.fill_between(x, sgd - sgd_desvio, sgd + sgd_desvio, color=SGD, alpha=0.12, lw=0)
    eje.fill_between(x, hedge - hedge_desvio, hedge + hedge_desvio, color=HEDGE, alpha=0.12, lw=0)
    eje.plot(x, sgd, color=SGD, lw=3.2, ls=(0, (1, 1.4)), marker="s", markersize=9)
    eje.plot(x, hedge, color=HEDGE, lw=3.2, marker="o", markersize=9)
    etiqueta_final(eje, 3, sgd[3], f"SGD online  {sgd[3]:.0f}", SGD, dx=0.12)
    eje.text(3.12, hedge[3] - 14, f"Hedge  {hedge[3]:.0f}", va="center", fontsize=15, color=TINTA, fontweight="demibold")
    eje.set_xlim(-0.25, 3.35)
    eje.set_ylim(50, 250)
    eje.set_xticks(x)
    eje.set_xticklabels(["todos", "1 de cada 2", "1 de cada 5", "1 de cada 20"])
    eje.tick_params(length=0, labelsize=13)
    eje.set_xlabel("mensajes que el usuario reporta", fontsize=13)
    eje.text(0, 1.04, "Errores en la mitad atacada (media ± desvío, 20 semillas)", transform=eje.transAxes,
             fontsize=14, color=TINTA_2, fontweight="demibold")
    guardar(figura, "06_cruce_etiquetas")


# ---------------------------------------------------------------------------
# 7. Reponderar empeora a SGD
# ---------------------------------------------------------------------------

def visual_reponderacion(reponderacion):
    hedge = reponderacion["0.05|hedge"][0]
    estatico = reponderacion["estatico"][0]
    filas = [
        ("SGD, sin reponderar", reponderacion["0.05|sgd|1"][0]),
        ("SGD × 1/√ρ", reponderacion["0.05|sgd|1/sqrt(rho)"][0]),
        ("SGD × 1/ρ", reponderacion["0.05|sgd|1/rho"][0]),
    ]
    figura, eje = plt.subplots(figsize=(8.2, 4.6))
    figura.subplots_adjust(left=0.27, right=0.95, top=0.74, bottom=0.1)
    y = np.arange(len(filas))[::-1]
    for (nombre, valor), yy in zip(filas, y):
        eje.plot([hedge, valor], [yy, yy], color=APAGADO, lw=3, zorder=1)
        eje.plot([valor], [yy], "o", markersize=15, color=SGD, zorder=3)
        eje.text(valor + 9, yy, f"{valor:.0f}", va="center", fontsize=17, fontweight="bold", color=TINTA)
    eje.axvline(hedge, color=HEDGE, lw=3, zorder=2)
    eje.text(hedge, len(filas) - 0.3, f"Hedge {hedge:.0f}", ha="center", va="bottom", fontsize=14, color=HEDGE, fontweight="bold")
    eje.set_yticks(y)
    eje.set_yticklabels([n for n, _ in filas], fontsize=15)
    eje.set_xlim(150, 360)
    eje.set_ylim(-0.6, len(filas) - 0.35)
    eje.grid(False)
    eje.set_xticks([])
    eje.spines["bottom"].set_visible(False)
    eje.tick_params(length=0)
    eje.text(-0.37, 1.2, f"Con 1 de cada 20 mensajes etiquetado (el estático comete {estatico:.0f})",
             transform=eje.transAxes, fontsize=14, color=TINTA_2, fontweight="demibold")
    guardar(figura, "07_reponderacion_sgd")


# ---------------------------------------------------------------------------
# 8. El duelo: deterministico contra randomizado
# ---------------------------------------------------------------------------

def visual_duelo():
    T = 4000
    eta = eta_teorico(T, 2)
    perdidas, predicciones, etiquetas = construir_secuencia_adversaria(T, eta)
    regret_det, _ = regret_acumulado(correr_hedge(perdidas, predicciones, etiquetas, eta, False)[0], perdidas)
    regrets = [regret_acumulado(correr_hedge(perdidas, predicciones, etiquetas, eta, True, semilla=s)[0], perdidas)[0]
               for s in range(20)]
    regret_rand = np.mean(regrets, axis=0)
    rondas = np.arange(1, T + 1)
    cota = np.log(2) / eta + eta * rondas / 8

    figura, eje = plt.subplots(figsize=(8.2, 5.6))
    figura.subplots_adjust(left=0.1, right=0.7, top=0.88, bottom=0.14)
    eje.plot(rondas, regret_det, color=DETERMINISTICO, lw=4, solid_capstyle="round")
    eje.plot(rondas, cota, color=HEDGE, lw=2, ls=(0, (4, 3)))
    eje.plot(rondas, regret_rand, color=HEDGE, lw=4, solid_capstyle="round")
    eje.text(T + 80, regret_det[-1], "Voto pesado\ndeterminístico\nregret = T/2", va="center", fontsize=15,
             color=TINTA, fontweight="demibold", linespacing=1.2)
    eje.text(T + 80, 230, f"Hedge randomizado\n≈ {regret_rand[-1]:.0f}, bajo su cota\nde {cota[-1]:.0f}", va="center",
             fontsize=15, color=TINTA, fontweight="demibold", linespacing=1.2)
    eje.plot([T], [regret_det[-1]], "o", markersize=9, color=DETERMINISTICO, clip_on=False)
    eje.plot([T], [regret_rand[-1]], "o", markersize=9, color=HEDGE, clip_on=False)
    eje.set_xlim(0, T)
    eje.set_ylim(0, 2100)
    eje.set_xticks([0, 1000, 2000, 3000, 4000])
    eje.set_xticklabels(["0", "1.000", "2.000", "3.000", "4.000"])
    eje.set_yticks([0, 500, 1000, 1500, 2000])
    eje.set_yticklabels(["0", "500", "1.000", "1.500", "2.000"])
    eje.tick_params(length=0, labelsize=13)
    eje.set_xlabel("rondas", fontsize=13)
    eje.text(0, 1.04, "Regret frente a un adversario que simula al jugador", transform=eje.transAxes,
             fontsize=14, color=TINTA_2, fontweight="demibold")
    guardar(figura, "08_duelo_deterministico")


# ---------------------------------------------------------------------------
# 9. Cada cota con su eta
# ---------------------------------------------------------------------------

def visual_cotas(semillas):
    inicio = semillas[0][0]["indice_inicio"]
    perdidas_0 = semillas[0][1]["perdidas_expertos"]
    K, T = perdidas_0.shape
    rondas = np.arange(1, T + 1)
    regret_T = np.mean([z["regret_hedge_peor_caso"] for _, z in semillas], axis=0)
    regret_L = np.mean([z["regret_hedge_small_loss"] for _, z in semillas], axis=0)
    eta_T = semillas[0][0]["regret"]["eta_peor_caso"]
    cota_T = np.log(K) / eta_T + eta_T * rondas / 8
    cotas_L = []
    for r, z in semillas:
        L = np.cumsum(z["perdidas_expertos"][r["indice_mejor_experto"]].astype(float))
        e = r["regret"]["eta_small_loss"]
        cotas_L.append((np.log(K) + e * L) / (1 - np.exp(-e)) - L)
    cota_L = np.mean(cotas_L, axis=0)

    figura, eje = plt.subplots(figsize=(8.2, 5.6))
    figura.subplots_adjust(left=0.1, right=0.72, top=0.88, bottom=0.14)
    banda_ataque(eje, inicio, T)
    eje.plot(rondas, cota_T, color=HEDGE, lw=2.2, ls=(0, (4, 3)))
    eje.plot(rondas, regret_T, color=HEDGE, lw=3.6)
    eje.plot(rondas, cota_L, color=SMALL_LOSS, lw=2.2, ls=(0, (4, 3)))
    eje.plot(rondas, regret_L, color=SMALL_LOSS, lw=3.6)
    etiquetas = [
        (cota_T[-1], f"cota  {cota_T[-1]:.0f}", HEDGE),
        (regret_T[-1] + 1.5, f"η peor caso  {regret_T[-1]:.0f}", HEDGE),
        (cota_L[-1] + 1.0, f"cota  {cota_L[-1]:.0f}", SMALL_LOSS),
        (regret_L[-1] - 2.5, f"η small-loss  {regret_L[-1]:.0f}", SMALL_LOSS),
    ]
    for y, texto, color in etiquetas:
        eje.text(T + 70, y, texto, va="center", fontsize=14, color=TINTA, fontweight="demibold")
    eje.set_xlim(0, T)
    eje.set_ylim(0, 64)
    eje.set_xticks([0, 1000, 2000, 3000, 4000])
    eje.set_xticklabels(["0", "1.000", "2.000", "3.000", "4.000"])
    eje.tick_params(length=0, labelsize=13)
    eje.set_xlabel("mensajes del stream", fontsize=13)
    eje.text(0, 1.04, "Regret de Hedge, cada η contra su propia cota", transform=eje.transAxes,
             fontsize=14, color=TINTA_2, fontweight="demibold")
    guardar(figura, "09_cotas_por_eta")


def main():
    semillas, resumen, reponderacion = cargar()
    print("Generando visuales:")
    visual_ataque()
    visual_brecha(resumen)
    visual_puntos(resumen, semillas)
    visual_sc_pasos(semillas)
    visual_pesos(semillas)
    visual_cruce(resumen)
    visual_reponderacion(reponderacion)
    visual_duelo()
    visual_cotas(semillas)


if __name__ == "__main__":
    main()
