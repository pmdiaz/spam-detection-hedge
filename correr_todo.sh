#!/usr/bin/env bash
#
# Corre todo el trabajo, etapa por etapa, en el orden del plan (docs/plan.md, §8).
#
# Uso:
#   ./correr_todo.sh                 corre todas las etapas
#   ./correr_todo.sh --pausa         espera un Enter entre etapa y etapa
#   ./correr_todo.sh --desde 8       arranca en la etapa 8 (saltea las anteriores)
#   ./correr_todo.sh --hasta 3       corre hasta la etapa 3 inclusive
#   ./correr_todo.sh --desde-cero    borra resultados y cache, y recalcula todo
#
# Las opciones se pueden combinar: ./correr_todo.sh --desde 4 --hasta 6 --pausa
#
# Duracion aproximada: 15-20 minutos desde cero. Con los resultados ya
# calculados, bastante menos: el experimento retoma las semillas que ya estan
# en resultados/semillas/ y los expertos entrenados quedan en resultados/cache/.
#
# Todo lo que se imprime queda ademas en resultados/corrida_completa.log.
# Si una etapa falla, el script se detiene ahi.

set -euo pipefail

# --- Configuracion -----------------------------------------------------------

# El python3 del sistema no tiene las librerias; se usa el de pyenv.
# Se puede cambiar con: PYTHON=/otra/ruta/python3 ./correr_todo.sh
PYTHON="${PYTHON:-$HOME/.pyenv/versions/3.12.13/bin/python3}"

RAIZ="$(cd "$(dirname "$0")" && pwd)"
LOG="$RAIZ/resultados/corrida_completa.log"

# Sin esto, Python acumula lo que imprime cuando la salida va a un pipe (el tee
# del log) y lo escribe recien al terminar: el log parece trabado aunque la
# etapa este avanzando.
export PYTHONUNBUFFERED=1

PAUSA=0
DESDE=0
HASTA=99
DESDE_CERO=0

while [ $# -gt 0 ]; do
    case "$1" in
        --pausa)
            PAUSA=1
            ;;
        --desde)
            DESDE="$2"
            shift
            ;;
        --hasta)
            HASTA="$2"
            shift
            ;;
        --desde-cero)
            DESDE_CERO=1
            ;;
        -h|--help)
            sed -n '3,20p' "$0"
            exit 0
            ;;
        *)
            echo "Opcion desconocida: $1  (usar --help)"
            exit 1
            ;;
    esac
    shift
done

if [ ! -x "$PYTHON" ]; then
    echo "No encuentro el interprete de Python en: $PYTHON"
    echo "Indicalo con: PYTHON=/ruta/a/python3 ./correr_todo.sh"
    exit 1
fi

mkdir -p "$RAIZ/resultados"

# Todo lo que sigue se imprime en pantalla y tambien en el log.
exec > >(tee "$LOG") 2>&1

# --- Utilidades --------------------------------------------------------------

etapa() {
    # etapa <numero> <titulo> <script> : corre un script de src/ con su encabezado.
    local numero="$1"
    local titulo="$2"
    local script="$3"

    if [ "$numero" -lt "$DESDE" ] || [ "$numero" -gt "$HASTA" ]; then
        echo "--- Etapa $numero: $titulo (salteada)"
        return
    fi

    echo
    echo "=================================================================="
    echo " Etapa $numero: $titulo"
    echo " src/$script"
    echo "=================================================================="

    local inicio=$SECONDS
    (cd "$RAIZ/src" && "$PYTHON" "$script")
    echo "--- Etapa $numero terminada en $((SECONDS - inicio)) s"

    if [ "$PAUSA" -eq 1 ]; then
        read -r -p "Enter para seguir con la proxima etapa... " < /dev/tty
    fi
}

# --- Preparacion -------------------------------------------------------------

echo "Corrida completa del trabajo: $(date '+%Y-%m-%d %H:%M')"
echo "Python: $PYTHON"

if [ "$DESDE_CERO" -eq 1 ]; then
    # Solo se borra lo que el propio pipeline regenera. No se tocan los
    # resultados archivados de corridas anteriores (resultados/*_v1_* etc.).
    echo "Borrando resultados/cache, resultados/semillas y resultados/resumen.json..."
    rm -rf "$RAIZ/resultados/cache" "$RAIZ/resultados/semillas" "$RAIZ/resultados/resumen.json"
fi

# --- Etapas ------------------------------------------------------------------

etapa 0 "Descarga del SMS Spam Collection"                 descargar_datos.py
etapa 1 "Carga del corpus y split warm-up / stream"         datos.py
etapa 2 "Los cinco expertos contra los baselines de Almeida" verificar_etapa2.py
etapa 3 "El adversario y su calibracion"                    verificar_etapa3.py
etapa 4 "Hedge deterministico y randomizado, y sus cotas"   verificar_etapa4.py
etapa 5 "Estatico, Hedge y SGD online sobre la misma secuencia" verificar_etapa5.py
etapa 6 "Barrido de rho con Hedge y SGD online"             verificar_etapa6.py
etapa 7 "Experimento completo con 20 semillas"              experimento.py
etapa 7 "Agregacion de las 20 semillas"                     agregar_resultados.py
etapa 7 "Robustez: SGD reponderado por 1/rho"              reponderacion_sgd.py
etapa 8 "Figuras del paper"                                 figuras.py

echo
echo "=================================================================="
echo " Listo en $((SECONDS / 60)) min $((SECONDS % 60)) s"
echo " Tablas:   resultados/resumen.json"
echo " Figuras:  figuras/*.pdf"
echo " Log:      resultados/corrida_completa.log"
echo " La etapa 9 (paper) se compila en Overleaf: paper/paper.tex"
echo "=================================================================="
