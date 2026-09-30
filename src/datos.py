"""Carga del corpus y division en warm-up y stream.

El protocolo de aprendizaje online de la slide 57 necesita una secuencia de rondas.
El corpus no tiene timestamps, asi que el orden lo fijamos nosotros con una
permutacion aleatoria: en el marco adversarial es el adversario quien elige la
secuencia, de modo que imponer un orden es legitimo (ver limitaciones del plan).

El primer 20% de la secuencia es el warm-up: sirve solo para entrenar a los
expertos, que despues quedan congelados (slide 71). El 80% restante es el stream
sobre el que se mide el regret.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ARCHIVO_CORPUS = Path(__file__).resolve().parent.parent / "datos" / "SMSSpamCollection"

PROPORCION_WARMUP = 0.20


def cargar_corpus():
    """Devuelve un DataFrame con las columnas 'etiqueta' (0=ham, 1=spam) y 'texto'."""
    corpus = pd.read_csv(
        ARCHIVO_CORPUS,
        sep="\t",
        header=None,
        names=["clase", "texto"],
        quoting=3,  # el corpus tiene comillas sueltas que no delimitan campos
    )

    corpus["etiqueta"] = (corpus["clase"] == "spam").astype(int)
    return corpus[["etiqueta", "texto"]]


def dividir_warmup_y_stream(corpus, semilla):
    """Permuta el corpus y lo parte en warm-up (20%) y stream (80%).

    La semilla controla la permutacion, que es una de las fuentes de azar que
    variamos entre corridas para reportar bandas de dispersion.
    """
    generador = np.random.default_rng(semilla)
    orden = generador.permutation(len(corpus))
    corpus_permutado = corpus.iloc[orden].reset_index(drop=True)

    cantidad_warmup = int(len(corpus_permutado) * PROPORCION_WARMUP)

    warmup = corpus_permutado.iloc[:cantidad_warmup].reset_index(drop=True)
    stream = corpus_permutado.iloc[cantidad_warmup:].reset_index(drop=True)

    return warmup, stream


if __name__ == "__main__":
    corpus = cargar_corpus()

    cantidad_spam = int(corpus["etiqueta"].sum())
    porcentaje_spam = 100 * cantidad_spam / len(corpus)

    print("=== Etapa 1: verificacion del corpus ===")
    print(f"Mensajes totales : {len(corpus)}  (esperado 5574)")
    print(f"Spam             : {cantidad_spam}  (esperado 747)")
    print(f"Porcentaje spam  : {porcentaje_spam:.2f}%  (esperado 13.40%)")

    warmup, stream = dividir_warmup_y_stream(corpus, semilla=0)
    print()
    print(f"Warm-up : {len(warmup)} mensajes, {int(warmup['etiqueta'].sum())} spam")
    print(f"Stream  : {len(stream)} mensajes, {int(stream['etiqueta'].sum())} spam")

    # Dato de Almeida et al. (Tabla 2) que respalda al experto estructural:
    # el spam promedia 23,48 tokens y el ham 13,18.
    tokens_por_mensaje = corpus["texto"].str.split().str.len()
    print()
    print("Tokens promedio por mensaje (Almeida et al., Tabla 2):")
    print(f"  ham  : {tokens_por_mensaje[corpus['etiqueta'] == 0].mean():.2f}  (esperado 13.18)")
    print(f"  spam : {tokens_por_mensaje[corpus['etiqueta'] == 1].mean():.2f}  (esperado 23.48)")
