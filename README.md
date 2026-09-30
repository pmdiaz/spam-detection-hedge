# Aprendizaje online con Hedge para detección de spam

**Autores:** Pablo Díaz y Ezequiel Martinez

Trabajo final de **Tópicos Avanzados en Ciencia de Datos** (MCD210, Maestría en Ciencia de Datos,
UdeSA — Daniel Fraiman). Paper de ~3 páginas que extiende el caso de detección de spam de la
clase 2 a un esquema de aprendizaje online con Hedge.

## Qué investiga

Ante un spammer que se adapta para evadir el filtro:

1. **¿Combinar o reentrenar?** ¿Cuánto del beneficio viene de *combinar* clasificadores fijos y
   cuánto de *reentrenar* el modelo? Lowd & Meek (2005) concluyeron que lo único que funciona es
   reentrenar seguido; acá lo ponemos a prueba.
2. **¿Cuánta etiqueta hace falta?** En producción el usuario reporta solo algunos mensajes.
   Medimos cómo se degrada el regret cuando la etiqueta se observa con probabilidad ρ.

Y de paso se corrige una inconsistencia de la teórica: el algoritmo de la slide 71 (voto pesado
determinístico) y la cota de la slide 73 (`√(2T log K)`) no corresponden al mismo algoritmo.

## Estructura

```
docs/plan.md              Plan de trabajo completo: marco formal, diseño experimental,
                          etapas, limitaciones y glosario
docs/resumen_papers.md    Resumen de los cinco papers de referencia y qué aporta cada uno
referencias/              PDFs de los papers (no versionados, ver referencias/README.md)
src/                      Código del experimento
figuras/                  Figuras generadas (no versionadas)
paper/                    paper.tex y referencias.bib
```

## Datos

**SMS Spam Collection** (Almeida et al., 2011): 5.574 mensajes, 747 spam (13,40%).
Se descarga con `src/descargar_datos.py` desde el repositorio UCI.

## Entorno

```
~/.pyenv/versions/3.12.13/bin/python3
numpy 2.4.4 · pandas 3.0.2 · scikit-learn 1.8.0 · matplotlib 3.10.9
```

No hay LaTeX local: `paper/paper.tex` se compila en Overleaf.

## Estado

Diseño cerrado y revisado contra la bibliografía. Queda una decisión abierta (si corremos la
variante con adversario adaptativo) y la implementación, que va por etapas según
[`docs/plan.md`](docs/plan.md) §8.
