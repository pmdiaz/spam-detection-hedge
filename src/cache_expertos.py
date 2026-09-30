"""Cache en disco de los expertos entrenados.

La seleccion de hiperparametros por CV anidada tarda unos minutos por semilla.
Como los expertos quedan CONGELADOS despues del warm-up (slide 71), entrenarlos
una vez por semilla y reusarlos es equivalente a reentrenarlos, y hace viable
iterar sobre el experimento.
"""

import pickle
from pathlib import Path

from datos import cargar_corpus, dividir_warmup_y_stream
from expertos import construir_expertos, entrenar_expertos

DIRECTORIO_CACHE = Path(__file__).resolve().parent.parent / "resultados" / "cache"


def obtener_expertos(semilla, verboso=True):
    """Devuelve (warmup, stream, expertos entrenados) para esa semilla."""
    DIRECTORIO_CACHE.mkdir(parents=True, exist_ok=True)
    archivo = DIRECTORIO_CACHE / f"expertos_semilla{semilla}.pkl"

    corpus = cargar_corpus()
    warmup, stream = dividir_warmup_y_stream(corpus, semilla=semilla)

    if archivo.exists():
        expertos = pickle.loads(archivo.read_bytes())
    else:
        if verboso:
            print(f"  entrenando expertos de la semilla {semilla} (CV anidada)...")
        expertos = entrenar_expertos(construir_expertos(), warmup)
        archivo.write_bytes(pickle.dumps(expertos))

    return warmup, stream, expertos


def obtener_indice_estatico(semilla, verboso=True):
    """Indice del experto que funciona como modelo estatico en esa semilla.

    Se elige por CV anidada sobre el warm-up (estatico.py), que tarda unos
    minutos, asi que tambien se cachea.
    """
    from estatico import seleccionar_modelo_estatico

    DIRECTORIO_CACHE.mkdir(parents=True, exist_ok=True)
    archivo = DIRECTORIO_CACHE / f"estatico_semilla{semilla}.txt"

    if archivo.exists():
        return int(archivo.read_text().strip())

    if verboso:
        print(f"  eligiendo el modelo estatico de la semilla {semilla} (CV anidada)...")

    corpus = cargar_corpus()
    warmup, _ = dividir_warmup_y_stream(corpus, semilla=semilla)
    indice, _, _ = seleccionar_modelo_estatico(warmup)

    archivo.write_text(str(indice))
    return indice
