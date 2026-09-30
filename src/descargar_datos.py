"""Descarga el SMS Spam Collection (Almeida et al., 2011) desde el repositorio UCI.

El corpus es el que documenta el paper del dataset: 5.574 mensajes, de los cuales
747 son spam (13,40%). Ese desbalance es el motivo por el que mas adelante no
reportamos accuracy sino Spam Caught y Blocked Hams.
"""

import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"

DIRECTORIO_DATOS = Path(__file__).resolve().parent.parent / "datos"
ARCHIVO_CORPUS = DIRECTORIO_DATOS / "SMSSpamCollection"


def descargar():
    """Baja el zip de UCI y extrae el corpus en datos/."""
    DIRECTORIO_DATOS.mkdir(exist_ok=True)

    if ARCHIVO_CORPUS.exists():
        print(f"El corpus ya esta en {ARCHIVO_CORPUS}, no se vuelve a descargar.")
        return

    print(f"Descargando {URL}")
    with urllib.request.urlopen(URL) as respuesta:
        contenido = respuesta.read()

    print(f"Descargados {len(contenido)} bytes. Extrayendo.")
    with zipfile.ZipFile(io.BytesIO(contenido)) as zip_descargado:
        nombres = zip_descargado.namelist()
        print(f"Archivos en el zip: {nombres}")
        zip_descargado.extractall(DIRECTORIO_DATOS)

    print(f"Corpus extraido en {ARCHIVO_CORPUS}")


if __name__ == "__main__":
    descargar()
