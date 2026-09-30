# Plan de trabajo — Paper: aprendizaje online con Hedge para detección de spam

**Materia:** Tópicos Avanzados en Ciencia de Datos (MCD210) — Daniel Fraiman
**Formato de entrega:** ~3 páginas, LaTeX a dos columnas (compilación en Overleaf), en español
**Origen del tema:** `referencias/clase_2_ventas_online.pdf`, slide 79 ("Ideas para el paper"), ítem 3:
*"Extender el caso de detección de spam a un clasificador que se reentrena online con Hedge,
y comparar contra un modelo estático."*
**Estado:** etapas 1-4 implementadas y verificadas. El plan incorpora lo que se aprendió al
implementarlas (ataque por duplicación de vocal, experto estructural enriquecido, cada cota con su
η, la construcción sintética). Quedan decisiones menores abiertas (§9).

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
nada. Con la versión enriquecida (§4), Hedge comete 117 errores en la mitad atacada contra 193 del
estático (semilla 0).

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

**El modelo estático** se elige con el mismo criterio, por validación cruzada anidada sobre el
warm-up: Naive Bayes (MCC 0,869), seguido de la regresión logística (0,854) y el estructural (0,845).
El margen sobre el estructural es chico y hay que verificar que se mantenga en todas las semillas
(§9).

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
- 20 semillas, variando la permutación del stream y el muestreo del Hedge randomizado.
- Resultados como media con banda de dispersión.

### Métricas: no reportar accuracy

En este corpus el clasificador trivial "todo es ham" saca **86,95% de accuracy** (Almeida et al.,
Tabla 7, fila *trivial rejection*). Cualquier número de accuracy es engañoso. Reportamos lo que usa
el paper del dataset:

- **Spam Caught (SC%)** — qué fracción del spam se atrapa.
- **Blocked Hams (BH%)** — qué fracción del correo legítimo se bloquea por error.
- **MCC** — coeficiente de correlación de Matthews, robusto al desbalance.

**Cuidado al reportar el regret:** hay que decir siempre *quién* fue el mejor experto en
retrospectiva, no solo el número. Con la primera versión del estructural existía el riesgo de que
fuera un experto casi trivial; con la enriquecida, en la semilla 0 el mejor experto fijo sobre el
stream atacado es el estructural (160 errores totales contra 255 de Naive Bayes).

### Figuras y tabla

| | Contenido | Qué muestra |
|---|---|---|
| **F1** | SC en ventana móvil de los 3 competidores principales, con el drift marcado. BH va a la tabla | El estático se cae y no se recupera; Hedge se recupera casi en el acto; SGD-online aprende los tokens nuevos |
| **F2** | Evolución de los pesos `w^(i)_t` de Hedge (stackplot) | Ver la lectura correcta abajo |
| **F3** | Panel A: regret de Hedge randomizado con η de peor caso y con η small-loss, cada uno contra **su** cota. Panel B: la construcción sintética, determinístico vs. randomizado | Que cada cota vale para su configuración; que el small-loss es mejor algoritmo; que el determinístico no tiene garantía |
| **T1** | Tabla: regret final, SC y BH por valor de ρ | El costo de la etiqueta escasa, contrastado con `1/√ρ` |

**La lectura correcta de F2.** El plan original esperaba que la masa "migrara" de los expertos
léxicos al estructural *a causa* del ataque. No es lo que pasa: el estructural enriquecido ya era
apenas mejor que Naive Bayes antes del ataque (58 contra 62 errores en la primera mitad), así que
Hedge llega al ataque con el peso repartido entre los dos (0,42 y 0,34). Cuando el ataque rompe a
Naive Bayes, la mayor parte del peso ya estaba sobre el experto robusto, y al final del stream tiene
0,994. No hay migración provocada por el ataque: hay **hedging** literal. El algoritmo tenía la
apuesta cubierta, y por eso la recuperación es casi instantánea.

Resultado de la semilla 0 en la mitad atacada: Hedge randomizado **117,3 ± 5,1 errores**, estático
**193**.

---

## 7. Estructura de las 3 hojas

| Sección | Extensión | Contenido |
|---|---|---|
| 1. Introducción | ½ col | Spam como problema adversarial (slides 65-67); la afirmación de Lowd & Meek; las dos preguntas |
| 2. Marco formal | ½ col | Protocolo online, pérdida, regret, por qué oblivious (policy regret), las dos cotas |
| 3. Algoritmos | ½ col | Hedge; cada cota con su η; determinístico vs. randomizado y la construcción sintética; etiqueta parcial y por qué no EXP3 |
| 4. Setup experimental | ½ col | Dataset y baselines, los 5 expertos, el ataque y su calibración |
| 5. Resultados | 1 col + 3 figs + tabla | F1, F2, F3 (dos paneles), T1 con lectura de cada una |
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
  estatico.py            # ✓ selección del modelo estático por CV anidada
  adversario.py          # ✓ duplicación de vocal + inyección acotada
  algoritmos.py          # ✓ Hedge det./random., cotas, η, construcción sintética
  cache_expertos.py      # ✓ cache en disco de los expertos entrenados por semilla
  verificar_etapa{2,3,4}.py  # ✓ verificaciones de cada etapa
  experimento.py         # pendiente: estático, Hedge, SGD online, ρ, 20 semillas
  figuras.py             # pendiente: F1, F2, F3 y la tabla T1
paper_spam_hedge/paper/
  paper.tex              # pendiente
  referencias.bib        # ✓
```

**Costo de cómputo:** la selección de hiperparámetros por CV anidada tarda unos minutos por semilla.
Como los expertos quedan congelados después del warm-up, se entrenan una vez por semilla y se cachean
en `resultados/cache/`. A partir de ahí, las predicciones de los expertos sobre el stream son una
matriz fija de K×T, y correr Hedge con muchas semillas de muestreo o muchos valores de ρ es casi
gratis.

### Etapas

| # | Etapa | Verificación |
|---|---|---|
| 1 ✓ | Descarga y carga del dataset; split warm-up / stream | 5.574 mensajes, 747 spam (13,40%) |
| 2 ✓ | Los 5 expertos entrenados y congelados | SC sin drift contra los baselines de Almeida (ver abajo) |
| 3 ✓ | Adversario y su calibración | El SC del estático cae de ~80% a ~40%; **el estructural sigue siendo el mejor experto en la mitad atacada**; la distribución de longitudes del spam atacado se superpone con la del original |
| 4 ✓ | Hedge determinístico y randomizado | Sin drift, el regret del randomizado crece sublinealmente y queda bajo **la cota de su propio η**; la construcción sintética da regret lineal al determinístico |
| 5 | Estático y SGD online | Corren sobre la misma secuencia |
| 6 | Barrido de ρ | El regret crece al bajar ρ, de forma compatible con `1/√ρ` |
| 7 | 20 semillas y agregación | Bandas de dispersión estables |
| 8 | Las 3 figuras y la tabla | Legibles en blanco y negro, a ancho de columna |
| 9 | Redacción del `.tex` | Entra en 3 páginas a dos columnas |

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

## 9. Decisiones abiertas

Ordenadas por cuánto afectan lo que falta implementar. Cada una lleva una recomendación.

1. **Qué η usar en el experimento principal.** El sintonizado por `L_best` es mejor, pero requiere
   conocer `L_best` de antemano, y con drift no se sabe. *Recomendación:* η sintonizado por T en el
   experimento; el small-loss solo en F3 como referencia de oráculo.
2. **Qué Hedge va en F1.** *Recomendación:* el randomizado, que es el que tiene garantía. El
   determinístico se reporta en la tabla.
3. **Estabilidad del modelo estático entre semillas.** En la semilla 0 la CV elige Naive Bayes por
   poco margen sobre el estructural (0,869 contra 0,845). Si en alguna semilla elige al estructural,
   el estático ya sería robusto y esa semilla deja de medir lo que queremos. Opciones: fijar Naive
   Bayes como estático por diseño ("el filtro bayesiano, que es el que atacan Lowd & Meek"), o
   mantener la CV y reportar en cuántas semillas cambia. *Recomendación:* verificarlo en la etapa 7
   antes de decidir.
4. **Espacio.** F3 ahora tiene dos paneles. La sugerencia del revisor de fusionar F1 y F2 en una
   figura con el eje temporal compartido vuelve a ser atendible. *Recomendación:* decidir al armar
   las figuras, con los gráficos a la vista.
5. **Ablación del experto estructural.** Correr Hedge también con la versión simple del estructural
   mostraría directamente la condición de la tesis: sin un experto que sobreviva no hay
   recuperación, con él sí. Cuesta poco (una corrida más) y ocupa una línea de tabla.
   *Recomendación:* hacerlo si entra.
6. **`norm='l2'` en el vectorizador.** Para fidelidad con el `MN TF NB` de Almeida habría que usar
   conteos crudos (`norm=None`) y volver a elegir α. *Recomendación:* dejarlo como está y declararlo;
   no cambia ninguna conclusión.
7. **Referencia de Herbster & Warmuth (1998).** Si se menciona Fixed-Share en la discusión hace falta
   la cita, que no está en `referencias/`.
8. **Adversario adaptativo.** Sin cambios respecto de la versión anterior del plan: queda fuera de la
   corrida y se menciona en la discusión con la degradación teórica a `T^{2/3}` de Cesa-Bianchi,
   Dekel & Shamir.

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
