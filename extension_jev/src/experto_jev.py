"""Jev como sexto experto de Hedge.

Jev (TypeSafe AI, septiembre 2026) es un "System One model": no genera texto,
devuelve decisiones tipadas con probabilidades que el fabricante describe como
calibradas. Para spam usamos la primitiva Noul ("¿esto es spam?"), que devuelve
directamente P(spam), y de paso una Choice con el tipo de spam, que solo se usa
en el dashboard.

Por que encaja en el marco de la slide 71. Los expertos de Hedge son funciones
FIJAS. Jev lo es en un sentido todavia mas fuerte que los otros cinco: no se
entrena sobre el warm-up, no ve el stream y no conoce al adversario. Es un
experto zero-shot. Eso lo vuelve el contraste natural del trabajo: el ataque se
calibra contra los pesos log-odds de un filtro bayesiano entrenado en ESTE
corpus (adversario.py), y Jev no comparte ese vocabulario.

DECISION: el prompt no menciona la ofuscacion. Decirle "ojo que los spammers
escriben viiagra" seria darle al defensor informacion sobre el ataque que los
otros expertos no tienen. Si se quiere probar esa variante, se cambia el texto y
se sube VERSION_PROMPT: la cache se indexa por version, asi que no se mezclan.

COSTO. Cada consulta tiene unos 300-400 tokens de entrada. El corpus completo
mas los spam atacados de 20 semillas son unas 11 mil consultas, del orden de 4-5
millones de tokens: a 0,042 USD por millon, unos centavos. Las respuestas se
guardan en disco y nunca se vuelve a consultar el mismo texto.

MODO SIMULADO. Para probar el pipeline sin API key existe un Jev falso
(simular_respuesta). NO es un modelo: es ruido alrededor de la etiqueta. Usa
otra cache, marca todos los resultados como simulados y el dashboard lo muestra
en una franja roja. Nunca usarlo para conclusiones.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

import numpy as np

DIRECTORIO_JEV = Path(__file__).resolve().parent.parent / "resultados" / "jev"

MODELO = "jev-1.13"  # version fijada: jev-latest podria cambiar entre corridas
VERSION_PROMPT = "v1"
UMBRAL = 0.5
CONCURRENCIA = 16

INSTRUCCION_SPAM = "Is this SMS message spam?"
CRITERIO_SPAM = {
    "true": (
        "Unsolicited bulk or commercial message: prizes, contests, premium-rate "
        "numbers, ringtones, subscriptions, promotions, dating or chat services, "
        "phishing or scams."
    ),
    "false": (
        "A personal message between people who know each other, or a legitimate "
        "message the recipient expects."
    ),
}

INSTRUCCION_TIPO = "What kind of message is this?"
TIPOS = {
    "premio": "Claims the recipient won a prize, cash, a holiday or a contest",
    "servicio_premium": "Ringtones, subscriptions, premium-rate numbers or paid SMS services",
    "oferta": "Commercial promotion, discount, phone upgrade or sales offer",
    "citas_chat": "Dating, flirting or adult chat lines",
    "estafa": "Phishing, fake account alerts, urgent requests to call or verify, other scams",
    "no_spam": "Not spam: a personal or legitimate message",
}


def _archivo_cache(simulado):
    nombre = "cache_jev_SIMULADO.jsonl" if simulado else f"cache_jev_{MODELO}_{VERSION_PROMPT}.jsonl"
    return DIRECTORIO_JEV / nombre


def clave(texto):
    return hashlib.sha1(f"{VERSION_PROMPT}\x00{texto}".encode("utf-8")).hexdigest()


class CacheJev:
    """Cache append-only en JSONL: una linea por texto consultado."""

    def __init__(self, simulado=False):
        self.simulado = simulado
        self.archivo = _archivo_cache(simulado)
        self.respuestas = {}
        if self.archivo.exists():
            for linea in self.archivo.read_text(encoding="utf-8").splitlines():
                if linea.strip():
                    registro = json.loads(linea)
                    self.respuestas[registro["clave"]] = registro

    def faltantes(self, textos):
        vistos = set()
        pendientes = []
        for texto in textos:
            k = clave(texto)
            if k not in self.respuestas and k not in vistos:
                vistos.add(k)
                pendientes.append(texto)
        return pendientes

    def guardar(self, registros):
        DIRECTORIO_JEV.mkdir(parents=True, exist_ok=True)
        with self.archivo.open("a", encoding="utf-8") as salida:
            for registro in registros:
                self.respuestas[registro["clave"]] = registro
                salida.write(json.dumps(registro, ensure_ascii=False) + "\n")

    def probabilidad(self, texto):
        return self.respuestas[clave(texto)]["p_spam"]

    def tipo(self, texto):
        return self.respuestas[clave(texto)]["tipo"]


# --- Consulta real a la API ---------------------------------------------------

def _preguntas():
    from typesafe_sdk import Choice, Noul, NoulCriteria

    return {
        "spam": Noul(
            instructions=INSTRUCCION_SPAM,
            criteria=NoulCriteria(true=CRITERIO_SPAM["true"], false=CRITERIO_SPAM["false"]),
        ),
        "tipo": Choice(instructions=INSTRUCCION_TIPO, criteria=TIPOS),
    }


async def _consultar_async(textos, cache, concurrencia):
    from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy

    preguntas = _preguntas()
    semaforo = asyncio.Semaphore(concurrencia)
    lote = []
    hechos = 0
    tokens = 0

    async with AsyncTypeSafeClient(model=MODELO, retry=RetryPolicy(max_retries=5)) as cliente:

        async def una(texto):
            nonlocal hechos, tokens
            async with semaforo:
                respuesta = await cliente.system_one(state={"sms": texto}, questions=preguntas)
            tipo = respuesta.answers["tipo"]
            registro = {
                "clave": clave(texto),
                "p_spam": float(respuesta.answers["spam"].noul),
                "tipo": tipo.choice,
                "confianza_tipo": float(tipo.confidence),
                "modelo": respuesta.model,
            }
            lote.append(registro)
            hechos += 1
            tokens += respuesta.usage.input_tokens
            if len(lote) >= 200:
                cache.guardar(lote[:])
                lote.clear()
                print(f"    Jev: {hechos}/{len(textos)} consultas, {tokens:,} tokens", flush=True)

        try:
            await asyncio.gather(*(una(texto) for texto in textos))
        finally:
            if lote:
                cache.guardar(lote)
    return tokens


# --- Jev simulado (SOLO para probar el pipeline) --------------------------------

def simular_respuesta(texto, etiqueta, atacado):
    """Respuesta FALSA y determinista. No intenta parecerse a Jev.

    Es ruido logistico alrededor de la etiqueta verdadera, un poco mas ruidoso en
    el spam atacado. Sirve para que el pipeline y el dashboard tengan numeros con
    la forma correcta, nada mas.
    """
    semilla = int(hashlib.sha1(texto.encode("utf-8")).hexdigest()[:8], 16)
    generador = np.random.default_rng(semilla)
    margen = 3.2 if etiqueta == 1 else -3.6
    if atacado:
        margen -= 1.0
    p = float(1 / (1 + np.exp(-(margen + generador.normal(0, 1.6)))))
    tipos_spam = ["premio", "servicio_premium", "oferta", "citas_chat", "estafa"]
    tipo = tipos_spam[semilla % 5] if p >= UMBRAL else "no_spam"
    return {"clave": clave(texto), "p_spam": round(p, 4), "tipo": tipo,
            "confianza_tipo": 0.5, "modelo": "SIMULADO"}


def completar_cache(textos, etiquetas=None, atacados=None, simulado=False):
    """Consulta a Jev los textos que todavia no estan en la cache."""
    cache = CacheJev(simulado)
    pendientes = cache.faltantes(textos)
    print(f"  Jev{' SIMULADO' if simulado else ''}: {len(textos)} textos, "
          f"{len(pendientes)} sin consultar todavia", flush=True)
    if not pendientes:
        return cache

    if simulado:
        info = {t: (e, a) for t, e, a in zip(textos, etiquetas, atacados)}
        cache.guardar([simular_respuesta(t, *info[t]) for t in pendientes])
        return cache

    if not os.environ.get("TYPESAFE_API_KEY"):
        raise SystemExit(
            "Falta TYPESAFE_API_KEY. Creala en https://console.typesafe.ai/ y exportala, "
            "o corre con --simular para probar el pipeline con un Jev falso."
        )
    tokens = asyncio.run(_consultar_async(pendientes, cache, CONCURRENCIA))
    print(f"  Jev: listo, {tokens:,} tokens de entrada (~{tokens * 0.042 / 1e6:.3f} USD)")
    return cache


class ExpertoJev:
    """Interfaz igual a la de los otros expertos: predecir(textos) -> {0,1}."""

    def __init__(self, cache):
        self.nombre = "Jev (zero-shot)"
        self.cache = cache

    def probabilidades(self, textos):
        return np.array([self.cache.probabilidad(texto) for texto in textos])

    def predecir(self, textos):
        return (self.probabilidades(textos) >= UMBRAL).astype(int)

    def tipos(self, textos):
        return [self.cache.tipo(texto) for texto in textos]
