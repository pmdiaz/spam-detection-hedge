"""Etapa 8: las figuras del paper.

Lee las series guardadas por experimento.py (resultados/semillas/*.npz y *.json)
y resultados/resumen.json. No vuelve a correr ningun experimento, salvo la
construccion sintetica del panel B de F3, que es independiente de los datos.

Salidas en figuras/, cada una en PDF (vectorial, para el .tex) y PNG (vista
previa):

  f1_sc_movil       Spam Caught en ventana movil de los tres competidores.
  f2_pesos          Evolucion de los pesos de Hedge.
  f1f2_combinada    F1 y F2 como dos paneles con el eje temporal compartido
                    (la alternativa que sugirio el revisor para ahorrar espacio).
  f3_regret         A: regret de Hedge con dos eta, cada uno contra su cota.
                    B: construccion sintetica, deterministico vs randomizado.
  f4_rho            Errores en la mitad atacada vs rho, Hedge y SGD online.

Decisiones de diseno:
  - Ancho de columna de un paper a dos columnas: 3,3 pulgadas. Letra de 8 pt.
  - Color por ENTIDAD, igual en todas las figuras (paleta validada con el
    script de la guia de visualizacion, incluida la separacion para daltonismo).
  - Cada serie lleva ademas su estilo de linea, para que se lea en blanco y
    negro, y etiqueta directa sobre la curva, no solo leyenda.
  - Todas las curvas son promedios sobre las 20 semillas de permutacion.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from algoritmos import (
    construir_secuencia_adversaria,
    correr_hedge,
    eta_teorico,
    regret_acumulado,
)

RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_SEMILLAS = RAIZ / "resultados" / "semillas"
DIRECTORIO_FIGURAS = RAIZ / "figuras"

ANCHO_COLUMNA = 3.3
VENTANA_MOVIL = 300

# Las series tienen ~4.000 puntos: dibujadas enteras, las rayas y los puntos
# del estilo de linea se pegan y todas parecen continuas, y se pierde la
# codificacion para blanco y negro. Se dibuja un punto cada PASO_DIBUJO rondas;
# las curvas ya vienen suavizadas (ventana movil o promedio), no se pierde nada.
PASO_DIBUJO = 20

# --- Paleta: un color por entidad, en todas las figuras ---
COLOR_ESTATICO = "#eb6834"       # naranja: el estatico, que es Naive Bayes
COLOR_HEDGE = "#2a78d6"          # azul: Hedge randomizado, eta de peor caso
COLOR_SGD = "#1baf7a"            # aqua: SGD online
COLOR_ESTRUCTURAL = "#4a3aa7"    # violeta: el experto estructural
COLOR_OTROS_LEXICOS = "#008300"  # verde: regresion logistica + arbol + reglas
COLOR_SMALL_LOSS = "#e87ba4"     # magenta: Hedge con eta small-loss (oraculo)
COLOR_DETERMINISTICO = "#e34948"  # rojo: Hedge deterministico

TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_TENUE = "#898781"
LINEA_GRILLA = "#e1e0d9"
LINEA_EJE = "#c3c2b7"


def configurar_estilo():
    """Estilo comun: letra chica, ejes y grilla discretos."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 8,
        "axes.titlesize": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "axes.edgecolor": LINEA_EJE,
        "axes.labelcolor": TINTA_SECUNDARIA,
        "xtick.color": TINTA_TENUE,
        "ytick.color": TINTA_TENUE,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": LINEA_GRILLA,
        "grid.linewidth": 0.5,
        "lines.linewidth": 1.4,
        "hatch.linewidth": 0.6,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,
    })


def guardar(figura, nombre):
    """Guarda con el tamano EXACTO de la figura (3,3 pulgadas de ancho).

    No se usa bbox_inches="tight": agranda la imagen para que entren las
    etiquetas de afuera del eje, y despues LaTeX la achica al ancho de columna,
    con lo que la letra queda por debajo de 8 pt. Cada figura fija sus margenes
    con subplots_adjust y deja lugar para las etiquetas directas.
    """
    DIRECTORIO_FIGURAS.mkdir(exist_ok=True)
    # Sin fecha de creacion en el PDF: asi, volver a generar una figura identica
    # da un archivo identico, y git no la marca como modificada.
    figura.savefig(DIRECTORIO_FIGURAS / f"{nombre}.pdf", metadata={"CreationDate": None})
    figura.savefig(DIRECTORIO_FIGURAS / f"{nombre}.png")
    plt.close(figura)
    print(f"  figuras/{nombre}.pdf y .png")


def cargar_semillas():
    """Devuelve una lista de (json, npz) por semilla."""
    semillas = []
    for archivo_json in sorted(DIRECTORIO_SEMILLAS.glob("semilla_*.json")):
        resultado = json.loads(archivo_json.read_text(encoding="utf-8"))
        series = np.load(archivo_json.with_suffix(".npz"))
        semillas.append((resultado, series))
    return semillas


def marcar_ataque(eje, indice_inicio, con_texto=True):
    """Linea vertical en la ronda donde empieza el ataque."""
    eje.axvline(indice_inicio, color=TINTA_SECUNDARIA, linewidth=0.8, linestyle=(0, (2, 2)))
    if con_texto:
        eje.text(indice_inicio + 40, 0.98, "ataque", transform=eje.get_xaxis_transform(),
                 fontsize=7, color=TINTA_SECUNDARIA, va="top")


def suma_movil(valores, ventana):
    """Suma de las ultimas 'ventana' rondas, para cada ronda desde la ventana en adelante."""
    acumulada = np.concatenate([[0.0], np.cumsum(valores)])
    return acumulada[ventana:] - acumulada[:-ventana]


# ---------------------------------------------------------------------------
# F1: Spam Caught en ventana movil
# ---------------------------------------------------------------------------

def calcular_sc_movil(semillas):
    """SC en ventana movil, agrupando las 20 semillas.

    La ventana es hacia atras (las ultimas VENTANA_MOVIL rondas), como la veria
    un filtro que esta funcionando: por eso la caida aparece un poco despues de
    la linea del ataque. Se suman los spams atrapados y los spams totales de
    todas las semillas dentro de la ventana, y recien despues se divide: es mas
    estable que promediar porcentajes de ventanas con pocos spams.

    Para Hedge randomizado se usa el error medio por ronda sobre sus semillas de
    muestreo: un spam cuenta como atrapado en la fraccion de corridas en que se
    atrapo.
    """
    atrapados_estatico = 0.0
    atrapados_hedge = 0.0
    atrapados_sgd = 0.0
    spams = 0.0

    for _, series in semillas:
        es_spam = (series["etiquetas"] == 1).astype(float)
        atrapado_estatico = es_spam * (series["prediccion_estatico"] == 1)
        atrapado_sgd = es_spam * (series["prediccion_sgd"] == 1)
        atrapado_hedge = es_spam * (1.0 - series["error_hedge_medio"])

        atrapados_estatico = atrapados_estatico + suma_movil(atrapado_estatico, VENTANA_MOVIL)
        atrapados_hedge = atrapados_hedge + suma_movil(atrapado_hedge, VENTANA_MOVIL)
        atrapados_sgd = atrapados_sgd + suma_movil(atrapado_sgd, VENTANA_MOVIL)
        spams = spams + suma_movil(es_spam, VENTANA_MOVIL)

    rondas = np.arange(VENTANA_MOVIL, VENTANA_MOVIL + len(spams))
    return rondas, {
        "estatico": 100 * atrapados_estatico / spams,
        "hedge": 100 * atrapados_hedge / spams,
        "sgd": 100 * atrapados_sgd / spams,
    }


def dibujar_sc_movil(eje, semillas, indice_inicio):
    rondas, sc = calcular_sc_movil(semillas)

    series = [
        ("SGD online", sc["sgd"], COLOR_SGD, (0, (1, 1.2))),
        ("Hedge", sc["hedge"], COLOR_HEDGE, "-"),
        ("Estático", sc["estatico"], COLOR_ESTATICO, (0, (4, 1.5))),
    ]
    for nombre, valores, color, estilo in series:
        eje.plot(rondas[::PASO_DIBUJO], valores[::PASO_DIBUJO], color=color,
                 linestyle=estilo, label=nombre)
        # Etiqueta directa al final de la curva.
        eje.text(rondas[-1] + 60, valores[-1], nombre, color=TINTA_PRIMARIA,
                 fontsize=7, va="center")

    marcar_ataque(eje, indice_inicio)
    eje.set_ylim(0, 100)
    eje.set_ylabel("Spam atrapado (%)")
    eje.set_xlim(0, rondas[-1])


def figura_sc_movil(semillas, indice_inicio):
    figura, eje = plt.subplots(figsize=(ANCHO_COLUMNA, 2.0))
    figura.subplots_adjust(left=0.15, right=0.78, top=0.95, bottom=0.2)
    dibujar_sc_movil(eje, semillas, indice_inicio)
    eje.set_xlabel("Ronda")
    # La leyenda repite las etiquetas directas, pero muestra la muestra del estilo
    # de linea, que es lo que necesita quien lee en blanco y negro.
    eje.legend(loc="lower left", frameon=False, ncol=1, handlelength=2.4)
    guardar(figura, "f1_sc_movil")


# ---------------------------------------------------------------------------
# F2: pesos de Hedge
# ---------------------------------------------------------------------------

def calcular_pesos(semillas):
    """Pesos medios de Hedge sobre las 20 semillas, en tres grupos.

    Regresion logistica, arbol y reglas se pliegan en "otros lexicos": la
    historia de la figura es Naive Bayes contra el estructural, y cinco capas
    apiladas no se leen a ancho de columna.
    """
    pesos = np.mean([series["pesos_hedge_medio"] for _, series in semillas], axis=0)
    naive_bayes = pesos[0]
    otros_lexicos = pesos[1] + pesos[2] + pesos[3]
    estructural = pesos[4]
    return naive_bayes, estructural, otros_lexicos


def dibujar_pesos(eje, semillas, indice_inicio):
    naive_bayes, estructural, otros_lexicos = calcular_pesos(semillas)
    rondas = np.arange(len(naive_bayes))

    # Naive Bayes abajo, el estructural en el medio, los otros lexicos arriba:
    # con este orden solo quedan pegados colores que se distinguen con
    # daltonismo (el validador rechazo el verde junto al naranja).
    eje.stackplot(
        rondas, naive_bayes, estructural, otros_lexicos,
        colors=[COLOR_ESTATICO, COLOR_ESTRUCTURAL, COLOR_OTROS_LEXICOS],
        edgecolor="#fcfcfb", linewidth=0.6,
    )

    # En escala de grises el violeta y el verde quedan en el mismo gris. La
    # textura a 45 grados es el canal de respaldo que prevé la guía de
    # visualizacion para impresion: se aplica a la capa secundaria. Se dibuja
    # como una capa aparte, transparente y solo con el rayado, porque en una
    # coleccion el color del rayado es el del borde, que aca es blanco.
    base_otros = naive_bayes + estructural
    eje.fill_between(
        rondas, base_otros, base_otros + otros_lexicos,
        facecolor="none", edgecolor="#7fce7f", hatch="////", linewidth=0,
    )

    # Etiquetas directas dentro de cada capa, en una ronda donde la capa es ancha.
    capas = [
        ("Naive Bayes", naive_bayes, 0.0, 1500, "white"),
        ("Estructural", estructural, naive_bayes, 3600, "white"),
        ("Otros léxicos", otros_lexicos, naive_bayes + estructural, 900, "white"),
    ]
    for nombre, capa, base, ronda, color_texto in capas:
        if np.ndim(base):
            centro = base[ronda] + capa[ronda] / 2
        else:
            centro = capa[ronda] / 2
        eje.text(ronda, centro, nombre, color=color_texto, fontsize=7,
                 ha="center", va="center", fontweight="bold")

    marcar_ataque(eje, indice_inicio, con_texto=False)
    eje.set_ylim(0, 1)
    eje.set_xlim(0, rondas[-1])
    eje.set_ylabel("Peso en Hedge")
    eje.grid(False)


def figura_pesos(semillas, indice_inicio):
    figura, eje = plt.subplots(figsize=(ANCHO_COLUMNA, 1.8))
    figura.subplots_adjust(left=0.15, right=0.97, top=0.95, bottom=0.22)
    dibujar_pesos(eje, semillas, indice_inicio)
    eje.set_xlabel("Ronda")
    guardar(figura, "f2_pesos")


def figura_combinada(semillas, indice_inicio):
    """F1 y F2 como dos paneles que comparten el eje temporal."""
    figura, (eje_sc, eje_pesos) = plt.subplots(
        2, 1, figsize=(ANCHO_COLUMNA, 3.4), sharex=True,
        gridspec_kw={"height_ratios": [1.15, 1], "hspace": 0.12},
    )
    figura.subplots_adjust(left=0.15, right=0.78, top=0.97, bottom=0.12)
    dibujar_sc_movil(eje_sc, semillas, indice_inicio)
    dibujar_pesos(eje_pesos, semillas, indice_inicio)
    eje_pesos.set_xlabel("Ronda")
    eje_sc.text(-0.16, 1.0, "A", transform=eje_sc.transAxes, fontweight="bold", va="top")
    eje_pesos.text(-0.16, 1.0, "B", transform=eje_pesos.transAxes, fontweight="bold", va="top")
    guardar(figura, "f1f2_combinada")


# ---------------------------------------------------------------------------
# F3: regret contra las cotas
# ---------------------------------------------------------------------------

def cota_peor_caso_en_el_tiempo(rondas, eta, cantidad_expertos):
    """Cota del regret de pesos exponenciales con eta fijo, valida en toda ronda t.

        R_t <= ln K / eta + eta * t / 8

    Sale del lema de Hoeffding. En t = T, con eta = sqrt(8 ln K / T), da
    sqrt(T ln K / 2), que es la mitad de la sqrt(2 T ln K) de la slide 73: la
    constante de la slide es conservadora.
    """
    return np.log(cantidad_expertos) / eta + eta * rondas / 8.0


def cota_small_loss_en_el_tiempo(perdida_acumulada_referencia, eta, cantidad_expertos):
    """Cota de Freund & Schapire (Teorema 2) con beta fijo, valida en toda ronda t.

        L_Hedge(t) <= (ln K + eta * L_i(t)) / (1 - e^{-eta})

    para cualquier experto i. Restando L_i(t) queda una cota del regret contra
    i. Como depende de la perdida acumulada del experto y no de t, su pendiente
    cambia cuando el ataque cambia el ritmo de errores: es la idea A2 del plan.
    """
    beta = np.exp(-eta)
    perdida_hedge_maxima = (np.log(cantidad_expertos) + eta * perdida_acumulada_referencia) / (1 - beta)
    return perdida_hedge_maxima - perdida_acumulada_referencia


def dibujar_regret_stream(eje, semillas, indice_inicio):
    cantidad_expertos, cantidad_rondas = semillas[0][1]["perdidas_expertos"].shape
    rondas = np.arange(1, cantidad_rondas + 1)

    regret_peor_caso = np.mean([s["regret_hedge_peor_caso"] for _, s in semillas], axis=0)
    regret_small_loss = np.mean([s["regret_hedge_small_loss"] for _, s in semillas], axis=0)

    eta_peor_caso = semillas[0][0]["regret"]["eta_peor_caso"]
    cota_peor_caso = cota_peor_caso_en_el_tiempo(rondas, eta_peor_caso, cantidad_expertos)

    cotas_small_loss = []
    for resultado, series in semillas:
        indice_mejor = resultado["indice_mejor_experto"]
        perdida_referencia = np.cumsum(series["perdidas_expertos"][indice_mejor].astype(float))
        eta_oraculo = resultado["regret"]["eta_small_loss"]
        cotas_small_loss.append(
            cota_small_loss_en_el_tiempo(perdida_referencia, eta_oraculo, cantidad_expertos)
        )
    cota_small_loss = np.mean(cotas_small_loss, axis=0)

    # Cada regret en linea continua; su cota, del mismo color y rayada.
    paso = slice(None, None, PASO_DIBUJO)
    rayada = (0, (4, 1.5))
    eje.plot(rondas[paso], cota_peor_caso[paso], color=COLOR_HEDGE, linestyle=rayada, linewidth=1.0)
    eje.plot(rondas[paso], regret_peor_caso[paso], color=COLOR_HEDGE)
    eje.plot(rondas[paso], cota_small_loss[paso], color=COLOR_SMALL_LOSS, linestyle=rayada,
             linewidth=1.0)
    eje.plot(rondas[paso], regret_small_loss[paso], color=COLOR_SMALL_LOSS)

    # eta_T: sintonizado por el horizonte (peor caso). eta_L: sintonizado por
    # L_best (small-loss, oraculo). El pie de figura explica la notacion.
    fin = rondas[-1] + 80
    eje.text(fin, cota_peor_caso[-1], r"cota $\eta_T$", fontsize=7, va="center",
             color=TINTA_SECUNDARIA)
    eje.text(fin, regret_peor_caso[-1] + 2, r"regret $\eta_T$", fontsize=7, va="center",
             color=TINTA_PRIMARIA)
    eje.text(fin, cota_small_loss[-1] + 2, r"cota $\eta_L$", fontsize=7, va="center",
             color=TINTA_SECUNDARIA)
    eje.text(fin, regret_small_loss[-1] - 4, r"regret $\eta_L$", fontsize=7, va="center",
             color=TINTA_PRIMARIA)

    marcar_ataque(eje, indice_inicio)
    eje.set_xlim(0, rondas[-1])
    eje.set_ylim(bottom=0)
    eje.set_xlabel("Ronda")
    eje.set_ylabel("Regret acumulado")


def dibujar_construccion_sintetica(eje, horizonte=4000, cantidad_semillas=20):
    """Panel B: el adversario que simula al jugador deterministico."""
    eta = eta_teorico(horizonte, 2)
    perdidas, predicciones, etiquetas = construir_secuencia_adversaria(horizonte, eta)
    rondas = np.arange(1, horizonte + 1)

    perdidas_deterministico, _ = correr_hedge(perdidas, predicciones, etiquetas, eta, randomizado=False)
    regret_deterministico, _ = regret_acumulado(perdidas_deterministico, perdidas)

    regrets_randomizado = []
    for semilla in range(cantidad_semillas):
        perdidas_jugador, _ = correr_hedge(
            perdidas, predicciones, etiquetas, eta, randomizado=True, semilla=semilla
        )
        regret, _ = regret_acumulado(perdidas_jugador, perdidas)
        regrets_randomizado.append(regret)
    regret_randomizado = np.mean(regrets_randomizado, axis=0)

    cota = cota_peor_caso_en_el_tiempo(rondas, eta, 2)

    eje.plot(rondas, regret_deterministico, color=COLOR_DETERMINISTICO)
    eje.plot(rondas, cota, color=COLOR_HEDGE, linestyle=(0, (4, 1.5)), linewidth=1.0)
    eje.plot(rondas, regret_randomizado, color=COLOR_HEDGE)

    eje.text(horizonte * 0.52, regret_deterministico[int(horizonte * 0.52)] + 120,
             "determinístico: T/2", fontsize=7, color=TINTA_PRIMARIA, ha="right")
    eje.text(horizonte * 0.97, cota[-1] + 110, "randomizado y su cota", fontsize=7,
             color=TINTA_PRIMARIA, ha="right", va="bottom")

    eje.set_xlim(0, horizonte)
    eje.set_ylim(bottom=0)
    eje.set_xlabel("Ronda")
    eje.set_ylabel("Regret acumulado")


def figura_regret(semillas, indice_inicio):
    figura, (eje_a, eje_b) = plt.subplots(
        2, 1, figsize=(ANCHO_COLUMNA, 3.8), gridspec_kw={"hspace": 0.62},
    )
    figura.subplots_adjust(left=0.17, right=0.8, top=0.93, bottom=0.1)
    dibujar_regret_stream(eje_a, semillas, indice_inicio)
    dibujar_construccion_sintetica(eje_b)
    eje_a.set_title("A. Stream atacado: cada η contra su cota", loc="left",
                    color=TINTA_PRIMARIA)
    eje_b.set_title("B. Adversario que simula al determinístico", loc="left",
                    color=TINTA_PRIMARIA)
    guardar(figura, "f3_regret")


# ---------------------------------------------------------------------------
# F4 (T1 del plan): errores vs rho
# ---------------------------------------------------------------------------

def figura_rho(resumen):
    barrido = resumen["barrido_rho"]
    valores_rho = [fila["rho"] for fila in barrido]
    hedge_media = [fila["errores_hedge"][0] for fila in barrido]
    hedge_desvio = [fila["errores_hedge"][1] for fila in barrido]
    sgd_media = [fila["errores_sgd"][0] for fila in barrido]
    sgd_desvio = [fila["errores_sgd"][1] for fila in barrido]
    estatico = resumen["competidores"]["estatico"]["errores_segunda"][0]

    figura, eje = plt.subplots(figsize=(ANCHO_COLUMNA, 2.1))
    figura.subplots_adjust(left=0.17, right=0.97, top=0.95, bottom=0.2)

    eje.axhline(estatico, color=COLOR_ESTATICO, linestyle=(0, (4, 1.5)), linewidth=1.0)
    eje.errorbar(valores_rho, sgd_media, yerr=sgd_desvio, color=COLOR_SGD,
                 linestyle=(0, (1, 1.2)), marker="s", markersize=4, capsize=2, linewidth=1.2)
    eje.errorbar(valores_rho, hedge_media, yerr=hedge_desvio, color=COLOR_HEDGE,
                 linestyle="-", marker="o", markersize=4, capsize=2, linewidth=1.2)

    # Eje x en escala log e invertido: hacia la derecha, menos etiquetas.
    eje.set_xscale("log")
    eje.set_xlim(1.3, 0.038)
    eje.set_xticks(valores_rho)
    eje.set_xticklabels(["1", "0,5", "0,2", "0,05"])
    eje.minorticks_off()

    eje.text(0.95, estatico + 6, "estático", color=TINTA_PRIMARIA, fontsize=7, va="bottom")
    eje.text(0.95, hedge_media[0] + 8, "Hedge", color=TINTA_PRIMARIA, fontsize=7, va="bottom")
    eje.text(0.95, sgd_media[0] - 8, "SGD online", color=TINTA_PRIMARIA, fontsize=7, va="top")

    eje.set_xlabel("Fracción de mensajes con etiqueta (ρ)")
    eje.set_ylabel("Errores en la mitad atacada")
    eje.set_ylim(40, 260)
    guardar(figura, "f4_rho")


def main():
    configurar_estilo()
    semillas = cargar_semillas()
    resumen = json.loads((RAIZ / "resultados" / "resumen.json").read_text(encoding="utf-8"))

    indices_inicio = {resultado["indice_inicio"] for resultado, _ in semillas}
    rondas_por_semilla = {len(series["etiquetas"]) for _, series in semillas}
    assert len(indices_inicio) == 1 and len(rondas_por_semilla) == 1, \
        "todas las semillas tienen que tener el mismo T y la misma ronda de ataque"
    indice_inicio = indices_inicio.pop()

    print(f"{len(semillas)} semillas, T = {rondas_por_semilla.pop()}, ataque en t = {indice_inicio}")
    figura_sc_movil(semillas, indice_inicio)
    figura_pesos(semillas, indice_inicio)
    figura_combinada(semillas, indice_inicio)
    figura_regret(semillas, indice_inicio)
    figura_rho(resumen)


if __name__ == "__main__":
    main()
