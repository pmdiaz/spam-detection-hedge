"""Agrega una transicion de fundido a cada diapositiva de un .pptx.

pptxgenjs no escribe transiciones. Segun el esquema de PresentationML, el
elemento <p:transition> va despues de <p:clrMapOvr> (o de <p:cSld> si no hay
clrMapOvr) y antes de <p:timing>. Se reescribe el zip copiando el resto tal cual.
"""
import re
import sys
import zipfile

entrada, salida = sys.argv[1], sys.argv[2]
TRANSICION = '<p:transition spd="med"><p:fade/></p:transition>'

with zipfile.ZipFile(entrada) as origen, zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as destino:
    cantidad = 0
    for item in origen.infolist():
        datos = origen.read(item.filename)
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", item.filename):
            xml = datos.decode("utf-8")
            if "<p:transition" not in xml:
                if "</p:clrMapOvr>" in xml:
                    xml = xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + TRANSICION, 1)
                else:
                    xml = xml.replace("</p:cSld>", "</p:cSld>" + TRANSICION, 1)
                cantidad += 1
            datos = xml.encode("utf-8")
        destino.writestr(item, datos)
print(f"transiciones agregadas: {cantidad}")
