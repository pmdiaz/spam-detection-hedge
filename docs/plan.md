# Plan de trabajo — Paper: aprendizaje online con Hedge para detección de spam

**Autores:** Pablo Díaz y Ezequiel Martinez
**Materia:** Tópicos Avanzados en Ciencia de Datos (MCD210) — Daniel Fraiman
**Formato de entrega:** ~3 páginas, LaTeX a dos columnas (compilación en Overleaf), en español
**Origen del tema:** `referencias/clase_2_ventas_online.pdf`, slide 79 ("Ideas para el paper"), ítem 3:
*"Extender el caso de detección de spam a un clasificador que se reentrena online con Hedge,
y comparar contra un modelo estático."*
**Estado:** etapas 1-8 implementadas y verificadas: el experimento completo con 20 semillas está
corrido (resultados en §6) y las tres figuras del paper están generadas (`figuras/*.pdf`). Falta la
redacción (etapa 9). El plan incorpora
lo que se aprendió al implementar: ataque por duplicación de vocal, experto estructural enriquecido,
cada cota con su η, la construcción sintética, estático fijo en Naive Bayes y α de SGD fijo.
Quedan decisiones menores abiertas (§9).

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
desempeño sin necesidad de reentrenar, pero solo mientras exista al menos un experto fijo que
sobreviva al ataque — y esa condición es exactamente el límite de la garantía de Hedge.

La condición no es retórica: la medimos. Con la primera versión del experto estructural, que no
sobrevivía al ataque, Hedge terminaba con 0,995 del peso en el modelo estático dañado y no recuperaba
nada. Con la versión enriquecida (§4), Hedge comete 133 ± 10 errores en la mitad atacada contra
190 ± 32 del estático, y cubre el 46 ± 13% de la brecha entre el estático y reentrenar (20 semillas,
§6).

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

**Nota sobre la constante, que el paper tiene que resolver con una sola versión.** Con η fijo, el
lema de Hoeffding da una cota válida en **toda** ronda t, no solo al final:

```
R_t  ≤  ln K / η  +  η · t / 8
```

Con `η = √(8 ln K / T)`, en `t = T` vale `√(T ln K / 2)`: **la mitad** de la `√(2 T ln K)` de la
slide. Las dos son correctas; la de la slide es conservadora. Con nuestros números: 59,9 contra
119,8. El paper usa la de Hoeffding, que es la que se grafica como curva en la Fig. 2, con una nota
sobre la constante de la slide.

**Lo mismo vale para la cota small-loss.** El Teorema 2 de Freund & Schapire, con β fijo, vale en
toda ronda t y contra cualquier experto i:
`L_Hedge(t) ≤ (ln K + η · L_i(t)) / (1 − e^{−η})`. Como depende de la pérdida acumulada del experto
y no de t, su pendiente cambia cuando el ataque cambia el ritmo de errores del experto. Es lo que la
Fig. 2A muestra como curva.

**Cota fina** (Freund & Schapire 1997, Lema 4), en función de la pérdida del mejor experto:

```
L_Hedge  ≤  L_best  +  √( 2 · L_best · ln K )  +  ln K
```

Esta segunda es la que importa: depende de `L_best` y no del horizonte. Antes del ataque `L_best` es
chico y la cota es apretada; después del ataque `L_best` crece y la cota se afloja. **Predice el
escalón del drift**, cosa que `√(2T ln K)` —que solo crece con T— no puede hacer.

### Cada cota vale para su propio η

Error que cometimos al implementar y que el paper tiene que evitar: las dos cotas corresponden a
**dos configuraciones distintas** del mismo algoritmo.

| Cota | η con el que vale |
|---|---|
| Peor caso `√(2T ln K)` | `η = √(8 ln K / T)` — requiere conocer T |
| Small-loss de F&S | `β = 1/(1 + √(2 ln K / L̃))`, o sea `η = ln(1 + √(2 ln K / L̃))` — requiere una cota `L̃ ≥ L_best` conocida de antemano |

Exigirle a la configuración de peor caso la cota small-loss da una "violación" que no es tal.

### Valores medidos (stream sin ataque, semilla 0)

T = 4460, K = 5, mejor experto fijo: Naive Bayes con `L_best = 115` errores.

| Configuración | η | Regret Hedge randomizado | Su cota |
|---|---|---|---|
| Sintonizado por T | 0,0537 | 26,4 ± 9,6 | 119,8 ✓ |
| Sintonizado por `L_best` | 0,1547 | **9,8 ± 4,8** | 20,8 ✓ |

El análisis small-loss no solo da una cota más ajustada: **prescribe un algoritmo mejor**. Sintonizar
η para `L_best` baja el regret 2,7×. La contra es que requiere conocer `L_best` de antemano, que con
drift no se sabe — es una sintonía de oráculo y hay que declararla así.

Regret sublineal confirmado: el regret por ronda baja de 0,0119 a 0,0059 a lo largo del stream, y un
ajuste log-log da `R_T ~ T^0,64`.

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

**Configuración usada en el experimento:**

- **Estático:** Naive Bayes, fijo por diseño (§4).
- **Hedge:** randomizado, con η sintonizado por T (`η = √(8 ln K / T)`). El determinístico y el η
  small-loss se corren y se guardan como referencia.
- **SGD online:** regresión logística por SGD sobre el mismo hashing, arranca entrenado sobre el
  warm-up, predice primero y actualiza después, learning rate por defecto de scikit-learn y
  `α = 1e-5` fijo (§4).

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

**Lo que encontramos al implementar cambia cómo se cuenta esto.** La brecha no aparece en el stream de
spam, y tiene que mostrarse con una construcción aparte. Se cuenta en dos partes:

**Parte 1 — en el stream de spam el determinístico anda mejor.** Sin ataque, su regret es **−8,0**:
comete 107 errores contra los 115 del mejor experto individual. Es lo que hace cualquier ensamble
sobre una secuencia benigna, y no contradice nada, porque la garantía es sobre el peor caso. El
ataque de spam no cambia esto: está dirigido al modelo estático, no al jugador, así que nunca
explota que el jugador sea predecible.

**Parte 2 — una construcción mínima exhibe la falla.** Dos expertos (uno dice siempre ham, el otro
siempre spam) y un adversario que **simula offline** al jugador determinístico y etiqueta lo
contrario de lo que va a predecir. El adversario sigue siendo **oblivious** —fija toda la secuencia
de antemano— y aun así funciona: contra un jugador determinístico la obliviousness no protege,
porque si sos predecible te pueden simular.

| T | Regret determinístico | R/T | Regret randomizado | Cota |
|---|---|---|---|---|
| 500 | 250 | 0,500 | 5,0 | 26,3 |
| 2000 | 1000 | 0,500 | 8,7 | 52,7 |
| 8000 | 4000 | 0,500 | 20,6 | 105,3 |

Regret exactamente `T/2`, lineal, contra el sublineal del randomizado. Son ~20 líneas de código
(`construir_secuencia_adversaria` en `algoritmos.py`) y media columna de paper.

Las dos partes juntas son más honestas que "el determinístico viola la cota": en la práctica benigna
anda mejor, y en el peor caso no tiene ninguna garantía.

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

Resultados medidos (semilla 0). Las columnas del ataque son sobre la mitad atacada del stream.

| # | Experto | Tipo | SC sin ataque | SC atacado | Errores mitad atacada |
|---|---|---|---|---|---|
| 1 | Naive Bayes multinomial (= estático) | léxico | 85,6% | 38,1% | 193 |
| 2 | Regresión logística | léxico | 79,6% | 5,5% | 288 |
| 3 | Árbol de decisión | léxico | 79,4% | 6,2% | 332 |
| 4 | Reglas por keywords | léxico | 80,3% | 12,8% | 284 |
| 5 | **Features estructurales** | formato | 80,8% | **66,8%** | **102** |

Un detalle que vale una línea en la discusión: el ataque, calibrado contra Naive Bayes, destroza a
los otros tres léxicos (5-13% de SC) mucho más que a su propio objetivo (38%). Naive Bayes resiste
mejor por el artefacto descrito en §5: para él, un token nunca visto cuenta como evidencia de spam.

### El experto estructural: por qué se enriqueció

El experto 5 usa nueve features de **formato**, ninguna de las cuales mira qué palabras aparecen:
longitud en tokens, proporción de dígitos, proporción de mayúsculas, cantidad de links, cantidad de
signos de exclamación, **teléfonos y códigos cortos**, **símbolos de moneda**, **tarifas** (`150p`,
`p/msg`, `/min`) y **palabras enteras en mayúscula**.

La primera versión tenía solo las cinco primeras y alcanzaba ~30% de SC. **Medido contra el ataque,
eso rompía el experimento:** en la mitad atacada seguía siendo peor que el estático dañado (222
contra 193 errores), apenas mejor que el clasificador trivial (289). Hedge le daba 0,000 de peso de
punta a punta y "combinar" no tenía nada que combinar. Probamos también Fixed-Share (Herbster &
Warmuth 1998), la variante de Hedge pensada para drift, y tampoco ayudaba: cambiar rápido de
experto no sirve si no hay un experto bueno al cual cambiar.

Los cuatro patrones nuevos son típicos del spam por SMS ("Call 09061701461", "£1000", "150p/msg",
"FREE") y la longitud sigue teniendo respaldo en Almeida et al. (2011), Tabla 2 (spam 23,48 tokens
contra 13,18 del ham).

**Declaración necesaria en el paper:** este experto es robusto al ataque en buena medida **por
construcción**, porque la ofuscación duplica vocales y no toca dígitos ni símbolos. No es un experto
robusto en general: es robusto a *este* ataque. Tampoco es inmune: la ofuscación convierte `150p` en
`150pp`, que rompe el patrón de tarifas, y por eso cae de 80,8% a 66,8%.

Se descartó la alternativa de un experto de n-gramas de caracteres: era aún más robusto (83,7% →
79,2%), pero sin ataque rendía igual que Naive Bayes, así que la validación cruzada podía elegirlo
como modelo estático. En ese caso el modelo desplegado ya sería robusto y la premisa del experimento
desaparecería.

### Selección de hiperparámetros

Los valores por defecto de dos expertos son inservibles con hashing, y hubo que elegirlos:

- **Naive Bayes con `alpha=1` colapsa (1% de SC).** El suavizado de Laplace agrega 2^18 = 262.144
  pseudo-conteos al denominador de cada clase, contra muy poca masa real en el warm-up: solo 3.495
  buckets están ocupados. La verosimilitud queda ahogada y el modelo predice el prior. Almeida no lo
  sufren porque usan vocabulario real, no hashing.
- **La regresión logística con `C=1` está sobrerregularizada** (47% de SC) para 2^18 features y
  1.114 ejemplos.

**Criterio:** validación cruzada de 5 folds **sobre el warm-up**, nunca sobre el stream, con **MCC**
como scorer (el criterio por el que Almeida ordenan su tabla). Entre valores estadísticamente
indistinguibles se elige el más regularizado (**regla de un error estándar**), porque la meseta de la
regresión logística es plana arriba de C≈100 y el argmax caía en C=3000 por ruido. Resultado:
`alpha = 0,001`, `C = 100`.

**Se descartó `class_weight='balanced'`**, que era la salida obvia: optimiza una pérdida reponderada,
distinta de la pérdida 0-1 sin pesos sobre la que definimos el regret, y produciría expertos
subóptimos para la pérdida que Hedge mide.

### Dos decisiones que la validación cruzada no podía tomar

Las dos salieron de la primera corrida con 20 semillas, y las dos se tomaron **fijando el valor por
diseño** en lugar de elegirlo por CV. En ambos casos se sigue registrando qué habría elegido la CV,
porque es una observación para la discusión. Los resultados de aquella corrida quedaron en
`resultados/semillas_v1_estatico_y_alpha_por_cv/`.

**El modelo estático es Naive Bayes, fijo.** La primera versión lo elegía por validación cruzada
anidada sobre el warm-up. En 20 semillas eligió Naive Bayes en 14 y el estructural en 6, siempre por
poco margen (en la semilla 0: 0,869 contra 0,845 de MCC). En esas 6 el diseño quedaba incoherente: el
adversario arma su ataque con los pesos de un filtro bayesiano (§5), así que no atacaba al modelo
desplegado, y el "estático" resultaba robusto por accidente. La dispersión del estático era ±42
errores y la fracción de brecha cubierta por Hedge iba de −125% a 210%. Fijarlo en Naive Bayes hace
que el estático sea siempre el modelo que el spammer ataca, que además es el filtro que estudian
Lowd & Meek. *Para la discusión:* un practicante que eligiera por CV habría desplegado, por azar, un
modelo robusto en 6 de cada 20 casos.

**El α de SGD online es 1e-5, fijo.** La primera versión lo elegía como a los expertos (CV sobre el
warm-up, MCC, regla de un error estándar). Con 20 semillas eso rompía la comparación: la CV eligió
1e-5 en 11 semillas, y ahí SGD cometió 65-83 errores en la mitad atacada; eligió 1e-4 en 8, y ahí
cometió 125-153. Las semillas en las que "Hedge le ganaba a reentrenar con todas las etiquetas" eran
exactamente esas. La causa: la CV mide qué tan bien clasifica el modelo *antes* del ataque, y ahí
1e-4 y 1e-5 dan casi lo mismo; lo que importa para este competidor es qué tan rápido *se adapta*, y
eso no se puede ver en un warm-up sin drift. Con α más grande el paso `1/(α(t+t₀))` es diez veces más
chico y la penalización L2 frena el aprendizaje de los tokens nuevos. La regla del error estándar
empeora las cosas, porque prefiere justamente el modelo más regularizado: es la regla correcta para
generalizar y la equivocada para un modelo que tiene que adaptarse. Se fija el valor que eligió la CV
en la semilla 0, donde se desarrolló el diseño; las otras 19 lo evalúan fuera de muestra. Un SGD mal
sintonizado favorecería injustamente a Hedge.

*Para la discusión:* es un hallazgo metodológico en sí mismo. Validar un hiperparámetro sobre datos
sin drift no mide la capacidad de adaptación, que es justamente lo que importa en un modelo online.

**Preprocesamiento** (siguiendo a Almeida et al., §3.1): sin stemming, sin eliminación de stopwords
y sin reducción de dimensionalidad, porque los mensajes son muy cortos.

**Vectorización:** `HashingVectorizer`, no `CountVectorizer`. Dos razones:
1. En streaming no se puede fijar el vocabulario usando datos futuros.
2. Los tokens ofuscados (`viiagra`) caen en buckets nuevos con peso cero — que es exactamente el
   mecanismo por el cual el ataque funciona.

Parámetros: `n_features = 2^18` (con ~10^4 tipos únicos, ~6% de tokens en colisión; con 2^16 serían
~23%) y `alternate_sign=False`, porque Naive Bayes multinomial necesita features no negativas.
`norm` quedó en su valor por defecto, `'l2'`: Naive Bayes recibe frecuencias normalizadas y no
conteos crudos como en el `MN TF NB` de Almeida (ver §9).

---

## 5. El adversario

A partir de `t = T/2`, todo mensaje etiquetado como spam se transforma. El ataque tiene un
mecanismo **primario** y uno **secundario y acotado**, y esa jerarquía es deliberada (ver más abajo):

- **Primario — ofuscación léxica:** se toman los tokens más delatores y se les **duplica la primera
  vocal interna** (`viagra` → `viiagra`; los tokens sin vocal interna, como `150p`, duplican el
  último carácter). **Preserva el conteo de tokens exactamente** y **no introduce dígitos**.
- **Secundario — good word injection, acotada:** se inyectan unos pocos tokens frecuentes en ham
  para diluir la señal, con un tope explícito sobre cuántos (ver la restricción de longitud).

Esto operacionaliza la slide 67 ("el spammer se adapta a nuestro clasificador"), que la teórica
enuncia sin experimentar.

### Por qué la ofuscación es el mecanismo primario

Lowd & Meek necesitan agregar ~150 palabras para partir al medio la detección, pero eso es en
**email**, donde 150 palabras se diluyen en el cuerpo del mensaje. Un SMS de este corpus promedia
**23,48 tokens** (Almeida et al., Tabla 2). Inyectar decenas de palabras lo llevaría a 50-170
tokens: **eso no es un SMS plausible**, y el mensaje atacado quedaría trivialmente separable por
longitud.

Eso rompería el experimento por dos lados a la vez:

1. **Falta de realismo.** El ataque dejaría de ser sigiloso y pasaría a ser un artefacto del
   montaje.
2. **Contaminación del experto estructural.** El experto 5 usa longitud, proporción de dígitos y
   proporción de mayúsculas. Una inyección masiva mueve esos tres features, y entonces el
   "salvavidas" del experimento deja de estar aislado del ataque.

### Por qué duplicación de vocal y no leetspeak

La primera versión usaba leetspeak (`a→4`, `i→1`, `o→0`, `e→3`, `s→5`). Medido, **contaminaba el
experimento**: al introducir dígitos subía la proporción de dígitos del spam atacado de 11,5% a
21,2%, y como en SMS los dígitos correlacionan con spam, el experto estructural pasaba de 32% a 62% de
SC. El ataque, que debía ser puramente léxico, terminaba *mejorando* al salvavidas.

La duplicación de vocal es mejor en las tres dimensiones (medido con 800 tokens ofuscados, sin
inyección):

| Esquema | SC del estático | SC del estructural (versión simple) | % de dígitos del spam |
|---|---|---|---|
| Leetspeak | 66,1% | 61,9% ← contaminado | 21,2% |
| Duplicación de vocal | **55,7%** | **27,0%** | 11,5% (sin cambio) |

Es además una evasión realista: los spammers escriben "viaagra", "vi agra", "v-i-a-g-r-a".

### Efecto del ataque sobre el experto estructural

| Feature | Efecto del ataque | Dirección |
|---|---|---|
| Longitud | La inyección de una palabra alarga el mensaje, y el experto aprendió que más largo → más spam | A favor |
| Dígitos, teléfonos, moneda | La duplicación de vocal no los toca | Neutro |
| Tarifas | `150p` → `150pp` rompe el patrón `\d+p` | **En contra** |
| Mayúsculas | La palabra de ham inyectada va en minúscula y diluye la proporción | En contra |

Resultado neto con la calibración final: el estructural cae de 80,8% a 66,8% de SC, y sigue siendo
por lejos el mejor experto en la mitad atacada.

### Cómo se nombra y se calibra

Es un **passive good word attack** en el sentido de Lowd & Meek (2005) —el atacante arma la lista
sin feedback del filtro— **extendido con ofuscación léxica**, que es justamente lo que ellos dejan
como trabajo futuro (*"characterizing other spam attacks (e.g., word obfuscation)"*). En nuestra
versión el peso relativo de los dos mecanismos está invertido respecto del original, por la
restricción de longitud del medio.

**Calibración, en dos pasos y en este orden:**

1. Subir la intensidad de la **ofuscación** (cuántos de los tokens de mayor peso se ofuscan) hasta
   donde alcance, sin tocar la inyección. Como preserva el conteo de tokens, no tiene costo en
   longitud.
2. Solo si con ofuscación sola no se llega al objetivo, agregar **inyección** hasta completarlo,
   respetando el tope de longitud.

**Objetivo:** que el modelo estático **pierda la mitad de su capacidad de detección** (de ~80% a
~40% de Spam Caught), que es el mismo punto de comparación que usan Lowd & Meek.

**Restricción dura — longitud plausible:** la distribución de longitudes del spam atacado debe
**superponerse con la del spam original**. Criterio operativo: la mediana de tokens del spam
atacado no puede superar en más de ~20% la del spam sin atacar, y su percentil 95 no puede superar
el **máximo del spam original**. Si para llegar al 40% de SC hiciera falta violar esa restricción,
**se reporta el SC que se alcanzó** y se declara el límite, en lugar de forzar un ataque irreal.

La referencia es el spam original y no el corpus completo: el spam es naturalmente más largo que el
ham, y la primera versión del criterio (percentil 95 del corpus) se violaba incluso sin ataque.

Los umbrales de 20% y del máximo son un criterio operativo nuestro, no salen de ningún paper.

### Calibración resultante (semilla 0)

**Ofuscación de los 800 tokens más delatores + 1 palabra legítima inyectada.**

| Inyectadas | SC del estático | Mediana de tokens | P95 | Longitud |
|---|---|---|---|---|
| 0 | 55,7% | 25 | 31 | ok |
| **1** | **38,1%** | 26 | 32 | ok |
| 2 | 23,5% | 27 | 33 | ok |
| 4 | 3,8% | 29 | 35 | ok |
| 5 | 0,7% | 30 | 36 | violada |

El SC del estático cae de 86,5% a 38,1%: una caída relativa del 56%, muy cerca del "la mitad del
spam bloqueado pasa" de Lowd & Meek. La mediana de longitud pasa de 25 a 26 tokens.

**La ofuscación sola no alcanza, y el motivo es un hallazgo para la discusión.** El SC del estático
no es monótono en la cantidad de tokens ofuscados: baja hasta ~800 y **vuelve a subir** (64% con
1600). Es un artefacto conocido de Naive Bayes: un token nunca visto tiene log-ratio **+1,31**, o sea
que cuenta como evidencia *a favor* de spam, porque la clase spam tiene menos masa total y el
suavizado le asigna más probabilidad a lo desconocido. Ofuscar demasiado inunda el mensaje de tokens
desconocidos y lo vuelve a delatar.

**Pesos del ataque.** Con hashing no se pueden recuperar los tokens a partir de los buckets, así que
los tokens "más delatores" se eligen por su log-odds de Naive Bayes calculado en espacio de tokens
sobre el warm-up. Es como Lowd & Meek modelan el filtro atacado (un peso por feature más un umbral),
y aproxima al modelo estático, que es Naive Bayes, aunque no es exactamente él: el estático usa
hashing, normalización y otro α.

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

- `T = 4460` rondas (tras reservar 20% de warm-up de los 5.574 SMS: 1.114 mensajes).
- **20 semillas de permutación.** Cada una fija un orden distinto del corpus y, con él, un warm-up,
  un stream, unos expertos entrenados y un ataque distintos.
- **Semillas de muestreo** dentro de cada permutación, para el azar de Hedge randomizado: 20 en el
  experimento principal y 5 en el barrido de ρ (100 corridas por valor de ρ en total).
- Resultados como media ± desvío entre las 20 semillas de permutación.

### Métricas: no reportar accuracy

En este corpus el clasificador trivial "todo es ham" saca **86,95% de accuracy** (Almeida et al.,
Tabla 7, fila *trivial rejection*). Cualquier número de accuracy es engañoso. Reportamos lo que usa
el paper del dataset:

- **Spam Caught (SC%)** — qué fracción del spam se atrapa.
- **Blocked Hams (BH%)** — qué fracción del correo legítimo se bloquea por error.
- **MCC** — coeficiente de correlación de Matthews, robusto al desbalance.

**Cuidado al reportar el regret:** hay que decir siempre *quién* fue el mejor experto en
retrospectiva, no solo el número. Con la primera versión del estructural existía el riesgo de que
fuera un experto casi trivial; con la enriquecida, el mejor experto fijo sobre el stream atacado es
el estructural en las 20 semillas.

**Reproducibilidad.** Los números de esta sección son exactamente reproducibles con
`./correr_todo.sh`. Una primera versión no lo era: al elegir los 800 tokens a ofuscar, los 14
empatados en el corte se desempataban según el orden de un `set` de Python, que cambia en cada
proceso, así que cada corrida atacaba con una lista apenas distinta. Ahora se desempata por orden
alfabético. El cambio movió las cifras en el último dígito (por ejemplo, 47 → 46% de la brecha y
16 → 15 semillas en que gana combinar con ρ = 0,05) y no cambió ninguna conclusión; los resultados
anteriores quedaron en `resultados/semillas_v2_desempate_aleatorio/`.

### Figuras del paper

Tres figuras, generadas por `src/figuras.py` a partir de lo que guardó el experimento (no vuelve a
correr nada). Todas son promedios sobre las 20 semillas.

| Figura | Archivo | Contenido | Qué muestra |
|---|---|---|---|
| **Fig. 1** | `f1f2_combinada.pdf` | A: spam atrapado en ventana móvil de 300 rondas para estático, Hedge y SGD online. B: pesos de Hedge (stackplot) con el mismo eje temporal | El estático cae y no se recupera; Hedge cae con él y se recupera en ~1.000 rondas mientras migra el peso; SGD online aprende los tokens nuevos |
| **Fig. 2** | `f3_regret.pdf` | A: regret de Hedge con `η_T` y con `η_L`, cada uno contra **su** cota como curva en el tiempo. B: la construcción sintética, determinístico contra randomizado | Que cada cota vale para su configuración; que la cota small-loss cambia de pendiente con el ataque (idea A2); que el determinístico tiene regret `T/2` |
| **Fig. 3** | `f4_rho.pdf` | Errores en la mitad atacada contra ρ, para Hedge y SGD online (media ± desvío), con el estático como referencia | El cruce entre combinar y reentrenar entre ρ = 0,2 y 0,05 |

Se generan también F1 y F2 por separado (`f1_sc_movil`, `f2_pesos`), por si se prefiere esa
variante. Los números finos (BH, MCC, regret por ρ) van en una tabla, no en las figuras.

**Diseño.** Ancho exacto de columna (3,3 pulgadas), letra de 8 pt, sin `bbox_inches="tight"` (que
agrandaba la imagen y hacía que LaTeX la achicara). Un color por entidad, igual en todas las figuras,
validado con el script de la guía de visualización, incluida la separación para daltonismo:

| Entidad | Color | Estilo |
|---|---|---|
| Estático / Naive Bayes | naranja | rayada |
| Hedge randomizado (`η_T`) | azul | continua |
| SGD online | aqua | punteada |
| Estructural | violeta | — |
| Otros léxicos (logística + árbol + reglas) | verde, con rayado a 45° | — |
| Hedge con `η_L` (small-loss) | magenta | continua |
| Hedge determinístico | rojo | continua |

Cada serie tiene además estilo de línea y etiqueta directa, para que se lea en blanco y negro. El
validador rechazó el verde junto al naranja (con protanopia son casi iguales), y por eso las capas de
los pesos van en el orden Naive Bayes, estructural, otros léxicos. En escala de grises el violeta y
el verde daban el mismo gris, y por eso "otros léxicos" lleva el rayado.

**La lectura correcta de los pesos** (Fig. 1B, promedio de 20 semillas). Tiene dos partes:

1. **Hay hedging antes del ataque.** Cuando llega el ataque, el peso está repartido en tercios:
   Naive Bayes 0,36, estructural 0,33, otros léxicos 0,31. Hedge no apostó todo al mejor experto
   del momento.
2. **Y hay una migración provocada por el ataque, que no es instantánea.** El spam atrapado por
   Hedge primero cae junto con el del estático, hasta ~45%, y recién después se recupera; el peso
   del estructural tarda unas 1.000 rondas en pasar de 0,33 a 0,95.

Esto corrige lo que decía esta sección con la semilla 0 ("no hay migración, la recuperación es casi
instantánea"). En esa semilla el estructural ya era el mejor antes del ataque; en el promedio no.

### Resultados con 20 semillas

Salida de `src/agregar_resultados.py`; el resumen completo queda en `resultados/resumen.json`.

**Competidores** (media ± desvío entre semillas):

| Competidor | Errores antes del ataque | Errores mitad atacada | SC atacada | BH atacada |
|---|---|---|---|---|
| Estático (Naive Bayes) | 60 ± 9 | 190 ± 32 | 42 ± 11% | 0,70% |
| Hedge randomizado | 72 ± 5 | 133 ± 10 | 59 ± 3% | 0,42% |
| Hedge determinístico | 48 ± 8 | 123 ± 11 | 61 ± 4% | 0,29% |
| SGD online | 50 ± 6 | **73 ± 6** | **83 ± 2%** | 1,07% |

**Pregunta 1 — combinar o reentrenar.** Reentrenar es lo que más recupera, como dicen Lowd & Meek.
Pero Hedge, sin tocar ningún modelo, cubre el **46 ± 13%** de la brecha entre el estático y
reentrenar (mediana 45%, rango 23% a 76%). El mecanismo: el SC de Hedge tiene como techo el del mejor
experto fijo (el estructural, ~60-67%), porque solo puede redistribuir peso; SGD supera ese techo
porque aprende los tokens nuevos.

*Cuidado:* la semilla 0 daba 59%, en el extremo favorable. En el paper va el 47%.

**El seguro de Hedge tiene un costo visible.** Antes del ataque, Hedge randomizado comete *más*
errores que el estático (72 contra 60): es el precio de sortear expertos en lugar de seguir al mejor,
la contracara de su garantía de peor caso. El determinístico no lo paga (48) y es mejor también
después del ataque. Es el mismo patrón de §3: en secuencias benignas el determinístico gana, y en el
peor caso no tiene garantía.

**Regret contra las cotas** (stream atacado):

| Configuración | Regret | Su cota | Bajo la cota |
|---|---|---|---|
| Randomizado, η de peor caso | 31,2 ± 1,5 | 59,9 (119,8 con la constante de la slide) | 20/20 |
| Randomizado, η small-loss (oráculo) | 15,1 ± 1,4 | 25,2 ± 0,7 | 20/20 |
| Determinístico | −2,6 ± 4,9 | — | — |

Sobre la cota de peor caso, ver la nota de §2: el paper usa `√(T ln K / 2)` = 59,9.

**Pregunta 2 — cuánta etiqueta hace falta** (errores en la mitad atacada; Hedge y SGD ven las mismas
rondas etiquetadas):

| ρ | Hedge | SGD online | Semillas en que gana Hedge | Regret de Hedge | R/R(1) | `1/√ρ` |
|---|---|---|---|---|---|---|
| 1 | 133 ± 10 | **73 ± 6** | 0/20 | 30,9 ± 3,2 | 1,00 | 1,00 |
| 0,5 | 142 ± 11 | **100 ± 6** | 0/20 | 42,3 ± 4,7 | 1,37 | 1,41 |
| 0,2 | 157 ± 12 | **141 ± 9** | 2/20 | 60,1 ± 6,3 | 1,94 | 2,24 |
| 0,05 | **189 ± 13** | 210 ± 25 | **15/20** | 93,2 ± 12,3 | 3,01 | 4,47 |

- **El cruce entre combinar y reentrenar está entre ρ = 0,2 y 0,05.** Con etiquetas abundantes
  reentrenar gana siempre; con 5% de etiquetas combinar gana en 15 de 20 semillas. Para recuperarse,
  reentrenar tiene que aprender del orden de un peso por token nuevo; Hedge solo aprende K = 5 pesos.
  Matiza a Lowd & Meek: *"frequent retraining"* requiere etiquetas frecuentes.
- **El regret de Hedge escala con pendiente −0,37** en log-log (teoría −0,5). Hasta ρ = 0,2 sigue
  bien la ley `1/√ρ`; la desviación está en ρ = 0,05, donde el regret se acerca al techo de no
  aprender nunca (pesos uniformes siempre; 162,8 en la semilla 0) y satura por debajo de la ley.
- **La cota con ρ < 1.** Las pérdidas estimadas valen hasta `1/ρ`, así que la cota de la slide 73 no
  aplica. Se usa la versión basada en la varianza del estimador, `ln K/η + ηT/(2ρ)`, la misma técnica
  de Auer et al. para EXP3, con `η = √ρ · η_T`. SGD online no repondera por `1/ρ`: aprende de los
  ejemplos que tiene, como un filtro real con los reportes de sus usuarios.
- *Cuidado:* la semilla 0 sugería un empate cerca de ρ = 0,2; con 20 semillas reentrenar todavía gana
  ahí en 18 de 20.

---

## 7. Estructura de las 3 hojas

| Sección | Extensión | Contenido |
|---|---|---|
| 1. Introducción | ½ col | Spam como problema adversarial (slides 65-67); la afirmación de Lowd & Meek; las dos preguntas |
| 2. Marco formal | ½ col | Protocolo online, pérdida, regret, por qué oblivious (policy regret), las dos cotas |
| 3. Algoritmos | ½ col | Hedge; cada cota con su η; determinístico vs. randomizado y la construcción sintética; etiqueta parcial y por qué no EXP3 |
| 4. Setup experimental | ½ col | Dataset y baselines, los 5 expertos, el ataque y su calibración |
| 5. Resultados | 1 col + 3 figs + tabla | Fig. 1 (spam atrapado y pesos), Fig. 2 (regret y cotas; construcción sintética), Fig. 3 (barrido de ρ), y una tabla con BH, MCC y regret |
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
- **El experto robusto lo es por construcción.** El estructural sobrevive porque el ataque duplica
  vocales y no toca dígitos ni símbolos. Un ataque que ofuscara también los números de teléfono y
  las tarifas lo rompería. El resultado de Hedge depende de que exista un experto así, y eso es
  justamente lo que la tesis afirma.
- **Hedge no olvida.** La slide 73 dice que Hedge se adapta "aun si el entorno cambia con el
  tiempo", pero su garantía es contra el mejor experto *fijo* sobre todo el horizonte. Si el mejor
  experto cambia a mitad de camino, un experto con mucha pérdida acumulada tiene un peso del orden
  de `e^{-η·ΔL}` y tarda en recuperarse. En nuestro experimento no se nota porque el estructural ya
  era bueno antes del ataque; la herramienta para el caso general es Fixed-Share (Herbster & Warmuth
  1998), que compite contra el mejor experto *por tramos*.
- **Feedback de dos lados.** El modelo de etiqueta parcial supone que la etiqueta, cuando llega,
  llega para cualquier predicción. El caso realista es de un solo lado (*apple tasting*).

---

## 8. Entregables y plan de implementación

```
paper_spam_hedge/src/
  descargar_datos.py     # ✓ baja y descomprime el SMS Spam Collection de UCI
  datos.py               # ✓ carga del corpus y split warm-up / stream
  expertos.py            # ✓ los 5 expertos, con selección de hiperparámetros por CV
  metricas.py            # ✓ SC, BH, MCC
  estatico.py            # ✓ estático fijo (Naive Bayes); la selección por CV solo se reporta
  adversario.py          # ✓ duplicación de vocal + inyección acotada
  algoritmos.py          # ✓ Hedge det./random., cotas, η, construcción sintética
  cache_expertos.py      # ✓ cache en disco de los expertos entrenados por semilla
  sgd_online.py          # ✓ competidor que reentrena, α fijo, con etiqueta parcial
  verificar_etapa{2..6}.py   # ✓ verificaciones de cada etapa
  experimento.py         # ✓ todo lo anterior con 20 semillas, en paralelo y retomable
  agregar_resultados.py  # ✓ tablas con media ± desvío y resultados/resumen.json
  figuras.py             # ✓ las figuras del paper, desde los resultados guardados
paper_spam_hedge/paper/
  paper.tex              # pendiente
  referencias.bib        # ✓
```

**Costo de cómputo:** como los expertos quedan congelados después del warm-up, se entrenan una vez
por semilla y se cachean en `resultados/cache/`. A partir de ahí, las predicciones de los expertos
sobre el stream son una matriz fija de K×T, y correr Hedge con muchas semillas de muestreo o muchos
valores de ρ es casi gratis. Medido: ~100 s por semilla la primera vez (CV anidada incluida), ~18 s
con el cache. Con 6 procesos en paralelo, las 20 semillas tardan 6,4 minutos sin cache y 1,2 con
cache. `experimento.py` guarda cada semilla apenas termina, así que si se corta, se retoma.

Por semilla quedan dos archivos en `resultados/semillas/`: `semilla_<s>.json` con los números para
las tablas, y `semilla_<s>.npz` con las series temporales para las figuras (predicciones del estático
y de SGD, error medio de Hedge por ronda, pesos medios, curvas de regret y la matriz de pérdidas de
los expertos).

### Etapas

| # | Etapa | Verificación |
|---|---|---|
| 1 ✓ | Descarga y carga del dataset; split warm-up / stream | 5.574 mensajes, 747 spam (13,40%) |
| 2 ✓ | Los 5 expertos entrenados y congelados | SC sin drift contra los baselines de Almeida (ver abajo) |
| 3 ✓ | Adversario y su calibración | El SC del estático cae de ~80% a ~40%; **el estructural sigue siendo el mejor experto en la mitad atacada**; la distribución de longitudes del spam atacado se superpone con la del original |
| 4 ✓ | Hedge determinístico y randomizado | Sin drift, el regret del randomizado crece sublinealmente y queda bajo **la cota de su propio η**; la construcción sintética da regret lineal al determinístico |
| 5 ✓ | Estático y SGD online | Corren sobre la misma secuencia (huella del DataFrame atacado) |
| 6 ✓ | Barrido de ρ, con Hedge y SGD online | El regret de Hedge crece al bajar ρ, de forma compatible con `1/√ρ`; Hedge y SGD ven las mismas rondas etiquetadas |
| 7 ✓ | 20 semillas y agregación | Bandas de dispersión estables: SGD ±6, Hedge ±10, regret ±1,6. La primera corrida no las tenía (SGD ±32) y reveló los dos problemas corregidos en §4 |
| 8 ✓ | Las 3 figuras | Ancho exacto de 3,3 pulgadas con letra de 8 pt; paleta validada para daltonismo; revisadas en color y en escala de grises |
| 9 | Redacción del `.tex` | Entra en 3 páginas a dos columnas |

Los resultados de las etapas 5 a 8 están en §6.

**Baselines de la etapa 2** (Almeida et al. 2011, Tabla 7, mismo corpus) contra lo medido,
promediado sobre 5 semillas:

| Nuestro experto | Referencia de Almeida | SC Almeida | SC medido | MCC medido |
|---|---|---|---|---|
| Naive Bayes multinomial | MN TF NB + tok1 | 52,1% | 83,7 ± 4,2% | 0,879 |
| Regresión logística | SVM lineal + tok1 | 83,1% | 77,0 ± 1,6% | 0,846 |
| Árbol de decisión | C4.5 + tok2 | 75,3% | 76,4 ± 2,1% | 0,770 |
| Reglas por keywords | — | — | 80,5 ± 2,1% | 0,808 |
| Features estructurales (enriquecido, semilla 0) | — | — | 80,8% | 0,877 |
| Trivial "todo ham" | trivial rejection | 0% | 0% | — |

Nuestro Naive Bayes queda **por encima** del de Almeida porque el α elegido por CV suaviza mucho menos
que su Laplace. En el paper hay que decirlo así y no presentarlo como una reproducción de su
baseline. Almeida entrenan con el 70% del corpus y nosotros con el 20%.

**Riesgo conocido: hay poco spam.** Con 747 spams y warm-up del 20%, quedan ~598 en el stream y solo
**~300 sufren el ataque**. El regret se mueve en decenas de errores, no en miles. Por eso las 20
semillas no son opcionales; si las curvas quedan muy ruidosas, achicar el warm-up.

**Estimación:** ~1 día de trabajo.

**Estilo de código:** simple y autoexplicativo, sin one-liners, con los comentarios anclados a la
teórica (número de slide cuando corresponda), igual que en las guías de la materia.

**Entorno:** `~/.pyenv/versions/3.12.13/bin/python3` (numpy 2.4.4, pandas 3.0.2, sklearn 1.8.0,
matplotlib 3.10.9). No hay LaTeX ni pandoc local: el `.tex` se compila en Overleaf.

---

## 9. Decisiones

### Resueltas en las etapas 5 a 7

- **Qué η usar en el experimento principal:** el sintonizado por T. El small-loss es mejor, pero
  requiere conocer `L_best` de antemano, y con drift no se sabe; queda como referencia de oráculo en
  F3.
- **Qué Hedge va en F1:** el randomizado, que es el que tiene garantía. El determinístico va en la
  tabla.
- **El modelo estático:** Naive Bayes, fijo por diseño. La CV habría elegido al estructural en 6 de
  20 semillas. Detalle en §4.
- **El α de SGD online:** 1e-5, fijo. La CV lo elegía mal para un modelo que tiene que adaptarse.
  Detalle en §4.

### Resueltas en la etapa 8

- **Espacio:** F1 y F2 van fusionadas en una figura de dos paneles con el eje temporal compartido,
  como sugirió el revisor. El paper queda con 3 figuras, y el eje compartido hace evidente que la
  caída del spam atrapado por Hedge coincide con la migración de peso.
- **Qué cota de peor caso usar:** la de Hoeffding, `√(T ln K / 2)` en t = T, con una nota sobre la
  constante de la slide (§2).

### Abiertas

Ordenadas por cuánto afectan lo que falta. Cada una lleva una recomendación.

1. **Ablación del experto estructural.** Correr Hedge también con la versión simple del estructural
   mostraría directamente la condición de la tesis: sin un experto que sobreviva no hay
   recuperación, con él sí. Cuesta poco (una corrida más) y ocupa una línea de tabla.
   *Recomendación:* hacerlo si entra.
2. **`norm='l2'` en el vectorizador.** Para fidelidad con el `MN TF NB` de Almeida habría que usar
   conteos crudos (`norm=None`) y volver a elegir α. *Recomendación:* dejarlo como está y declararlo;
   no cambia ninguna conclusión.
3. **Referencia de Herbster & Warmuth (1998).** Si se menciona Fixed-Share en la discusión hace falta
   la cita, que no está en `referencias/`.
4. **Adversario adaptativo.** Queda fuera de la corrida y se menciona en la discusión con la
   degradación teórica a `T^{2/3}` de Cesa-Bianchi, Dekel & Shamir.

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
es señal fuerte de spam, el spammer escribe `viiagra`, y para el modelo esa palabra no existe.

**SGD online.** Dos cosas juntas. *SGD* (descenso por gradiente estocástico) es una forma de
entrenar: en vez de darle los 5.000 mensajes juntos, el modelo mira un ejemplo, corrige un poco sus
parámetros en la dirección que reduce el error, mira el siguiente, corrige otra vez. *Online* quiere
decir que eso nunca termina: cada mail nuevo, una vez conocida su etiqueta, se usa para corregir un
poco más. En scikit-learn es el método `partial_fit`.

Está en el experimento porque es el único competidor que se actualiza solo. Cuando el spammer
empieza con `viiagra`, después de unos ejemplos etiquetados este modelo aprende por su cuenta que
`viiagra` es spam. Los cinco expertos están congelados y nunca pueden aprender eso: Hedge solo puede
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

**Duplicación de vocal.** La ofuscación que usa el spammer en nuestro ataque: repetir una vocal de
la palabra delatora (`viagra` → `viiagra`). Para el filtro es una palabra que nunca vio, pero para
una persona se sigue leyendo igual.

**Leetspeak.** Escribir con números que parecen letras: `4` por `a`, `1` por `i`, `0` por `o`, `3`
por `e`, `5` por `s`. Fue la primera versión de nuestro ataque y se descartó porque, al agregar
dígitos, hacía que el experto estructural detectara *más* spam en lugar de menos (§5).

**Semillas (seeds).** El experimento tiene componentes al azar (el orden de los mensajes, el sorteo
de EXP3). Correrlo 20 veces con distinto azar y promediar evita que el resultado sea casualidad de
una corrida.

**HashingVectorizer.** El texto hay que convertirlo en números. Esto manda cada palabra a una
casilla fija de un vector grande usando una función hash. La alternativa clásica arma primero la
lista de todas las palabras que existen; el hashing no necesita esa lista, y por eso tolera que
aparezcan palabras nuevas como `viiagra` sin romperse.

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

### Agregados en la etapa 7

**Validación cruzada (CV, *cross-validation*).** Una forma de estimar qué tan bien va a andar un
modelo con datos que no vio, sin gastar datos aparte. Se parten los datos en 5 pedazos (*folds*), se
entrena con 4 y se evalúa con el que quedó afuera, y se repite 5 veces rotando cuál queda afuera. El
promedio estima el desempeño con datos nuevos. En este trabajo se usa siempre **solo sobre el
warm-up**, nunca sobre el stream. Su límite, que vimos en la etapa 7: responde "¿qué tan bien
clasifica datos como los del warm-up?", y como en el warm-up no hay ataque, no puede responder
"¿qué tan rápido se adapta cuando el spammer cambia?".

**Regla de un error estándar.** Criterio para elegir entre valores de un hiperparámetro que dan
resultados casi iguales en la validación cruzada: en lugar de quedarse con el mejor, se elige el más
simple (el más regularizado) entre los que están a menos de un error estándar del mejor. Evita
perseguir diferencias que son ruido. Es la regla correcta para generalizar, y la equivocada para un
modelo que tiene que adaptarse rápido, porque lo que prefiere —más regularización— es justamente lo
que frena la adaptación.

**Semilla de permutación y semilla de muestreo.** Las dos fuentes de azar del experimento. La de
*permutación* decide en qué orden llegan los mensajes, y con eso cambia todo lo demás: qué mensajes
van al warm-up, cómo quedan entrenados los expertos, qué se ataca. La de *muestreo* decide, dentro de
una misma permutación, qué experto sortea Hedge randomizado en cada ronda y qué rondas tienen
etiqueta. Los "± desvío" de las tablas son entre semillas de permutación.
