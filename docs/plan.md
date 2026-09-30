# Plan de trabajo — Paper: aprendizaje online con Hedge para detección de spam

**Materia:** Tópicos Avanzados en Ciencia de Datos (MCD210) — Daniel Fraiman
**Formato de entrega:** ~3 páginas, LaTeX a dos columnas (compilación en Overleaf), en español
**Origen del tema:** `referencias/clase_2_ventas_online.pdf`, slide 79 ("Ideas para el paper"), ítem 3:
*"Extender el caso de detección de spam a un clasificador que se reentrena online con Hedge,
y comparar contra un modelo estático."*
**Estado:** diseño revisado contra la bibliografía (ver [`resumen_papers.md`](resumen_papers.md)) —
queda 1 decisión abierta (§9)

---

## 1. Preguntas de investigación

El paper responde dos preguntas que la teórica plantea pero no mide, y de paso corrige una
inconsistencia de las slides.

1. **¿Combinar o reentrenar?** Ante un adversario que se adapta, ¿cuánto del beneficio viene de
   *combinar* expertos y cuánto de *reentrenar* el modelo? La slide 69 presenta tres modelos
   distintos (elegir θ, elegir un clasificador, pesar K clasificadores) pero no los compara entre sí,
   y la consigna de la slide 79 los confunde al proponer solo "Hedge vs. estático".

   Lowd & Meek (2005) concluyen que *"the only remedy we know of is frequent retraining"*. Esta
   pregunta pone a prueba esa afirmación: ¿alcanza con cambiar a quién le creés, sin reentrenar?

2. **¿Cuánta etiqueta hace falta?** Hedge supone que en cada ronda se observa la pérdida de los K
   expertos (información completa, slide 57). En producción la etiqueta verdadera es escasa: el
   usuario reporta solo algunos mensajes. Modelamos que `y_t` se revela con probabilidad ρ y medimos
   cómo se degrada el regret al bajar ρ.

**Observación teórica que sale de paso:** el algoritmo de la slide 71 (voto pesado determinístico) y
la cota de la slide 73 (`√(2T log K)`) **no corresponden al mismo algoritmo**. Ver §3.

**Tesis:** bajo drift adversarial, combinar expertos fijos recupera gran parte de la pérdida de
desempeño sin necesidad de reentrenar, pero solo mientras exista al menos un experto fijo bueno —
y esa condición es exactamente el límite de la garantía de Hedge.

---

## 2. Marco formal

Protocolo de aprendizaje online de la slide 57, con pérdida 0-1.

En cada ronda `t = 1, ..., T`:

1. El entorno (adversario) presenta un contexto `x_t ∈ X` (el mensaje) y fija una etiqueta `y_t ∈ {0,1}`.
2. El jugador predice `ŷ_t ∈ {0,1}`.
3. Se revela `y_t` y el jugador sufre `ℓ_t = 1{ŷ_t ≠ y_t}`.

Los K expertos son **funciones fijas** `f^(1), ..., f^(K)`, tal como los define la slide 71:
se entrenan una vez sobre un tramo de warm-up y quedan congelados. Su pérdida en la ronda t es
`ℓ_t(i) = 1{f^(i)(x_t) ≠ y_t}`.

**Regret**, contra el mejor experto fijo en retrospectiva:

```
R_T = Σ_t 1{ŷ_t ≠ y_t}  −  min_i Σ_t 1{f^(i)(x_t) ≠ y_t}
```

### Por qué esta definición de regret es legítima acá

Cesa-Bianchi, Dekel & Shamir (2013) muestran que, contra un adversario **adaptativo**, esta
definición es *"clearly inadequate"*: el término "qué hubiera pasado si jugaba `i` en esta ronda" no
tiene interpretación si el adversario venía reaccionando a nuestras jugadas. En ese caso hace falta
**policy regret**, donde la acción alternativa se juega desde el principio. Y sin restringir la
memoria del adversario, el regret lineal es inevitable para cualquier algoritmo (Arora et al. 2012).

Nuestro adversario es **oblivious** (§5), así que la definición de arriba es la correcta. Las cotas
originales de Hedge y de EXP3 se prueban bajo el mismo supuesto.

### Las dos cotas

**Cota de peor caso** (la de la slide 73): `R_T ≤ √(2 T ln K)`.

**Cota fina** (Freund & Schapire 1997, Lema 4), en función de la pérdida del mejor experto:

```
L_Hedge  ≤  L_best  +  √( 2 · L_best · ln K )  +  ln K
```

Esta segunda es la que importa: depende de `L_best` y no del horizonte. Antes del ataque `L_best` es
chico y la cota es apretada; después del ataque `L_best` crece y la cota se afloja. **Predice el
escalón del drift**, cosa que `√(2T ln K)` —que solo crece con T— no puede hacer.

Estimación con nuestros números (a confirmar en la corrida):

| | Cálculo | Valor aprox. |
|---|---|---|
| Peor caso | `√(2 · 4459 · ln 5)` | ~120 errores |
| Small-loss con `L_best ≈ 150` | `√(2 · 150 · ln 5)` | ~22 errores |

---

## 3. Competidores y variantes

### Los tres competidores principales

Todos ven exactamente la misma secuencia `(x_1,y_1), ..., (x_T,y_T)`.

| Competidor | Qué hace | Qué efecto aísla |
|---|---|---|
| **Estático** | Un único modelo entrenado en el warm-up y congelado | Línea de base: lo que uno despliega en la práctica |
| **Hedge** | Pesos exponenciales sobre los K expertos congelados | El valor de **combinar**, sin reentrenar nada |
| **SGD online** | Un único modelo actualizado con `partial_fit` en cada ronda | El valor de **reentrenar**, sin combinar |

Separar Hedge de SGD-online es el aporte central: la consigna original compara Hedge contra el
estático, lo cual mezcla los dos efectos en un solo número.

### Actualización de Hedge (slide 72)

```
w^(i)_{t+1} = w^(i)_t · exp( −η · 1{f^(i)(x_t) ≠ y_t} ),   luego renormalizar
```

### Variante A: determinístico vs. randomizado

La slide 71 predice por **voto pesado determinístico**: `ŷ_t = 1` si `Σ_i f^(i)(x_t)·w_t(i) > 1/2`.
Pero la cota `√(2T ln K)` de la slide 73 es la de **Hedge**, donde la pérdida de la ronda es la de
la **mezcla** `Σ_i w_t(i)·ℓ_t(i)`, que se realiza **muestreando** un experto `I_t ~ w_t` y jugando
su predicción.

No es notación. Para un algoritmo determinístico **no existe** cota de regret sublineal en el peor
caso: el adversario ve tu predicción antes de fijar la etiqueta, te hace errar siempre, y el mejor
experto erra la mitad. La cota clásica de Weighted Majority es **multiplicativa** (del orden de
`2,41·(L_best + log₂K)` con β=1/2), no aditiva. La aleatorización no es un artificio de la
demostración: es lo que hace posible la garantía.

**Corremos las dos** y mostramos la brecha empírica y cuál de las dos respeta la cota.

### Variante B: etiqueta parcial (probabilidad ρ)

**Por qué no usamos EXP3.** El plan original tenía un competidor EXP3 "que observa solo la pérdida
del experto jugado". Eso no se sostiene: los expertos son funciones determinísticas y tenemos `x_t`,
así que jugamos `ŷ_t = f^(I_t)(x_t)` y al saber si acertamos **inferimos `y_t`**, y con `y_t` la
pérdida de los cinco expertos es computable. En clasificación binaria con pérdida revelada, el
feedback bandit **colapsa en información completa**. EXP3 resolvería un problema que no tenemos.

**El modelo correcto de feedback escaso en spam** es que la etiqueta llegue solo a veces: el usuario
reporta algunos mensajes y el resto nunca se corrigen. Modelamos `y_t` observada con probabilidad ρ;
en las rondas sin etiqueta nadie actualiza. Con el estimador insesgado `ℓ̂ = ℓ/ρ` en las rondas
observadas —el mismo truco de importance sampling de EXP3— el regret escala como `√(T ln K / ρ)`.

Barrido: `ρ ∈ {1 , 0,5 , 0,2 , 0,05}`. Predicción: el regret crece como `1/√ρ`.

*Nota para la discusión:* el modelo aún más fiel sería de **un solo lado** (*apple tasting*): si
mandás el mensaje a spam el usuario no lo mira y nunca sabés si erraste. Se menciona, no se corre.

---

## 4. Los cinco expertos

| # | Experto | Tipo | ¿Sobrevive al ataque léxico? |
|---|---|---|---|
| 1 | Naive Bayes multinomial | léxico | No |
| 2 | Regresión logística | léxico | No |
| 3 | Árbol de decisión | léxico | No |
| 4 | Reglas por keywords | léxico | No |
| 5 | **Features estructurales** | no léxico | **Sí** |

El experto 5 usa solo longitud del mensaje, proporción de dígitos, proporción de mayúsculas,
cantidad de links y cantidad de signos de exclamación.

**Por qué está ahí, y por qué no es ad-hoc.** El ataque que montamos es léxico, así que degrada a
los cuatro primeros. Sin un experto inmune, el drift rompe a *todos* y Hedge no puede recuperarse:
Hedge garantiza competir contra el mejor experto fijo, y si el mejor pasa a ser malo, la garantía no
dice nada útil.

La elección tiene respaldo publicado: Almeida et al. (2011), Tabla 2, reportan que el spam promedia
**23,48 tokens** por mensaje contra **13,18** del ham. La longitud discrimina en este corpus, está
documentado, y no lo inventamos nosotros. Igual declaramos en el paper que lo elegimos sabiendo que
es inmune al ataque léxico.

**Preprocesamiento** (siguiendo a Almeida et al., §3.1): sin stemming, sin eliminación de stopwords
y sin reducción de dimensionalidad, porque los mensajes son muy cortos.

**Vectorización:** `HashingVectorizer`, no `CountVectorizer`. Dos razones:
1. En streaming no se puede fijar el vocabulario usando datos futuros.
2. Los tokens ofuscados (`v1agra`) caen en buckets nuevos con peso cero — que es exactamente el
   mecanismo por el cual el ataque funciona.

---

## 5. El adversario

A partir de `t = T/2`, todo mensaje etiquetado como spam se transforma:

- **Ofuscación léxica:** se toman los tokens de mayor peso del modelo estático y se les aplica
  sustitución leetspeak (`a→4`, `i→1`, `o→0`, `e→3`, `s→5`).
- **Good word injection:** se inyectan tokens frecuentes en ham para diluir la señal.

Esto operacionaliza la slide 67 ("el spammer se adapta a nuestro clasificador"), que la teórica
enuncia sin experimentar.

### Cómo se nombra y se calibra

Es un **passive good word attack** en el sentido de Lowd & Meek (2005) —el atacante arma la lista
sin feedback del filtro— **extendido con ofuscación léxica**, que es justamente lo que ellos dejan
como trabajo futuro (*"characterizing other spam attacks (e.g., word obfuscation)"*).

**Calibración:** en lugar de fijar un número arbitrario de tokens, se calibra la intensidad hasta
que el modelo estático **pierda la mitad de su capacidad de detección** (de ~80% a ~40% de Spam
Caught). Es el mismo punto de comparación que usan ellos: con ≤150 palabras agregadas, la mitad del
spam bloqueado pasa.

### Oblivious, y por qué

El adversario ataca al **modelo estático**, no a cada competidor por separado. Tres razones, en
orden de peso:

1. Contra un adversario adaptativo la definición usual de regret no está bien definida y haría falta
   policy regret (§2).
2. Sin memoria acotada, el regret lineal es inevitable para cualquier algoritmo.
3. Todos los competidores ven la misma secuencia, así que las diferencias son atribuibles al
   algoritmo y no a la suerte del ataque que le tocó.

La versión adaptativa por competidor queda como posible corrida secundaria (§9).

---

## 6. Mediciones y figuras

- `T ≈ 4459` rondas (tras reservar 20% de warm-up de los 5.574 SMS).
- 20 semillas, variando la permutación del stream y el muestreo del Hedge randomizado.
- Resultados como media con banda de dispersión.

### Métricas: no reportar accuracy

En este corpus el clasificador trivial "todo es ham" saca **86,95% de accuracy** (Almeida et al.,
Tabla 7, fila *trivial rejection*). Cualquier número de accuracy es engañoso. Reportamos lo que usa
el paper del dataset:

- **Spam Caught (SC%)** — qué fracción del spam se atrapa.
- **Blocked Hams (BH%)** — qué fracción del correo legítimo se bloquea por error.
- **MCC** — coeficiente de correlación de Matthews, robusto al desbalance.

**Cuidado al reportar el regret:** con 13,4% de spam, el experto trivial tiene pérdida 0-1 de solo
0,134. Si el ataque rompe a los expertos léxicos, **el "mejor experto fijo en retrospectiva" podría
terminar siendo el trivial**, y el regret se estaría midiendo contra una vara ridícula. Hay que
decir siempre *quién* fue el mejor experto en retrospectiva, no solo el número.

### Figuras y tabla

| | Contenido | Qué muestra |
|---|---|---|
| **F1** | SC y BH en ventana móvil de los 3 competidores principales, con el drift marcado | El estático se cae y no se recupera; Hedge se recupera parcialmente; SGD-online se recupera del todo |
| **F2** | Evolución de los pesos `w^(i)_t` de Hedge (stackplot) | La masa migra de los expertos léxicos al estructural |
| **F3** | Regret empírico de Hedge determinístico y randomizado, contra **las dos cotas** (peor caso y small-loss) | Que la cota de la slide 73 aplica al randomizado y no al determinístico; y que la small-loss sigue la forma real de la curva |
| **T1** | Tabla: regret final y SC por valor de ρ | El costo de la etiqueta escasa, contrastado con `1/√ρ` |

---

## 7. Estructura de las 3 hojas

| Sección | Extensión | Contenido |
|---|---|---|
| 1. Introducción | ½ col | Spam como problema adversarial (slides 65-67); la afirmación de Lowd & Meek; las dos preguntas |
| 2. Marco formal | ½ col | Protocolo online, pérdida, regret, por qué oblivious (policy regret), las dos cotas |
| 3. Algoritmos | ½ col | Hedge; determinístico vs. randomizado; etiqueta parcial y por qué no EXP3 |
| 4. Setup experimental | ½ col | Dataset y baselines, los 5 expertos, el ataque y su calibración |
| 5. Resultados | 1 col + 3 figs + tabla | F1, F2, F3, T1 con lectura de cada una |
| 6. Discusión y limitaciones | ½ col | Ver abajo |
| 7. Conclusión | ¼ col | Las dos respuestas, en una frase cada una |

### Limitaciones a declarar explícitamente

- **Pérdida 0-1 simétrica.** En spam un falso positivo (ham marcado como spam) cuesta mucho más
  que un falso negativo. La teoría de Hedge admite pérdidas en [0,1], así que la extensión a
  pérdida asimétrica es directa, pero no la corremos. Por eso reportamos SC y BH por separado.
- **Expertos congelados.** Es lo que supone la slide 71, pero implica que Hedge no puede superar
  al mejor experto fijo: ante un adversario que rompe a todos, la garantía se vacía.
- **Adversario sintético y oblivious.** El SMS Spam Collection no tiene timestamps, así que el
  orden temporal y el drift los imponemos nosotros. Es legítimo en el marco adversarial (el
  adversario elige la secuencia), pero no es drift observado en la naturaleza.
- **Feedback de dos lados.** El modelo de etiqueta parcial supone que la etiqueta, cuando llega,
  llega para cualquier predicción. El caso realista es de un solo lado (*apple tasting*).

---

## 8. Entregables y plan de implementación

```
paper_spam_hedge/
  descargar_datos.py     # baja y descomprime el SMS Spam Collection de UCI
  expertos.py            # los 5 expertos: entrenamiento en warm-up y congelado
  adversario.py          # ofuscación leetspeak + good word injection, con calibración
  algoritmos.py          # Hedge determinístico, Hedge randomizado, estático, SGD online
  experimento.py         # loop de rondas, barrido de ρ, 20 semillas, guarda resultados
  figuras.py             # F1, F2, F3 y la tabla T1
  figuras/f1.png f2.png f3.png
  paper.tex              # listo para Overleaf
  referencias.bib
```

### Etapas

| # | Etapa | Verificación |
|---|---|---|
| 1 | Descarga y carga del dataset; split warm-up / stream | 5.574 mensajes, 747 spam (13,40%) |
| 2 | Los 5 expertos entrenados y congelados | SC sin drift contra los baselines de Almeida (ver abajo) |
| 3 | Adversario y su calibración | El SC del estático cae de ~80% a ~40%; el del experto estructural no se mueve |
| 4 | Hedge determinístico y randomizado | Sin drift, el regret del randomizado crece sublinealmente y queda bajo ambas cotas |
| 5 | Estático y SGD online | Corren sobre la misma secuencia |
| 6 | Barrido de ρ | El regret crece al bajar ρ, de forma compatible con `1/√ρ` |
| 7 | 20 semillas y agregación | Bandas de dispersión estables |
| 8 | Las 3 figuras y la tabla | Legibles en blanco y negro, a ancho de columna |
| 9 | Redacción del `.tex` | Entra en 3 páginas a dos columnas |

**Baselines para la etapa 2** (Almeida et al. 2011, Tabla 7, mismo corpus):

| Nuestro experto | Referencia | SC % esperado |
|---|---|---|
| Naive Bayes multinomial | MN TF NB + tok1 | ~52 |
| Regresión logística | cercano a SVM lineal | ~80 |
| Árbol de decisión | C4.5 + tok2 | ~75 |
| Experto trivial | trivial rejection | 0 |

Si alguno se desvía mucho, hay un bug.

**Riesgo conocido: hay poco spam.** Con 747 spams y warm-up del 20%, quedan ~598 en el stream y solo
**~300 sufren el ataque**. El regret se mueve en decenas de errores, no en miles. Por eso las 20
semillas no son opcionales; si las curvas quedan muy ruidosas, achicar el warm-up.

**Estimación:** ~1 día de trabajo.

**Estilo de código:** simple y autoexplicativo, sin one-liners, con los comentarios anclados a la
teórica (número de slide cuando corresponda), igual que en las guías de la materia.

**Entorno:** `~/.pyenv/versions/3.12.13/bin/python3` (numpy 2.4.4, pandas 3.0.2, sklearn 1.8.0,
matplotlib 3.10.9). No hay LaTeX ni pandoc local: el `.tex` se compila en Overleaf.

---

## 9. Decisión abierta

**¿Corremos la versión adaptativa del adversario?** Cesa-Bianchi, Dekel & Shamir (2013), Tabla 1,
predicen que con un adversario adaptativo de **memoria acotada** el regret se degrada de `√T` a
`T^{2/3}`. Eso convierte la corrida secundaria en un experimento con hipótesis falsable: ajustar una
ley de potencia al regret empírico y estimar el exponente.

**Costo:** hay que definir formalmente la memoria acotada, medir **policy regret** en lugar del
regret usual, y agregar el ajuste. Es aproximadamente media página de formalismo más una figura, en
un paper que ya está justo en espacio.

*Recomendación:* dejarlo fuera de la corrida y mencionarlo en la discusión con la predicción
teórica, salvo que al escribir sobre espacio.

> La decisión #2 del plan anterior (si el experto estructural era ad-hoc) quedó **resuelta**: tiene
> respaldo en la Tabla 2 de Almeida et al. Ver §4.

---

## 10. Referencias

Todas disponibles en [`referencias/`](../referencias/). Resúmenes y aportes de cada una en
[`resumen_papers.md`](resumen_papers.md).

- Y. Freund, R. Schapire (1997). *A Decision-Theoretic Generalization of On-Line Learning and an
  Application to Boosting*. JCSS 55(1). → Hedge original, la cota small-loss, determinístico vs.
  randomizado
- P. Auer, N. Cesa-Bianchi, Y. Freund, R. Schapire (2002). *The Nonstochastic Multiarmed Bandit
  Problem*. SIAM J. Comput. 32(1). → EXP3/EXP4, importance sampling, y por qué el bandit no aplica acá
- D. Lowd, C. Meek (2005). *Good Word Attacks on Statistical Spam Filters*. CEAS. → el ataque, su
  taxonomía pasivo/activo y su calibración; la tesis que discutimos
- T. Almeida, J. M. Gómez Hidalgo, A. Yamakami (2011). *Contributions to the Study of SMS Spam
  Filtering*. DocEng'11. → el dataset, el preprocesamiento, las métricas, los baselines
- N. Cesa-Bianchi, O. Dekel, O. Shamir (2013). *Online Learning with Switching Costs and Other
  Adaptive Adversaries*. arXiv:1302.4387. → policy regret, tasas por tipo de adversario
- N. Cesa-Bianchi, G. Lugosi (2006). *Prediction, Learning, and Games*. Cambridge University Press.
  → referencia general (no hace falta tenerla)
- Material de la materia: `referencias/clase_2_ventas_online.pdf`, slides 57-79.

---

## 11. Glosario

Términos que aparecen en este documento, explicados con el caso del spam.

### Los centrales

**Ham.** El correo legítimo, el que no es spam. Es la palabra que usa la literatura del área y no
tiene ningún contenido técnico. En el paper conviene escribir "legítimo".

**Drift (deriva).** Entrenás un modelo con los datos de hoy y lo dejás funcionando meses. Vos no lo
tocaste, pero el mundo cambió: las palabras que usan los spammers hoy no son las de hace medio año.
El modelo se quedó quieto mientras el fenómeno se movió, y empieza a fallar.

En este trabajo es *drift adversarial*, el caso peor: el mundo no cambia por casualidad, cambia
porque alguien lo cambia a propósito para romper el filtro. Ejemplo: el modelo aprendió que `viagra`
es señal fuerte de spam, el spammer escribe `v1agra`, y para el modelo esa palabra no existe.

**SGD online.** Dos cosas juntas. *SGD* (descenso por gradiente estocástico) es una forma de
entrenar: en vez de darle los 5.000 mensajes juntos, el modelo mira un ejemplo, corrige un poco sus
parámetros en la dirección que reduce el error, mira el siguiente, corrige otra vez. *Online* quiere
decir que eso nunca termina: cada mail nuevo, una vez conocida su etiqueta, se usa para corregir un
poco más. En scikit-learn es el método `partial_fit`.

Está en el experimento porque es el único competidor que se actualiza solo. Cuando el spammer
empieza con `v1agra`, después de unos ejemplos etiquetados este modelo aprende por su cuenta que
`v1agra` es spam. Los cinco expertos están congelados y nunca pueden aprender eso: Hedge solo puede
cambiar *cuánto le cree a cada uno*, no enseñarles palabras nuevas. Esa es justamente la comparación
central del paper.

**Oblivious (ajeno, que no mira).** Adjetivo para el adversario; describe contra quién dirige el
ataque.

- *Oblivious:* escribe todos los mails ofuscados de antemano, sin fijarse a quién se enfrenta. Esa
  única lista se le da a los cuatro competidores.
- *Adaptativo:* mira qué filtro le está bloqueando los mails y personaliza el ataque contra ese
  filtro en particular.

El adaptativo es más realista, pero genera un problema de medición: si cada competidor recibe mails
distintos porque el spammer se los personalizó, no rindieron el mismo examen y comparar sus errores
es injusto. El oblivious le toma a todos el mismo examen, así que las diferencias son atribuibles al
algoritmo. Esa es toda la razón de la decisión de §5.

### Los demás

**Regret (arrepentimiento).** No es cuántos errores cometiste, sino cuántos errores *de más*
cometiste respecto de la mejor opción fija que podrías haber elegido conociendo el futuro. Si
cometiste 300 errores y el mejor experto hubiera cometido 250, el regret es 50.

**Sublineal.** Que el regret crece más despacio que la cantidad de rondas. Si en 1.000 rondas
acumulás 100 de regret y en 4.000 acumulás 200 (y no 400), es sublineal: el arrepentimiento *por
ronda* tiende a cero. Es la definición operativa de "está aprendiendo".

**Información completa vs. bandit.** Qué te enterás después de clasificar un mail. Con *información
completa* ves qué habría contestado cada uno de los cinco expertos y si acertaba. Con feedback
*bandit* solo sabés si acertaste vos, y nunca sabrás qué hubiera pasado eligiendo otro. Es como
elegir restaurante: solo probás el que elegiste.

**Warm-up.** El primer 20% de los datos, usado únicamente para entrenar a los expertos. No cuenta
para la evaluación.

**η (eta).** La tasa de aprendizaje de Hedge: qué tan duro se castiga a un experto cada vez que se
equivoca. Muy grande, un solo error lo manda al descarte; muy chica, Hedge tarda demasiado en
reaccionar al drift.

**K y T.** K es la cantidad de expertos (5 acá), T la cantidad de rondas (~4.400 mensajes).

**Leetspeak.** Escribir con números que parecen letras: `4` por `a`, `1` por `i`, `0` por `o`, `3`
por `e`, `5` por `s`. Es lo que usa el spammer en nuestro ataque.

**Semillas (seeds).** El experimento tiene componentes al azar (el orden de los mensajes, el sorteo
de EXP3). Correrlo 20 veces con distinto azar y promediar evita que el resultado sea casualidad de
una corrida.

**HashingVectorizer.** El texto hay que convertirlo en números. Esto manda cada palabra a una
casilla fija de un vector grande usando una función hash. La alternativa clásica arma primero la
lista de todas las palabras que existen; el hashing no necesita esa lista, y por eso tolera que
aparezcan palabras nuevas como `v1agra` sin romperse.

**Importance sampling.** El truco que usa EXP3 para estimar cuánto habrían perdido los expertos que
*no* jugó: divide la pérdida observada por la probabilidad con la que eligió a ese experto. Así, en
promedio, la estimación da lo correcto aunque solo haya visto uno.

**Stackplot.** Gráfico de áreas apiladas. Lo usamos para la figura 2: cada banda es el peso de un
experto y todas suman 1, así que se ve de un vistazo cómo se reparte la confianza a lo largo del
tiempo.

**Falso positivo / falso negativo.** Falso positivo: marcar como spam un mensaje legítimo (perdés un
mail que te importaba). Falso negativo: dejar pasar spam (molesto, pero recuperable). En spam el
primero cuesta mucho más, y por eso figura en las limitaciones de §7.

### Agregados tras la revisión de la bibliografía

**Spam Caught (SC) y Blocked Hams (BH).** Las dos métricas que usa el paper del dataset. SC es qué
porcentaje del spam lográs atrapar; BH es qué porcentaje del correo legítimo bloqueás por error. Se
reportan por separado porque los dos errores no cuestan lo mismo: un filtro que atrapa el 98% del
spam pero bloquea el 26% del correo bueno es inservible, y con un solo número de accuracy eso no se
ve.

**MCC (coeficiente de correlación de Matthews).** Un número entre −1 y +1 que resume la calidad de
una clasificación binaria sin dejarse engañar por el desbalance de clases. +1 es predicción
perfecta, 0 es equivalente a tirar una moneda, −1 es predecir siempre al revés. Se usa acá porque
la accuracy no sirve cuando solo el 13% de los mensajes son spam.

**Hedge determinístico vs. randomizado.** Dos formas de convertir los pesos en una predicción.
*Determinístico:* se hace el voto pesado y se predice lo que diga la mayoría ponderada — siempre lo
mismo ante la misma entrada. *Randomizado:* se sortea un experto según los pesos y se juega su
predicción — dos corridas con la misma entrada pueden diferir. Importa porque la cota teórica de la
slide 73 vale para el segundo y no para el primero: contra un adversario que ve tu predicción antes
de fijar la etiqueta, ser predecible es una desventaja que no se puede acotar.

**Cota small-loss.** Una cota de regret que depende de cuántos errores comete el mejor experto
(`L_best`) en vez de depender de cuántas rondas hay (`T`). Es más informativa: si el mejor experto
casi no se equivoca, la cota es muy apretada; si se equivoca mucho, se afloja. Por eso puede
reproducir el escalón que produce el drift, mientras que una cota que solo crece con el tiempo no.

**Policy regret.** La versión correcta del regret cuando el adversario se adapta a vos. El regret
usual pregunta "¿qué hubiera pasado si en *esta* ronda jugaba otra cosa?", lo cual no tiene sentido
si el adversario venía reaccionando a todo lo que hiciste antes. El policy regret pregunta "¿qué
hubiera pasado si hubiera jugado esa otra cosa *desde el principio*?", dejando que el adversario
reaccione también a esa historia alternativa.

**ρ (rho) — probabilidad de observar la etiqueta.** En nuestro modelo de feedback escaso, la
fracción de mensajes para los que llegamos a saber la verdad (porque el usuario los reportó o los
corrigió). Con ρ = 1 vemos todas las etiquetas; con ρ = 0,05 solo una de cada veinte. Las rondas sin
etiqueta no actualizan nada.

**Good word attack.** El ataque de Lowd & Meek: el spammer agrega a sus mensajes palabras típicas
del correo legítimo para diluir la señal de spam. *Pasivo* si arma la lista sin poder probar el
filtro; *activo* si puede mandar mensajes de prueba y ver cuáles pasan. Nuestro ataque es el pasivo,
extendido con ofuscación de las palabras delatoras.

**Apple tasting.** El modelo de feedback donde solo te enterás del resultado si tomás una de las dos
decisiones. El nombre viene de probar manzanas: si la mordés sabés si estaba buena, pero ya no la
podés vender; si no la mordés, la vendés pero nunca sabés. En spam: si mandás el mensaje a la
carpeta de spam, el usuario no lo mira y nunca sabés si te equivocaste.
