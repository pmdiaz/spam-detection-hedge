"""Verificacion de la etapa 3: el adversario y su calibracion.

Criterios del plan (§8):
  1. El SC del modelo estatico cae de ~80% a ~40%.
  2. El SC del experto estructural no se mueve.
  3. La distribucion de longitudes del spam atacado se superpone con la original.

Calibracion en dos pasos y en este orden (§5):
  1. Subir la intensidad de la OFUSCACION, que no tiene costo en longitud.
  2. Solo si no alcanza, agregar INYECCION respetando el tope de longitud.

Sobre el criterio 3: la comparacion es contra la distribucion del SPAM ORIGINAL,
no contra la del corpus completo. El spam es naturalmente mas largo que el ham
(23,48 contra 13,18 tokens en Almeida et al., Tabla 2), asi que compararlo con
el percentil del corpus daria violacion incluso sin ningun ataque.
"""

import numpy as np

from adversario import (
    Adversario,
    calcular_pesos_tokens,
    palabras_mas_legitimas,
    tokens_mas_delatores,
)
from datos import cargar_corpus, dividir_warmup_y_stream
from estatico import seleccionar_modelo_estatico
from expertos import construir_expertos, entrenar_expertos
from metricas import spam_caught

OBJETIVO_SC = 40.0
TOLERANCIA_MEDIANA = 1.20
CANTIDAD_TOKENS_OFUSCADOS = 800


def longitudes(textos):
    return np.array([len(texto.split()) for texto in textos])


def spam_de_la_segunda_mitad(stream, indice_inicio):
    segunda_mitad = stream.iloc[indice_inicio:]
    return segunda_mitad[segunda_mitad["etiqueta"] == 1]["texto"].tolist()


def medir_sc(experto, stream, indice_inicio):
    segunda_mitad = stream.iloc[indice_inicio:]
    predicciones = experto.predecir(segunda_mitad["texto"].tolist())
    return spam_caught(segunda_mitad["etiqueta"].to_numpy(), predicciones)


def main():
    corpus = cargar_corpus()
    warmup, stream = dividir_warmup_y_stream(corpus, semilla=0)

    print("Entrenando expertos sobre el warm-up (CV anidada, tarda unos minutos)...")
    expertos = entrenar_expertos(construir_expertos(), warmup)

    indice_estatico, nombre_estatico, _ = seleccionar_modelo_estatico(warmup)
    modelo_estatico = expertos[indice_estatico]
    experto_estructural = expertos[4]

    pesos = calcular_pesos_tokens(warmup["texto"].tolist(), warmup["etiqueta"].to_numpy())
    tokens_objetivo = tokens_mas_delatores(pesos, CANTIDAD_TOKENS_OFUSCADOS)
    palabras_buenas = palabras_mas_legitimas(pesos, cantidad=200)

    indice_inicio = len(stream) // 2

    longitudes_originales = longitudes(spam_de_la_segunda_mitad(stream, indice_inicio))
    mediana_referencia = float(np.median(longitudes_originales))
    maximo_referencia = float(longitudes_originales.max())

    sc_estatico_sin_ataque = medir_sc(modelo_estatico, stream, indice_inicio)
    sc_estructural_sin_ataque = medir_sc(experto_estructural, stream, indice_inicio)

    print(f"\nModelo estatico: {nombre_estatico}")
    print(f"Spam en la segunda mitad: {len(longitudes_originales)} mensajes")
    print(f"Longitud del spam original: mediana {mediana_referencia:.0f} tokens, "
          f"maximo {maximo_referencia:.0f}")
    print(f"Restriccion de longitud: mediana <= {TOLERANCIA_MEDIANA * mediana_referencia:.0f}, "
          f"percentil 95 <= {maximo_referencia:.0f}\n")

    print("=== Calibracion: ofuscacion de los top-800 tokens, mas inyeccion creciente ===")
    encabezado = (f"{'inyectadas':>11} {'SC estatico':>12} {'SC estruct.':>12} "
                  f"{'mediana':>8} {'p95':>6} {'longitud':>10}")
    print(encabezado)
    print("-" * len(encabezado))

    configuracion_elegida = None

    for cantidad_inyectada in [0, 1, 2, 3, 4, 5, 6]:
        adversario = Adversario(tokens_objetivo, palabras_buenas, cantidad_inyectada)
        atacado = adversario.atacar_stream(stream, indice_inicio, semilla=0)

        sc_estatico = medir_sc(modelo_estatico, atacado, indice_inicio)
        sc_estructural = medir_sc(experto_estructural, atacado, indice_inicio)

        longitudes_atacadas = longitudes(spam_de_la_segunda_mitad(atacado, indice_inicio))
        mediana = float(np.median(longitudes_atacadas))
        percentil95 = float(np.percentile(longitudes_atacadas, 95))

        longitud_ok = (
            mediana <= TOLERANCIA_MEDIANA * mediana_referencia
            and percentil95 <= maximo_referencia
        )

        print(f"{cantidad_inyectada:>11} {sc_estatico:>11.2f}% {sc_estructural:>11.2f}% "
              f"{mediana:>8.0f} {percentil95:>6.0f} {'ok' if longitud_ok else 'VIOLADA':>10}")

        if configuracion_elegida is None and longitud_ok and sc_estatico <= OBJETIVO_SC:
            configuracion_elegida = (cantidad_inyectada, sc_estatico, sc_estructural)

    print("\n=== Verificacion de los tres criterios ===")
    if configuracion_elegida is None:
        print("NO se alcanzo el objetivo dentro de la restriccion de longitud.")
        return

    cantidad_inyectada, sc_estatico, sc_estructural = configuracion_elegida
    caida_relativa = 100 * (1 - sc_estatico / sc_estatico_sin_ataque)

    print(f"Configuracion: ofuscacion de {CANTIDAD_TOKENS_OFUSCADOS} tokens "
          f"+ {cantidad_inyectada} good word(s)")
    print(f"  1. SC del estatico   : {sc_estatico_sin_ataque:.2f}% -> {sc_estatico:.2f}%  "
          f"(caida relativa {caida_relativa:.0f}%)")
    print(f"  2. SC del estructural: {sc_estructural_sin_ataque:.2f}% -> {sc_estructural:.2f}%")
    print(f"  3. Longitud          : dentro de la restriccion")


if __name__ == "__main__":
    main()
