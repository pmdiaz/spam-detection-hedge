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
figuras/                  Figuras del paper (se versionan los PDF; los PNG son vistas previas)
paper/                    paper.tex y referencias.bib
resultados/               Resultados y cache (no versionados, se regeneran)
correr_todo.sh            Corre todo el trabajo, etapa por etapa
```

## Cómo reproducir los resultados

Todo el trabajo se corre con un solo script, desde la raíz del repo. Para reproducirlo **desde
cero**, sin reutilizar nada calculado antes:

```bash
./correr_todo.sh --desde-cero
```

Qué hace:

1. **Borra lo que el propio script regenera:** `resultados/cache/` (los expertos entrenados),
   `resultados/semillas/` (los resultados de cada semilla) y `resultados/resumen.json`. No toca
   los resultados de corridas anteriores que se hayan archivado en otras carpetas de
   `resultados/`.
2. **Corre las etapas en orden**, cada una con su verificación: descarga de los datos (0), carga y
   división del corpus (1), los cinco expertos (2), el ataque y su calibración (3), Hedge y sus
   cotas (4), los tres competidores (5), el barrido de ρ (6), el experimento con 20 semillas y su
   agregación (7) y las figuras (8). La etapa 9, el paper, se compila en Overleaf.

Tarda entre 15 y 25 minutos, según la máquina; a batería, más. Lo que imprime se ve en pantalla y
queda en `resultados/corrida_completa.log`, que se actualiza en vivo. Si una etapa falla, el script
se detiene ahí.

Las salidas son `resultados/resumen.json` (las cifras del paper) y `figuras/*.pdf`. La corrida es
determinística: todo el azar usa semillas fijas, así que reproduce las mismas cifras y los mismos
PDF, byte a byte.

Otras opciones, que se pueden combinar:

| Comando | Para qué |
|---|---|
| `./correr_todo.sh` | Corre todo, pero reutiliza lo ya calculado: los expertos cacheados y las semillas completas. Mucho más rápido |
| `./correr_todo.sh --pausa` | Espera un Enter entre etapa y etapa, para ir leyendo cada verificación |
| `./correr_todo.sh --desde 7` | Arranca en la etapa 7 y saltea las anteriores |
| `./correr_todo.sh --hasta 3` | Corre hasta la etapa 3 inclusive |
| `./correr_todo.sh --help` | Muestra la ayuda |

El script usa el Python de `~/.pyenv/versions/3.12.13/bin/python3`. Para usar otro:
`PYTHON=/ruta/a/python3 ./correr_todo.sh --desde-cero`.

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

Implementación completa: las etapas 0 a 8 están verificadas, el experimento con 20 semillas está
corrido y las figuras están generadas. El paper (`paper/paper.tex`) está compilado en Overleaf,
que es la versión que manda para el texto. Los resultados y las decisiones de diseño están en
[`docs/plan.md`](docs/plan.md).
