"""Genera notas_orador.html: el guion de la charla, una tarjeta por diapositiva.

El contenido es HTML escrito a mano (fragmentos de confianza), organizado como
datos. Los tiempos acumulados y la barra de tiempo se calculan aca, asi el
documento queda completo y estatico; el JavaScript solo filtra por orador y
recuerda que diapositivas ya se ensayaron.
"""

from pathlib import Path

SALIDA = Path(__file__).parent / "notas_orador.html"

SECCIONES = {1: "El problema", 2: "Hallazgos", 3: "Cierre"}

# Cada diapositiva: numero, seccion, orador, segundos, titulo, mensaje clave,
# guion (lista), pase, datos (lista de pares), referencias, preguntas (pares).
DIAPOSITIVAS = [
    dict(n=1, sec=1, orador="A", seg=30, titulo="Combinar o reentrenar",
         mensaje="Un filtro de spam pelea contra alguien que aprende. Comparamos dos formas de defenderse.",
         guion=[
             "Presentarnos: nombres y materia.",
             "Una frase de entrada: «Cuando el spammer se adapta al filtro, ¿conviene combinar modelos que ya tenemos o reentrenar uno?».",
             "Las palabras de la derecha son reales: así queda un spam después de nuestro ataque.",
         ],
         pase="«Empecemos por el problema.»",
         datos=[("Duración total", "20 min, 18 diapositivas"), ("Orador A", "diapositivas 1 a 10"), ("Orador B", "diapositivas 11 a 18")],
         refs=["Paper y código: github.com/pmdiaz/spam-detection-hedge"],
         preguntas=[]),
    dict(n=2, sec=1, orador="A", seg=75, titulo="Un spammer que aprende a esquivar el filtro",
         mensaje="Con cambios mínimos, el spammer reduce a la mitad lo que atrapa el filtro.",
         guion=[
             "Leer el SMS del primer teléfono. Después señalar en el segundo las palabras en naranja: <em>reply → reeply</em>, <em>win → wiin</em>, <em>stop → stoop</em>.",
             "La palabra en azul, «lol», es la palabra legítima que se agrega.",
             "Aclarar que es un mensaje real del corpus, atacado por nuestro propio código.",
             "Señalar las cifras: el filtro estático pasa de atrapar el 85% del spam a atrapar el 42%.",
             "Remarcar: el mensaje crece una sola palabra. En SMS, agregar decenas de palabras lo delataría por el largo.",
         ],
         pase="«¿Cómo se defiende un filtro de esto? Hay dos caminos.»",
         datos=[("Spam atrapado por el estático", "85 ± 4% sin ataque → 42 ± 11% con ataque"), ("Ataque", "800 palabras más delatoras + 1 legítima"),
                ("Restricción", "la mediana del largo no crece más de 20%"), ("Números", "sin vocal duplican el último carácter: £100 → £1000")],
         refs=["Lowd & Meek (2005), good word attack", "Almeida et al. (2011), SMS Spam Collection", "Paper §4, «Ataque»"],
         preguntas=[("¿Por qué duplicar vocales y no usar leetspeak?",
                     "El leetspeak agrega dígitos, y eso favorecía por casualidad al experto que mira el formato. Duplicar vocales es un ataque puramente léxico.")]),
    dict(n=3, sec=1, orador="A", seg=60, titulo="Dos formas de defenderse",
         mensaje="Combinar no toca los modelos; reentrenar sí.",
         guion=[
             "Combinar: cinco clasificadores entrenados una vez y congelados (los cinco círculos). Hedge solo decide a cuál creerle.",
             "Reentrenar: un único modelo que aprende de cada mensaje etiquetado. La grilla de puntitos verdes representa sus pesos: uno por palabra.",
             "Leer la cita: Lowd y Meek concluyen que lo único que funciona es reentrenar seguido. Esa es la tesis que ponemos a prueba.",
         ],
         pase="«De ahí salen nuestras dos preguntas.»",
         datos=[("Expertos", "Naive Bayes, logística, árbol, reglas, estructural"), ("Estructural", "9 rasgos de formato, no mira palabras"),
                ("SGD online", "regresión logística, hashing 2¹⁸, α = 10⁻⁵")],
         refs=["Freund & Schapire (1997), Hedge", "Lowd & Meek (2005)", "Paper §3.2"],
         preguntas=[("¿Por qué esos cinco expertos?",
                     "Por diversidad: cuatro miran palabras y uno mira formato. Esa diversidad es lo que Hedge aprovecha cuando el ataque rompe a los léxicos.")]),
    dict(n=4, sec=1, orador="A", seg=40, titulo="Dos preguntas",
         mensaje="Las dos preguntas ordenan toda la charla.",
         guion=[
             "Leer las dos preguntas. Los hallazgos 1 y 2 las responden, en ese orden.",
             "Anticipar que el hallazgo 3 son dos precisiones sobre la teoría de la materia, y el 4 lecciones de método.",
             "Mostrar los cuatro círculos de arriba a la derecha: marcan en qué hallazgo estamos durante toda la charla.",
         ],
         pase="«Para responderlas armamos este experimento.»",
         datos=[], refs=["Paper §1"], preguntas=[]),
    dict(n=5, sec=1, orador="A", seg=80, titulo="Cómo lo medimos",
         mensaje="Los tres competidores ven exactamente la misma secuencia de mensajes.",
         guion=[
             "Recorrer la barra de izquierda a derecha: está a escala del corpus.",
             "Warm-up para entrenar; después, en cada ronda se predice, se ve la etiqueta y recién ahí se actualiza.",
             "El tramo oscuro es la mitad atacada: ahí se mide quién se recupera.",
             "Métricas: con 13% de spam, un filtro que no marca nada acierta el 87%. Por eso medimos spam atrapado y legítimo bloqueado por separado.",
         ],
         pase="«Antes de los resultados, un minuto sobre cómo decide Hedge.»",
         datos=[("Corpus", "5.574 SMS, 747 spam (13,4%)"), ("Warm-up", "1.114 mensajes"), ("Stream", "T = 4.460 rondas"),
                ("Spam atacado", "≈ 305 por semilla"), ("No marcar nada", "86,95% de acierto")],
         refs=["Almeida et al. (2011), Tabla 7", "Paper §4"],
         preguntas=[("¿Por qué 20 semillas?",
                     "Cada semilla cambia el orden de los mensajes, el warm-up y el ataque. Con ≈ 305 spams atacados por semilla, una sola corrida varía mucho.")]),
    dict(n=6, sec=1, orador="A", seg=75, titulo="Hedge en un minuto",
         mensaje="Hedge no elige un modelo: reparte la confianza y la mueve hacia el que acierta.",
         guion=[
             "La regla es una sola línea: cada error multiplica el peso del experto por e<sup>−η</sup>.",
             "En cada mensaje se sortea un experto según los pesos.",
             "Presentar a los cinco expertos con sus colores; el violeta, el estructural, va a ser protagonista.",
             "Regret: errores de más contra el mejor experto fijo. La garantía es que crece como √T.",
         ],
         pase="«¿Cuánto rinde esto contra el ataque?»",
         datos=[("η de peor caso", "√(8 ln K / T) = 0,054"), ("Peso inicial", "1/5 cada experto"),
                ("Rasgos del estructural", "largo, dígitos, mayúsculas, links, «!», teléfonos, moneda, tarifas, palabras en mayúscula")],
         refs=["Freund & Schapire (1997)", "Clase 2, slides 71 a 73", "Paper §2"],
         preguntas=[("¿Por qué sortear un experto en vez de votar?", "Lo responde el hallazgo 3: la garantía vale para la versión que sortea.")]),
    dict(n=7, sec=2, orador="A", seg=60, titulo="Combinar recupera casi la mitad, sin reentrenar",
         mensaje="Hedge cubre el 46% de la brecha sin tocar ningún modelo.",
         guion=[
             "Leer la recta de izquierda a derecha: el estático comete 190 errores en la mitad atacada, Hedge 133 y SGD online 73.",
             "El tramo azul es lo que Hedge recupera: el 46% de la distancia entre no adaptarse y reentrenar, solo cambiando a quién le cree.",
             "Reentrenar sigue ganando cuando hay etiquetas, como dicen Lowd y Meek. Pero combinar hace casi la mitad del trabajo.",
         ],
         pase="«¿Qué significa eso en mensajes?»",
         datos=[("Errores sin ataque", "estático 60 · Hedge 72 · determ. 48 · SGD 50"), ("Errores con ataque", "190 ± 32 · 133 ± 10 · 123 ± 11 · 73 ± 6"),
                ("Brecha cubierta", "46 ± 13% (mediana 45%, de 23% a 76%)")],
         refs=["Paper Tabla 1", "Paper §5, «Combinar o reentrenar»"],
         preguntas=[("Con las medias de la tabla da 49%, ¿por qué dicen 46%?",
                     "El 46% es el promedio de la fracción calculada en cada semilla. Las dos cuentas son válidas; reportamos la de por semilla."),
                    ("¿Por qué Hedge comete más errores que el estático antes del ataque?",
                     "Es el precio del seguro: sortear expertos en vez de seguir siempre al mejor. El voto determinístico no paga ese precio.")]),
    dict(n=8, sec=2, orador="A", seg=45, titulo="De 305 spams atacados, Hedge atrapa 52 más",
         mensaje="La misma comparación, contada en mensajes concretos.",
         guion=[
             "Cada punto es un spam que llegó atacado; en color, los que el filtro detecta.",
             "El estático atrapa 128 de 305; Hedge, 180; SGD, 252.",
             "Hedge atrapa 52 más que el estático; SGD, 72 más que Hedge.",
         ],
         pase="«Veamos cómo pasa esto mensaje a mensaje.»",
         datos=[("Spam atrapado, mitad atacada", "42 ± 11% · 59 ± 3% · 83 ± 2%"), ("Spams atacados", "≈ 305 por semilla")],
         refs=["Paper Tabla 1"], preguntas=[]),
    dict(n=9, sec=2, orador="A", seg=90, titulo="Qué pasa mientras dura el ataque (animación)",
         mensaje="El estático cae y no se recupera; Hedge se recupera a medias moviendo el peso; SGD aprende las palabras nuevas.",
         guion=[
             "Dejar correr la animación y narrar sobre ella; con un clic se pausa si hace falta explicar algo.",
             "Fase 1: sin ataque, los tres filtros atrapan parecido, entre 80% y 90% del spam.",
             "Fase 2: llega el ataque y los tres caen. El estático se queda en ~43%: no tiene cómo aprender.",
             "Fase 3: mirar el panel de abajo. El peso de Hedge pasa al experto estructural (violeta) y Hedge sube hasta ~60%.",
             "Fase 4: SGD aprendió las palabras ofuscadas y vuelve casi al nivel previo. Hedge no puede: sus expertos están congelados.",
             "Al final, señalar los contadores: 190, 133 y 73 errores en la mitad atacada.",
         ],
         pase="«¿Y cómo hace Hedge para recuperarse sin aprender palabras?»",
         datos=[("Video", "24 s: 4 s sin ataque, 11 s de ataque, 5 s de resultado"), ("Ventana", "300 mensajes, media de 20 semillas"),
                ("Spam atrapado, mitad atacada", "42 ± 11% · 59 ± 3% · 83 ± 2%")],
         refs=["Paper Fig. 1", "presentacion/animacion.py"], preguntas=[]),
    dict(n=10, sec=2, orador="A", seg=75, titulo="Por qué funciona: la apuesta ya estaba cubierta",
         mensaje="Hedge no había apostado todo al mejor del momento, y después mueve el peso al experto que sobrevive.",
         guion=[
             "Explicar el gráfico: el alto de cada franja es el peso de ese experto en Hedge.",
             "Punto 1: al llegar el ataque, el peso estaba repartido en tercios.",
             "Punto 2: el peso migra al experto estructural en unos 1.000 mensajes, y termina con 0,96.",
             "El estructural sobrevive porque mira el formato, no las palabras.",
         ],
         pase="«Todo esto con todas las etiquetas. Ezequiel muestra qué pasa cuando escasean.» → pasa a B",
         datos=[("Pesos al ataque", "NB 0,36 · estructural 0,33 · otros 0,31"), ("Pesos al final", "estructural 0,96 · NB 0,04")],
         refs=["Paper Fig. 1", "Paper §5"],
         preguntas=[("¿Hedge se olvida de lo que pasó antes?",
                     "No: compite contra el mejor experto fijo de todo el horizonte. Para drift general existe Fixed-Share (Herbster & Warmuth, 1998).")]),
    dict(n=11, sec=2, orador="B", seg=90, titulo="Con pocas etiquetas, combinar le gana a reentrenar",
         mensaje="Reentrenar necesita etiquetas frecuentes; cuando escasean, combinar es más robusto.",
         guion=[
             "Explicar el eje: cuántos mensajes reporta el usuario, de todos a 1 de cada 20.",
             "Con todas las etiquetas, reentrenar gana claramente: 73 contra 133.",
             "A medida que bajan las etiquetas, SGD se degrada mucho más rápido que Hedge.",
             "Las curvas se cruzan entre 1 de cada 5 y 1 de cada 20: en la zona azul, Hedge gana en 15 de 20 semillas y SGD termina peor que no adaptarse.",
         ],
         pase="«Nos objetaron que esto podía ser un artefacto. Lo probamos.»",
         datos=[("Hedge", "133 · 142 · 157 · 189 errores"), ("SGD online", "73 · 100 · 141 · 210 errores"), ("Etiquetas", "100% · 50% · 20% · 5%"),
                ("Gana Hedge", "0 · 0 · 2 · 15 de 20 semillas")],
         refs=["Paper Fig. 3", "Paper §5, «Etiqueta escasa»"],
         preguntas=[("¿Cómo modelan la escasez?",
                     "Cada mensaje se etiqueta con probabilidad ρ. Hedge usa el estimador ℓ/ρ con η = √ρ · η_T. Hedge y SGD ven exactamente las mismas rondas etiquetadas.")]),
    dict(n=12, sec=2, orador="B", seg=75, titulo="No es un artefacto de cómo se pondera",
         mensaje="Reponderar a SGD lo empeora; la ventaja de Hedge es estructural.",
         guion=[
             "Contar la objeción del revisor: SGD perdería por no reponderar sus ejemplos como hace Hedge.",
             "Lo probamos: reponderar empeora a SGD, de 210 a 240 o a 323 errores. La línea azul es Hedge, con 189.",
             "La razón es de conteo: Hedge aprende 5 pesos; reentrenar tiene que aprender un peso por cada palabra nueva.",
             "Lo que sí paga Hedge es varianza: con 5% de etiquetas, cada observación pesa ≈ 4,5 veces más.",
         ],
         pase="«Ahora, dos precisiones sobre la teoría de la materia.»",
         datos=[("Con 5% de etiquetas", "Hedge 189 · SGD 210"), ("SGD reponderado", "× 1/√ρ: 240 · × 1/ρ: 323"),
                ("Estático", "190"), ("Factor de varianza", "1/√0,05 ≈ 4,5")],
         refs=["Auer et al. (2002), estimador ℓ/ρ", "src/reponderacion_sgd.py", "Paper §5"],
         preguntas=[("¿Por qué a Hedge sí le sirve dividir por ρ?",
                     "Porque le evita sesgo al comparar expertos entre sí. A SGD, multiplicar el peso solo le agranda los pasos.")]),
    dict(n=13, sec=2, orador="B", seg=90, titulo="La cota de la teoría no es la del voto pesado",
         mensaje="La garantía vale para el Hedge que sortea, no para el que vota.",
         guion=[
             "En clase, las slides 71 y 73 presentan juntos el voto pesado y la cota.",
             "Pero la cota es del Hedge randomizado. Un jugador predecible se puede simular.",
             "Construimos un adversario que simula al determinístico y etiqueta lo contrario: su regret crece lineal, T/2 (línea roja).",
             "El randomizado, en la misma secuencia, queda en ≈ 14, bajo su cota de 37: casi pegado al piso del gráfico.",
             "Aclarar que en el stream real el determinístico incluso anda mejor: la diferencia es de peor caso.",
         ],
         pase="«La segunda precisión es sobre qué cota usar.»",
         datos=[("Secuencia sintética", "T = 4.000, K = 2"), ("Determinístico", "regret 2.000 = T/2"),
                ("Randomizado", "≈ 14 (cota ≈ 37)"), ("En el stream de spam", "determinístico −2,6 ± 4,9")],
         refs=["Freund & Schapire (1997)", "Cesa-Bianchi & Lugosi (2006)", "Paper §3.1 y Fig. 2B"],
         preguntas=[("Si el determinístico anda mejor en la práctica, ¿por qué importa?",
                     "Porque solo el randomizado tiene garantía contra un adversario. En datos benignos se puede usar el determinístico, pero sin cobertura de peor caso.")]),
    dict(n=14, sec=2, orador="B", seg=75, titulo="Cada cota vale para su tasa de aprendizaje",
         mensaje="Hay dos cotas y cada una vale solo para su propio η.",
         guion=[
             "La cota de peor caso vale para η sintonizado por T; la cota small-loss, para η sintonizado por la pérdida del mejor experto.",
             "Las dos se cumplen en las 20 semillas: cada línea llena queda bajo su línea punteada del mismo color.",
             "La small-loss da la mitad de regret, pero necesita información que bajo drift no tenemos.",
             "Señalar que la cota small-loss cambia de pendiente con el ataque, porque sigue la pérdida acumulada.",
         ],
         pase="«Tres lecciones que sirven fuera de este trabajo.»",
         datos=[("η de peor caso", "0,054 → regret 31,2 ± 1,5 · cota 59,9"), ("η small-loss", "≈ 0,128 → regret 15,1 ± 1,4 · cota 25,2"),
                ("Constante de la slide", "√(2T ln K) = 119,8, el doble")],
         refs=["Freund & Schapire (1997), Teorema 2 y Lema 4", "Paper §2 y Fig. 2A"],
         preguntas=[("¿Por qué la cota de la slide es el doble?",
                     "Es una versión conservadora. La derivación por el lema de Hoeffding da √(T ln K / 2) en t = T.")]),
    dict(n=15, sec=2, orador="B", seg=90, titulo="Tres cosas que sirven fuera de este trabajo",
         mensaje="Medir bien, validar lo que importa y asegurarse de que algún experto sobreviva.",
         guion=[
             "La accuracy engaña con datos desbalanceados.",
             "La validación cruzada sobre datos sin drift no sirve para elegir hiperparámetros de adaptación: tuvimos que fijar el α de SGD.",
             "Combinar solo funciona si algún experto sobrevive: con la primera versión del estructural, Hedge no recuperaba nada.",
         ],
         pase="«¿Qué hacemos con esto?»",
         datos=[("No marcar nada", "86,95% de acierto"), ("CV eligió α = 10⁻⁴", "en 8 de 20 semillas: 125–153 errores contra 65–83"),
                ("Estructural simple", "0,995 del peso en el estático dañado (semilla de desarrollo)")],
         refs=["Paper §5 y §6", "docs/plan.md §4"],
         preguntas=[("¿Por qué el estático es Naive Bayes y no el que elige la validación cruzada?",
                     "La CV habría elegido al estructural en 6 de 20 semillas. El ataque se construye contra un filtro bayesiano, así que el estático tiene que ser ese filtro.")]),
    dict(n=16, sec=3, orador="B", seg=60, titulo="Cuándo combinar y cuándo reentrenar",
         mensaje="Lowd y Meek tenían razón a medias: reentrenar seguido funciona si hay etiquetas seguido.",
         guion=[
             "Con etiquetas abundantes, reentrenar.",
             "Con etiquetas escasas, combinar expertos diversos, con al menos uno robusto al ataque.",
             "Siempre, medir spam atrapado y legítimo bloqueado por separado.",
             "Cerrar con la pregunta abierta y aclarar que no la probamos.",
         ],
         pase="«Y lo que este trabajo no muestra.»",
         datos=[("Con todas las etiquetas", "SGD 73 · Hedge 133 errores"), ("Con 5% de etiquetas", "Hedge 189 · SGD 210 errores")],
         refs=["Paper §6 y Conclusión"], preguntas=[]),
    dict(n=17, sec=3, orador="B", seg=45, titulo="Lo que este trabajo no muestra",
         mensaje="Los límites son reales, y los más importantes son dos.",
         guion=[
             "No leer las seis: mencionar las dos principales.",
             "El drift es sintético, porque el corpus no tiene fechas.",
             "El experto robusto lo es para este ataque en particular.",
         ],
         pase="«Gracias. ¿Preguntas?»",
         datos=[("Adversario adaptativo", "degradaría √T a T^(2/3)")],
         refs=["Cesa-Bianchi, Dekel & Shamir (2013)", "Paper §6"], preguntas=[]),
    dict(n=18, sec=3, orador="B", seg=15, titulo="¿Preguntas?",
         mensaje="Abrir preguntas.",
         guion=["Agradecer y abrir preguntas. Repartir las respuestas según el tema de cada uno."],
         pase="",
         datos=[("Repositorio", "github.com/pmdiaz/spam-detection-hedge")],
         refs=["Verificar antes de la charla que el repositorio sea público."], preguntas=[]),
]

PREGUNTAS_GENERALES = [
    ("¿Se generaliza a email?",
     "El corpus es de SMS. El mecanismo, que reentrenar necesita muchos más parámetros que combinar, no depende del medio, pero no lo medimos en email."),
    ("¿Qué pasa con un adversario que reacciona?",
     "Hace falta policy regret, y con memoria acotada las tasas se degradan de √T a T^(2/3) (Cesa-Bianchi, Dekel & Shamir, 2013). No lo corrimos."),
    ("¿Por qué no usaron EXP3 para el caso con poca información?",
     "En clasificación binaria, saber si la predicción jugada acertó revela la etiqueta, y con ella la pérdida de todos los expertos: el feedback bandit colapsa en información completa."),
    ("¿Y si el modelo que reentrena fuera uno de los expertos de Hedge?",
     "Es la pregunta abierta natural. No lo probamos."),
    ("¿Cómo eligieron las 800 palabras del ataque?",
     "Calibrando hasta reducir a la mitad la detección del estático, sin que la mediana del largo crezca más de 20%."),
]

REFERENCIAS = [
    "Freund, Y. y Schapire, R. E. (1997). A decision-theoretic generalization of on-line learning and an application to boosting. <em>JCSS</em>, 55(1).",
    "Auer, P., Cesa-Bianchi, N., Freund, Y. y Schapire, R. E. (2002). The nonstochastic multiarmed bandit problem. <em>SIAM J. Comput.</em>, 32(1).",
    "Lowd, D. y Meek, C. (2005). Good word attacks on statistical spam filters. <em>CEAS</em>.",
    "Almeida, T. A., Gómez Hidalgo, J. M. y Yamakami, A. (2011). Contributions to the study of SMS spam filtering. <em>DocEng'11</em>.",
    "Cesa-Bianchi, N., Dekel, O. y Shamir, O. (2013). Online learning with switching costs and other adaptive adversaries. arXiv:1302.4387.",
    "Herbster, M. y Warmuth, M. K. (1998). Tracking the best expert. <em>Machine Learning</em>, 32(2).",
    "Cesa-Bianchi, N. y Lugosi, G. (2006). <em>Prediction, Learning, and Games</em>. Cambridge University Press.",
    "Fraiman, D. (2026). Tópicos Avanzados en Ciencia de Datos, clase 2 (slides 57 a 79).",
]


def mmss(segundos):
    return f"{segundos // 60}:{segundos % 60:02d}"


def tarjeta(d, inicio):
    guion = "".join(f"<li>{g}</li>" for g in d["guion"])
    pase = f'<p class="pase"><span class="etq">Pase</span>{d["pase"]}</p>' if d["pase"] else ""
    datos = "".join(f"<div class='dato'><dt>{k}</dt><dd>{v}</dd></div>" for k, v in d["datos"])
    datos_html = f"<h4>Datos a mano</h4><dl class='datos'>{datos}</dl>" if d["datos"] else ""
    refs = "".join(f"<li>{r}</li>" for r in d["refs"])
    refs_html = f"<h4>Referencias</h4><ul class='refs'>{refs}</ul>" if d["refs"] else ""
    preg = "".join(f"<div class='qa'><p class='q'>{q}</p><p class='a'>{a}</p></div>" for q, a in d["preguntas"])
    preg_html = f"<h4>Si preguntan</h4>{preg}" if d["preguntas"] else ""
    fin = inicio + d["seg"]
    return f"""
<article class="diapo" data-orador="{d['orador']}" id="d{d['n']}">
  <header class="diapo-cab">
    <span class="num">{d['n']:02d}</span>
    <h3>{d['titulo']}</h3>
    <span class="chip chip-{d['orador'].lower()}">Orador {d['orador']}</span>
    <span class="tiempo"><b>{mmss(d['seg'])}</b> · {mmss(inicio)}–{mmss(fin)}</span>
    <label class="ensayo"><input type="checkbox" id="ensayo-{d['n']}" data-n="{d['n']}"> Ensayada</label>
  </header>
  <div class="diapo-cuerpo">
    <div class="trabajo">
      <p class="mensaje">{d['mensaje']}</p>
      <ul class="guion">{guion}</ul>
      {pase}
    </div>
    <aside class="apoyo">{datos_html}{refs_html}{preg_html}</aside>
  </div>
</article>"""


def construir():
    total = sum(d["seg"] for d in DIAPOSITIVAS)
    total_a = sum(d["seg"] for d in DIAPOSITIVAS if d["orador"] == "A")
    total_b = total - total_a
    numeros_a = [d["n"] for d in DIAPOSITIVAS if d["orador"] == "A"]
    numeros_b = [d["n"] for d in DIAPOSITIVAS if d["orador"] == "B"]
    rango_a = f"{min(numeros_a)}–{max(numeros_a)}"
    rango_b = f"{min(numeros_b)}–{max(numeros_b)}"

    segmentos = "".join(
        f"<a class='seg seg-{d['orador'].lower()}' href='#d{d['n']}' style='flex:{d['seg']}' "
        f"title='{d['n']}. {d['titulo']} ({mmss(d['seg'])})'>{d['n']}</a>" for d in DIAPOSITIVAS)

    cuerpo = []
    inicio = 0
    seccion_actual = None
    for d in DIAPOSITIVAS:
        if d["sec"] != seccion_actual:
            seccion_actual = d["sec"]
            cuerpo.append(f"<h2 class='seccion'><span>{seccion_actual}</span>{SECCIONES[seccion_actual]}</h2>")
        cuerpo.append(tarjeta(d, inicio))
        inicio += d["seg"]

    preguntas = "".join(f"<div class='qa'><p class='q'>{q}</p><p class='a'>{a}</p></div>" for q, a in PREGUNTAS_GENERALES)
    referencias = "".join(f"<li>{r}</li>" for r in REFERENCIAS)

    return PLANTILLA.format(
        total=mmss(total), total_a=mmss(total_a), total_b=mmss(total_b), margen=mmss(20 * 60 - total),
        rango_a=rango_a, rango_b=rango_b, cantidad=len(DIAPOSITIVAS),
        segmentos=segmentos, cuerpo="".join(cuerpo), preguntas=preguntas, referencias=referencias)


PLANTILLA = """<meta charset="utf-8">
<title>Guion de Combinar o reentrenar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: una columna de tarjetas por diapositiva; cada tarjeta se parte en
   espacio de trabajo (guion, izquierda) y apoyo (datos y referencias, derecha). */
:root {{
  --bg: #F3F4F6; --card: #FFFFFF; --ink: #1E2430; --ink-2: #535C6C; --muted: #858D9C;
  --line: #E1E4EA; --soft: #F0F2F5;
  --a: #2A64B0; --a-tint: #E5EEF9; --b: #5747AD; --b-tint: #ECE9F8;
  --estatico: #D9602F; --hedge: #2A78D6; --sgd: #159A6B; --estructural: #4A3AA7;
  --sans: "Public Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #14171D; --card: #1C2028; --ink: #E6E9EF; --ink-2: #AFB6C3; --muted: #7E8696;
    --line: #2B303A; --soft: #222731;
    --a: #8DB7EE; --a-tint: #1D2B3F; --b: #ADA3F1; --b-tint: #29253F;
    --estatico: #EE8A60; --hedge: #6FA6EA; --sgd: #3CC594; --estructural: #9C91EC;
    color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #14171D; --card: #1C2028; --ink: #E6E9EF; --ink-2: #AFB6C3; --muted: #7E8696;
  --line: #2B303A; --soft: #222731;
  --a: #8DB7EE; --a-tint: #1D2B3F; --b: #ADA3F1; --b-tint: #29253F;
  --estatico: #EE8A60; --hedge: #6FA6EA; --sgd: #3CC594; --estructural: #9C91EC;
  color-scheme: dark;
}}

* {{ box-sizing: border-box; }}
body {{ background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.55; }}
.pagina {{ max-width: 1120px; margin: 0 auto; padding-inline: 20px; padding-block: 36px 64px; display: grid; gap: 28px; }}

.cabecera {{ display: grid; gap: 18px; }}
.sobre {{ font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0; }}
h1 {{ font-size: clamp(28px, 4vw, 38px); line-height: 1.15; margin: 0; font-weight: 700; letter-spacing: -.01em; text-wrap: balance; }}
.resumen {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1px; background: var(--line);
  border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
.resumen div {{ background: var(--card); padding: 12px 16px; }}
.resumen dt {{ font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
.resumen dd {{ margin: 2px 0 0; font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }}

.linea {{ display: grid; gap: 8px; }}
.linea-barra {{ display: flex; gap: 2px; height: 34px; border-radius: 8px; overflow: hidden; }}
.seg {{ display: flex; align-items: center; justify-content: center; font: 500 12px var(--mono); text-decoration: none; min-width: 0; }}
.seg-a {{ background: var(--a-tint); color: var(--a); }}
.seg-b {{ background: var(--b-tint); color: var(--b); }}
.seg:hover, .seg:focus-visible {{ outline: 2px solid currentColor; outline-offset: -2px; }}
.linea-leyenda {{ display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: var(--ink-2); }}

.controles {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px 20px; position: sticky; top: env(safe-area-inset-top, 0px);
  z-index: 2; background: var(--bg); padding-block: 10px; border-bottom: 1px solid var(--line); }}
.filtro {{ display: inline-flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: var(--card); }}
.filtro button {{ font: 500 13px var(--sans); color: var(--ink-2); background: none; border: 0; padding: 7px 14px; cursor: pointer; }}
.filtro button + button {{ border-left: 1px solid var(--line); }}
.filtro button[aria-pressed="true"] {{ background: var(--ink); color: var(--card); }}
.filtro button:focus-visible {{ outline: 2px solid var(--hedge); outline-offset: -2px; }}
.colores {{ display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; color: var(--ink-2); }}
.colores span::before {{ content: ""; display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; background: var(--c); }}
.progreso {{ margin-left: auto; font: 500 13px var(--mono); color: var(--muted); }}

.seccion {{ display: flex; align-items: baseline; gap: 12px; margin: 14px 0 0; font-size: 13px; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
.seccion span {{ font-family: var(--mono); color: var(--ink-2); }}

.diapo {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }}
.diapo-cab {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; padding: 14px 20px; border-bottom: 1px solid var(--line); }}
.num {{ font: 500 13px var(--mono); color: var(--muted); }}
.diapo-cab h3 {{ margin: 0; font-size: 17px; font-weight: 600; flex: 1 1 260px; min-width: 0; text-wrap: balance; }}
.chip {{ font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; white-space: nowrap; }}
.chip-a {{ background: var(--a-tint); color: var(--a); }}
.chip-b {{ background: var(--b-tint); color: var(--b); }}
.tiempo {{ font: 400 13px var(--mono); color: var(--ink-2); white-space: nowrap; font-variant-numeric: tabular-nums; }}
.tiempo b {{ font-weight: 500; color: var(--ink); }}
.ensayo {{ display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--ink-2); cursor: pointer; }}
.ensayo input {{ accent-color: var(--hedge); width: 16px; height: 16px; }}
.diapo.hecha .diapo-cab {{ background: var(--soft); }}

.diapo-cuerpo {{ display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr); }}
.trabajo {{ padding: 18px 22px 20px; display: grid; gap: 12px; align-content: start; min-width: 0; }}
.apoyo {{ padding: 18px 22px 20px; background: var(--soft); border-left: 1px solid var(--line); display: grid; gap: 10px; align-content: start; min-width: 0; }}
.mensaje {{ margin: 0; font-size: 17px; font-weight: 600; line-height: 1.4; max-width: 62ch; }}
.guion {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; color: var(--ink); max-width: 66ch; }}
.guion li::marker {{ color: var(--muted); }}
.pase {{ margin: 4px 0 0; font-style: italic; color: var(--ink-2); display: flex; gap: 10px; align-items: baseline; }}
.etq {{ font: 600 11px var(--sans); font-style: normal; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }}
.apoyo h4 {{ margin: 6px 0 0; font-size: 11px; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); }}
.apoyo h4:first-child {{ margin-top: 0; }}
.datos {{ margin: 0; display: grid; gap: 6px; }}
.dato dt {{ font-size: 12px; color: var(--ink-2); }}
.dato dd {{ margin: 0; font: 500 13px/1.45 var(--mono); color: var(--ink); font-variant-numeric: tabular-nums; }}
.refs {{ margin: 0; padding-left: 18px; font-size: 13px; color: var(--ink-2); display: grid; gap: 3px; }}
.qa {{ display: grid; gap: 2px; }}
.qa .q {{ margin: 0; font-size: 13px; font-weight: 600; }}
.qa .a {{ margin: 0; font-size: 13px; color: var(--ink-2); }}

.final {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 20px; }}
.caja {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 18px 22px; display: grid; gap: 12px; align-content: start; }}
.caja h2 {{ margin: 0; font-size: 13px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
.caja .qa .q {{ font-size: 14px; }}
.caja .qa .a {{ font-size: 14px; }}
.biblio {{ margin: 0; padding-left: 18px; display: grid; gap: 8px; font-size: 13px; color: var(--ink-2); }}
.checklist {{ margin: 0; padding-left: 18px; display: grid; gap: 6px; font-size: 14px; }}

@media (max-width: 760px) {{
  .diapo-cuerpo, .final {{ grid-template-columns: minmax(0, 1fr); }}
  .apoyo {{ border-left: 0; border-top: 1px solid var(--line); }}
  .progreso {{ margin-left: 0; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ scroll-behavior: auto !important; }} }}
@media print {{
  .controles, .ensayo {{ display: none; }}
  .diapo {{ break-inside: avoid; }}
  body {{ background: #FFFFFF; }}
}}
</style>

<main class="pagina">
  <header class="cabecera">
    <p class="sobre">Notas del orador · Tópicos Avanzados en Ciencia de Datos · UdeSA</p>
    <h1>Combinar o reentrenar: guion de la charla</h1>
    <dl class="resumen">
      <div><dt>Duración</dt><dd>20:00</dd></div>
      <div><dt>Guion</dt><dd>{total}</dd></div>
      <div><dt>Orador A · {rango_a}</dt><dd>{total_a}</dd></div>
      <div><dt>Orador B · {rango_b}</dt><dd>{total_b}</dd></div>
      <div><dt>Margen</dt><dd>{margen}</dd></div>
    </dl>
    <div class="linea">
      <div class="linea-barra" role="navigation" aria-label="Diapositivas, con ancho proporcional a su tiempo">{segmentos}</div>
      <div class="linea-leyenda"><span>Cada bloque es una diapositiva; su ancho es su tiempo. Tocá un bloque para ir a la tarjeta.</span></div>
    </div>
  </header>

  <div class="controles">
    <div class="filtro" role="group" aria-label="Filtrar por orador">
      <button type="button" id="filtro-todos" data-filtro="todos" aria-pressed="true">Todas</button>
      <button type="button" id="filtro-a" data-filtro="A" aria-pressed="false">Orador A</button>
      <button type="button" id="filtro-b" data-filtro="B" aria-pressed="false">Orador B</button>
    </div>
    <div class="colores" aria-label="Colores de las diapositivas">
      <span style="--c: var(--estatico)">Estático</span><span style="--c: var(--hedge)">Hedge</span>
      <span style="--c: var(--sgd)">SGD online</span><span style="--c: var(--estructural)">Estructural</span>
    </div>
    <span class="progreso" id="progreso">0 de {cantidad} ensayadas</span>
  </div>

  {cuerpo}

  <section class="final">
    <div class="caja">
      <h2>Preguntas probables del público</h2>
      {preguntas}
    </div>
    <div class="caja">
      <h2>Antes de ensayar en Canva</h2>
      <ul class="checklist">
        <li>Importar <code>combinar_o_reentrenar.pptx</code> desde Crear → Importar archivo.</li>
        <li>Canva no importa las transiciones de PowerPoint: agregar «Desvanecer» desde Animar.</li>
        <li>Los gráficos son imágenes generadas por <code>visuales.py</code> desde los resultados: para cambiar uno, regenerarlo, no editarlo a mano.</li>
        <li>Revisar fuentes: titulares en Georgia y texto en Arial. Si Canva no tiene Georgia, elegir otra serif para todos los titulares.</li>
        <li>La diapositiva 9 es un video (<code>visuales/animacion_ataque.mp4</code>). Si el PDF importado no lo trae, subir el MP4 a mano y activar la reproducción automática.</li>
        <li>Confirmar que el repositorio sea público antes de mostrar el enlace.</li>
      </ul>
      <h2>Referencias</h2>
      <ol class="biblio">{referencias}</ol>
    </div>
  </section>
</main>

<script>
(function () {{
  var CLAVE = "guion-combinar-reentrenar-v3"; // v3: mazo de 18 diapositivas, otra numeracion
  var estado = {{ filtro: "todos", ensayadas: [] }};
  try {{
    var guardado = JSON.parse(localStorage.getItem(CLAVE) || "null");
    if (guardado) estado = guardado;
  }} catch (e) {{}}

  function guardar() {{
    try {{ localStorage.setItem(CLAVE, JSON.stringify(estado)); }} catch (e) {{}}
  }}

  var diapos = Array.prototype.slice.call(document.querySelectorAll(".diapo"));
  var botones = Array.prototype.slice.call(document.querySelectorAll(".filtro button"));
  var casillas = Array.prototype.slice.call(document.querySelectorAll(".ensayo input"));
  var progreso = document.getElementById("progreso");

  function aplicarFiltro() {{
    diapos.forEach(function (d) {{
      d.hidden = estado.filtro !== "todos" && d.dataset.orador !== estado.filtro;
    }});
    botones.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(b.dataset.filtro === estado.filtro));
    }});
  }}

  function aplicarEnsayos() {{
    casillas.forEach(function (c) {{
      var hecha = estado.ensayadas.indexOf(c.dataset.n) !== -1;
      c.checked = hecha;
      c.closest(".diapo").classList.toggle("hecha", hecha);
    }});
    progreso.textContent = estado.ensayadas.length + " de " + casillas.length + " ensayadas";
  }}

  botones.forEach(function (b) {{
    b.addEventListener("click", function () {{
      estado.filtro = b.dataset.filtro;
      aplicarFiltro();
      guardar();
    }});
  }});
  casillas.forEach(function (c) {{
    c.addEventListener("change", function () {{
      var i = estado.ensayadas.indexOf(c.dataset.n);
      if (c.checked && i === -1) estado.ensayadas.push(c.dataset.n);
      if (!c.checked && i !== -1) estado.ensayadas.splice(i, 1);
      aplicarEnsayos();
      guardar();
    }});
  }});

  aplicarFiltro();
  aplicarEnsayos();
}})();
</script>
"""

if __name__ == "__main__":
    SALIDA.write_text(construir(), encoding="utf-8")
    total = sum(d["seg"] for d in DIAPOSITIVAS)
    print(f"escrito {SALIDA} · {len(DIAPOSITIVAS)} diapositivas · guion {mmss(total)}")
