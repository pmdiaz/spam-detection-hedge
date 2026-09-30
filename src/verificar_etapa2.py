"""Verificacion de la etapa 2: los cinco expertos entrenados y congelados.

Criterio del plan: el Spam Caught de cada experto sobre el stream SIN ataque
debe ser compatible con los baselines publicados por Almeida et al. (2011),
Tabla 7, medidos sobre este mismo corpus. Si alguno se desvia mucho, hay un bug.

Aviso sobre la comparacion: Almeida entrena con el 70% del corpus y nosotros
solo con el 20% (el warm-up), asi que es esperable quedar algo por debajo de sus
numeros. Lo que verificamos es el orden de magnitud y el ordenamiento relativo.
"""

import numpy as np

from datos import cargar_corpus, dividir_warmup_y_stream
from expertos import construir_expertos, entrenar_expertos
from metricas import accuracy, blocked_hams, mcc, spam_caught

BASELINES_ALMEIDA = {
    "naive bayes multinomial": ("MN TF NB + tok1", 52.06),
    "regresion logistica": ("SVM lineal + tok1", 83.10),
    "arbol de decision": ("C4.5 + tok2", 75.25),
    "reglas por keywords": ("sin referencia directa", None),
    "features estructurales": ("sin referencia directa", None),
}


def main():
    corpus = cargar_corpus()
    warmup, stream = dividir_warmup_y_stream(corpus, semilla=0)

    expertos = entrenar_expertos(construir_expertos(), warmup)

    etiquetas = stream["etiqueta"].to_numpy()
    textos = stream["texto"].tolist()

    print("=== Etapa 2: expertos sobre el stream SIN ataque ===")
    print(f"Warm-up: {len(warmup)} mensajes | Stream: {len(stream)} mensajes, "
          f"{int(etiquetas.sum())} spam\n")

    encabezado = f"{'experto':<26} {'SC %':>7} {'BH %':>7} {'MCC':>7} {'Acc %':>7}   referencia Almeida"
    print(encabezado)
    print("-" * len(encabezado))

    for experto in expertos:
        predicciones = experto.predecir(textos)

        nombre_referencia, sc_referencia = BASELINES_ALMEIDA[experto.nombre]
        if sc_referencia is None:
            comentario = nombre_referencia
        else:
            comentario = f"{nombre_referencia}: SC ~{sc_referencia:.0f}%"

        print(
            f"{experto.nombre:<26} "
            f"{spam_caught(etiquetas, predicciones):>7.2f} "
            f"{blocked_hams(etiquetas, predicciones):>7.2f} "
            f"{mcc(etiquetas, predicciones):>7.3f} "
            f"{accuracy(etiquetas, predicciones):>7.2f}   {comentario}"
        )

    # Referencia de Almeida: el clasificador trivial que nunca marca spam.
    # No es uno de nuestros cinco expertos, es la vara para mostrar que la
    # accuracy no sirve como metrica en este corpus.
    predicciones_triviales = np.zeros(len(etiquetas), dtype=int)
    print("-" * len(encabezado))
    print(
        f"{'(trivial: todo ham)':<26} "
        f"{spam_caught(etiquetas, predicciones_triviales):>7.2f} "
        f"{blocked_hams(etiquetas, predicciones_triviales):>7.2f} "
        f"{mcc(etiquetas, predicciones_triviales):>7.3f} "
        f"{accuracy(etiquetas, predicciones_triviales):>7.2f}   trivial rejection: Acc 86.95%"
    )

    print("\nHiperparametros elegidos por CV sobre el warm-up (nunca sobre el stream):")
    for experto in expertos:
        elegido = getattr(experto, "hiperparametro_elegido", None)
        if elegido is not None:
            valor, puntaje = elegido
            print(f"  {experto.nombre:<26} valor={valor}  (MCC en CV = {puntaje:.3f})")

    print("\nKeywords derivadas del warm-up (experto 4):")
    experto_reglas = expertos[3]
    print("  " + ", ".join(experto_reglas.keywords[:20]))


if __name__ == "__main__":
    main()
