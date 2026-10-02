"""Animacion del ataque, mensaje a mensaje, para la presentacion.

Un video 16:9 con el estilo del mazo (fondo papel, titular en Georgia):
  - arriba, el spam atrapado por cada competidor en una ventana movil de 300 mensajes;
  - abajo, el peso de cada experto dentro de Hedge;
  - a la derecha, los errores acumulados desde que empieza el ataque;
  - al pie, un subtitulo que narra cada fase.
El cursor avanza rapido antes del ataque, despacio mientras el ataque pega y los
modelos reaccionan, y se detiene al final con el resultado.

Todo sale de los resultados guardados (media de 20 semillas); no corre el experimento.

Uso:
  python animacion.py            # escribe visuales/animacion_ataque.mp4 y su portada en PNG
  python animacion.py --cuadros DIR  # solo algunos cuadros sueltos en PNG en DIR, para revisar el diseño
Necesita ffmpeg: el del sistema o el del paquete imageio-ffmpeg.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import Rectangle

from visuales import (APAGADO, ESTATICO, ESTRUCTURAL, GRILLA, HEDGE, OTROS, SALIDA, SGD, TENUE, TINTA, TINTA_2,
                      cargar, sc_movil)

PAPEL = "#F7F5F0"
BANDA_ATAQUE = "#ECE9E2"
FPS = 30
VENTANA = 300

plt.rcParams.update({"figure.facecolor": PAPEL, "axes.facecolor": PAPEL, "savefig.facecolor": PAPEL,
                     "savefig.transparent": False})


def miles(n):
    return f"{n:,.0f}".replace(",", ".")


def decimal(x):
    return f"{x:.2f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def preparar_datos():
    semillas, resumen, _ = cargar()
    inicio = semillas[0][0]["indice_inicio"]
    T = len(semillas[0][1]["etiquetas"])

    rondas_sc, sc = sc_movil(semillas, VENTANA)

    W = np.mean([z["pesos_hedge_medio"] for _, z in semillas], axis=0)
    pesos = {"nb": W[0], "estructural": W[4], "otros": W[1:4].sum(axis=0)}

    # Errores por ronda de cada competidor, promediados entre semillas.
    # Para Hedge se usa el error esperado de su sorteo (error_hedge_medio).
    errores = {"estatico": 0.0, "hedge": 0.0, "sgd": 0.0}
    for _, z in semillas:
        y = z["etiquetas"]
        errores["estatico"] = errores["estatico"] + (z["prediccion_estatico"] != y)
        errores["sgd"] = errores["sgd"] + (z["prediccion_sgd"] != y)
        errores["hedge"] = errores["hedge"] + z["error_hedge_medio"]
    acumulados = {}
    for clave, valor in errores.items():
        por_ronda = valor / len(semillas)
        por_ronda[:inicio] = 0.0
        acumulados[clave] = np.cumsum(por_ronda)

    return dict(inicio=inicio, T=T, rondas_sc=rondas_sc, sc=sc, pesos=pesos, acumulados=acumulados,
                fraccion=resumen["fraccion_brecha_hedge"]["media"])


def cronograma(inicio, T):
    """Posicion del cursor (ultimo mensaje visto) en cada cuadro del video."""
    lento_hasta = 3400
    tramos = [
        np.linspace(0, inicio, 4 * FPS, endpoint=False),            # sin ataque: rapido
        np.linspace(inicio, lento_hasta, 11 * FPS, endpoint=False),  # el ataque pega: despacio
        np.linspace(lento_hasta, T, 4 * FPS),                       # se estabiliza
        np.full(5 * FPS, T),                                         # resultado, quieto
    ]
    cursores = np.concatenate(tramos).astype(int)
    cuadros_finales = len(tramos[-1])
    return cursores, cuadros_finales


def subtitulo(cursor, inicio, T, final):
    if final:
        return "Resultado: en la mitad atacada, el estático comete 190 errores, Hedge 133 y SGD 73."
    if cursor < inicio:
        return "1 · Sin ataque, los tres filtros atrapan parecido: entre 80% y 90% del spam."
    if cursor < inicio + 330:
        return "2 · Empieza el ataque: el spam llega con palabras alteradas y los tres caen."
    if cursor < inicio + 1100:
        return "3 · Hedge mueve el peso al experto estructural, que mira el formato y no las palabras."
    return "4 · SGD aprendió las palabras nuevas. El estático sigue sin adaptarse."


def separar_etiquetas(posiciones, distancia_minima, minimo, maximo):
    """Corre etiquetas en vertical para que no se pisen, respetando su orden."""
    orden = np.argsort(posiciones)
    ys = np.array(posiciones, dtype=float)[orden]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < distancia_minima:
            ys[i] = ys[i - 1] + distancia_minima
    if ys[-1] > maximo:
        ys -= ys[-1] - maximo
    ys = np.maximum(ys, minimo)
    resultado = np.empty_like(ys)
    resultado[orden] = ys
    return resultado


# ---------------------------------------------------------------------------
# Escena
# ---------------------------------------------------------------------------

class Escena:
    def __init__(self, d):
        self.d = d
        inicio, T = d["inicio"], d["T"]
        self.fig = plt.figure(figsize=(16, 9), dpi=120)
        fig = self.fig

        fig.text(0.045, 0.93, "HALLAZGO 1 · EL ATAQUE, MENSAJE A MENSAJE", fontsize=13, color=TINTA_2,
                 fontweight="bold", family="Avenir Next")
        fig.text(0.045, 0.855, "Qué pasa mientras dura el ataque", fontsize=34, color=TINTA, family="Georgia")
        self.contador = fig.text(0.955, 0.93, "", fontsize=14, color=TINTA_2, ha="right", family="Avenir Next")

        # --- Panel de spam atrapado ---
        self.ax1 = fig.add_axes([0.065, 0.43, 0.53, 0.3])
        ax1 = self.ax1
        self.banda1 = Rectangle((inicio, 0), 0, 100, color=BANDA_ATAQUE, lw=0, zorder=0)
        ax1.add_patch(self.banda1)
        self.linea_ataque1 = ax1.axvline(inicio, color=TENUE, lw=1.4, ls=(0, (3, 3)), zorder=1, alpha=0)
        self.rotulo_ataque = ax1.text(inicio + 50, 4, "con ataque", fontsize=13, color=TINTA_2,
                                      fontweight="demibold", alpha=0)
        ax1.set_xlim(0, T)
        ax1.set_ylim(0, 100)
        ax1.set_yticks([0, 25, 50, 75, 100])
        ax1.set_yticklabels(["0", "25", "50", "75", "100%"])
        ax1.set_xticks([0, 1000, 2000, 3000, 4000])
        ax1.set_xticklabels([])
        ax1.tick_params(length=0, labelsize=13)
        ax1.text(0, 1.17, "Spam atrapado, ventana de 300 mensajes", transform=ax1.transAxes, fontsize=15,
                 color=TINTA_2, fontweight="demibold")

        self.series = [
            ("estatico", ESTATICO, "Estático", (0, (5, 2))),
            ("hedge", HEDGE, "Hedge", "-"),
            ("sgd", SGD, "SGD online", (0, (1, 1.4))),
        ]
        self.lineas, self.puntos, self.etiquetas = {}, {}, {}
        for clave, color, nombre, estilo in self.series:
            (self.lineas[clave],) = ax1.plot([], [], color=color, lw=3.2, ls=estilo, solid_capstyle="round", label=nombre)
            (self.puntos[clave],) = ax1.plot([], [], "o", color=color, markersize=9, zorder=5,
                                             markeredgecolor=PAPEL, markeredgewidth=2)
            self.etiquetas[clave] = ax1.text(0, 0, "", fontsize=14, color=TINTA, fontweight="demibold", va="center")
        ax1.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, fontsize=13,
                   handlelength=2.6, borderaxespad=0.2, borderpad=0)

        # --- Panel de pesos ---
        self.ax2 = fig.add_axes([0.065, 0.16, 0.53, 0.17])
        ax2 = self.ax2
        ax2.set_xlim(0, T)
        ax2.set_ylim(0, 1)
        ax2.grid(False)
        ax2.set_yticks([0, 0.5, 1])
        ax2.set_yticklabels(["0", "0,5", "1"])
        ax2.set_xticks([0, 1000, 2000, 3000, 4000])
        ax2.set_xticklabels(["0", "1.000", "2.000", "3.000", "4.000"])
        ax2.tick_params(length=0, labelsize=13)
        ax2.set_xlabel("mensajes del stream", fontsize=13, color=TINTA_2)
        ax2.text(0, 1.3, "Peso de cada experto dentro de Hedge", transform=ax2.transAxes, fontsize=15,
                 color=TINTA_2, fontweight="demibold")
        self.linea_ataque2 = ax2.axvline(inicio, color=PAPEL, lw=2, ls=(0, (3, 3)), zorder=4, alpha=0)
        self.rellenos = []
        self.capas = [("nb", ESTATICO, "Naive Bayes"), ("estructural", ESTRUCTURAL, "Estructural"),
                      ("otros", OTROS, "Otros léxicos")]
        manijas = [Rectangle((0, 0), 1, 1, color=color) for _, color, _ in self.capas]
        ax2.legend(manijas, [n for _, _, n in self.capas], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3,
                   frameon=False, fontsize=13, handlelength=1.2, borderaxespad=0.2, borderpad=0)
        self.etiquetas_pesos = [ax2.text(0, 0, "", fontsize=13, color=TINTA, fontweight="demibold", va="center")
                                for _ in self.capas]

        # --- Contadores de errores ---
        x0 = 0.735
        fig.text(x0, 0.745, "ERRORES DESDE EL ATAQUE", fontsize=13, color=TINTA_2, fontweight="bold")
        fig.text(x0, 0.71, "media de 20 semillas; menos es mejor", fontsize=12, color=TENUE)
        self.filas = {}
        for i, (clave, color, nombre, _) in enumerate(self.series):
            y = 0.6 - i * 0.145
            fig.patches.append(Rectangle((x0, y + 0.012), 0.012, 0.022, color=color, transform=fig.transFigure))
            fig.text(x0 + 0.02, y + 0.023, nombre, fontsize=17, color=TINTA, va="center", fontweight="demibold")
            numero = fig.text(0.955, y + 0.023, "", fontsize=34, color=TINTA, ha="right", va="center", fontweight="bold")
            fondo = Rectangle((x0, y - 0.025), 0.22, 0.012, color=APAGADO, transform=fig.transFigure)
            barra = Rectangle((x0, y - 0.025), 0, 0.012, color=color, lw=0, transform=fig.transFigure)
            fig.patches.extend([fondo, barra])
            self.filas[clave] = (numero, barra)
        self.conclusion = fig.text(x0, 0.215, "", fontsize=16, color=TINTA, va="top", linespacing=1.35)

        # --- Subtitulo y fuente ---
        fig.patches.append(Rectangle((0.045, 0.085), 0.91, 0.0012, color=GRILLA, transform=fig.transFigure))
        self.subtitulo = fig.text(0.045, 0.045, "", fontsize=19, color=TINTA, va="center")
        fig.text(0.955, 0.015, "Media de 20 permutaciones del SMS Spam Collection", fontsize=10, color=TENUE, ha="right")

    def dibujar(self, cursor, final):
        d = self.d
        inicio, T = d["inicio"], d["T"]
        ax1, ax2 = self.ax1, self.ax2
        hay_ataque = cursor >= inicio

        self.contador.set_text(f"mensaje {miles(max(cursor, 1))} de {miles(T)}")

        # Banda y marca del ataque, que aparecen cuando el cursor llega.
        self.banda1.set_width(max(cursor - inicio, 0))
        for artista in (self.linea_ataque1, self.rotulo_ataque, self.linea_ataque2):
            artista.set_alpha(1 if hay_ataque else 0)

        # Curvas de spam atrapado hasta el cursor.
        visibles = d["rondas_sc"] <= cursor
        xs = d["rondas_sc"][visibles]
        cabezas = []
        for clave, color, nombre, _ in self.series:
            ys = d["sc"][clave][visibles]
            self.lineas[clave].set_data(xs, ys)
            if len(xs):
                self.puntos[clave].set_data([xs[-1]], [ys[-1]])
                cabezas.append((clave, nombre, xs[-1], ys[-1]))
            else:
                self.puntos[clave].set_data([], [])
                self.etiquetas[clave].set_text("")
        if cabezas:
            alturas = separar_etiquetas([c[3] for c in cabezas], 8, 3, 97)
            for (clave, nombre, x, y), altura in zip(cabezas, alturas):
                etiqueta = self.etiquetas[clave]
                etiqueta.set_position((min(x + 70, T + 70), altura))
                etiqueta.set_text(f"{nombre} {y:.0f}%")
                etiqueta.set_clip_on(False)

        # Pesos apilados hasta el cursor.
        for relleno in self.rellenos:
            relleno.remove()
        self.rellenos = []
        hasta = min(max(cursor, 1), T - 1)
        x = np.arange(hasta + 1)
        base = np.zeros(hasta + 1)
        centros, valores = [], []
        for clave, color, _ in self.capas:
            alto = d["pesos"][clave][:hasta + 1]
            self.rellenos.append(ax2.fill_between(x, base, base + alto, color=color, lw=0, zorder=2))
            centros.append(base[-1] + alto[-1] / 2)
            valores.append(alto[-1])
            base = base + alto
        alturas = separar_etiquetas(centros, 0.17, 0.08, 0.92)
        for etiqueta, (clave, _, nombre), altura, valor in zip(self.etiquetas_pesos, self.capas, alturas, valores):
            etiqueta.set_position((min(hasta + 70, T + 70), altura))
            etiqueta.set_text(f"{nombre} {decimal(valor)}")
            etiqueta.set_clip_on(False)

        # Contadores.
        for clave, _, _, _ in self.series:
            numero, barra = self.filas[clave]
            errores = d["acumulados"][clave][min(cursor, T - 1)] if hay_ataque else 0.0
            numero.set_text(miles(errores) if hay_ataque else "–")
            numero.set_color(TINTA if hay_ataque else TENUE)
            barra.set_width(0.22 * min(errores / 200, 1))

        if final:
            self.conclusion.set_text(
                f"Hedge recorre el {d['fraccion']:.0f}% del camino\nentre no adaptarse y reentrenar,\nsin tocar ningún modelo.")
        else:
            self.conclusion.set_text("")
        self.subtitulo.set_text(subtitulo(cursor, inicio, T, final))


def main():
    d = preparar_datos()
    escena = Escena(d)
    cursores, cuadros_finales = cronograma(d["inicio"], d["T"])

    if "--cuadros" in sys.argv:
        carpeta = Path(sys.argv[sys.argv.index("--cuadros") + 1])
        carpeta.mkdir(parents=True, exist_ok=True)
        muestras = [(1500, False), (2400, False), (2900, False), (3600, False), (d["T"], True)]
        for cursor, final in muestras:
            escena.dibujar(cursor, final)
            nombre = carpeta / f"animacion_cuadro_{cursor}{'_final' if final else ''}.png"
            escena.fig.savefig(nombre, dpi=120)
            print(" ", nombre.name)
        return

    try:
        import imageio_ffmpeg
        plt.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass  # se usa el ffmpeg del sistema

    escritor = FFMpegWriter(fps=FPS, codec="libx264",
                            extra_args=["-pix_fmt", "yuv420p", "-crf", "20", "-preset", "slow", "-movflags", "+faststart"])
    archivo = SALIDA / "animacion_ataque.mp4"
    total = len(cursores)

    # Portada: el primer cuadro, que PowerPoint muestra antes de que arranque el video.
    escena.dibujar(int(cursores[0]), final=False)
    escena.fig.savefig(SALIDA / "animacion_portada.png", dpi=120)

    with escritor.saving(escena.fig, str(archivo), dpi=120):
        for i, cursor in enumerate(cursores):
            escena.dibujar(int(cursor), final=i >= total - cuadros_finales)
            escritor.grab_frame()
    print(f"  {archivo.name}: {total} cuadros, {total / FPS:.0f} s")


if __name__ == "__main__":
    main()
