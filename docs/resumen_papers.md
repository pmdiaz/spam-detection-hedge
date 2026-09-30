# Papers de referencia: resumen y aportes al trabajo

Documento complementario de [`plan.md`](plan.md).
Cubre los cinco papers de `referencias/` que usaremos como referencias.
(Se excluye Blanchard & Kpotufe 2025, demasiado teórico para 3 páginas.)

> **Aviso:** la lectura de Auer et al. (2002) reveló un problema en el diseño del experimento —
> el competidor EXP3 de §3 del plan no se sostiene tal como está planteado. Ver **idea A3**.

---

# Parte 1 — Resúmenes

## 1. Freund & Schapire (1997) — *A Decision-Theoretic Generalization of On-Line Learning and an Application to Boosting*

`referencias/freund_schapire_1997_hedge.pdf` · JCSS 55(1), 119-139 · **La fuente original de Hedge**

### Qué hace

Plantea el *problema de asignación online*: en cada ronda t el jugador reparte una distribución
`w_t` sobre N estrategias, el entorno revela un vector de pérdidas `ℓ_t ∈ [0,1]^N`, y el jugador
sufre la **pérdida de la mezcla** `Σ_i w_t(i) · ℓ_t(i)`. Es una generalización del modelo de
predicción con expertos a cualquier función de pérdida acotada.

El algoritmo, **Hedge(β)**, es la generalización de la regla de pesos multiplicativos de
Littlestone & Warmuth:

```
w_{t+1}(i) = w_t(i) · β^{ℓ_t(i)}        con β ∈ [0,1)
```

Es la misma regla de la slide 72 escrita con base β en vez de exponencial: `β = e^{-η}`.

### Resultados principales

**Teorema 2** (cota general, con prior arbitrario `w_1`):

```
L_Hedge  ≤  ( −ln w_1(i) − L_i · ln β ) / (1 − β)        para todo experto i
```

Con prior uniforme `w_1(i) = 1/N`, el término `−ln w_1(i)` se vuelve `ln N`.

**Cota derivada** (Lema 4, ec. 11), que es la forma que importa:

```
L_Hedge  ≤  L_best  +  √( 2 · L_best · ln N )  +  ln N
```

De ahí se obtiene el peor caso `O(√(T ln N))`, que es la cota `√(2T log K)` de la slide 73.

### Dos detalles que suelen pasarse por alto

1. **La cota depende de `L_best`, no de T.** Los autores lo dicen explícitamente: *"if L is close
   to zero, then the rate of convergence will be much faster, roughly O((ln N)/T)"*. Es una cota
   de tipo *small-loss*: si el mejor experto es bueno, el regret es mucho menor que `√T`.
2. **El prior inicial puede no ser uniforme** y la cota es más fuerte para los expertos que
   reciben más peso inicial (aparece `−ln w_1(i)`, no `ln N`). Los pesos iniciales funcionan como
   un prior sobre qué experto esperamos que ande bien.

El término `√(2 L ln N)` no se puede mejorar más que por una constante (cota inferior de
Cesa-Bianchi et al.).

### Y la parte de boosting

La segunda mitad del paper deriva **AdaBoost** como aplicación del mismo esquema, invirtiendo los
roles: los "expertos" pasan a ser los ejemplos de entrenamiento. Es la razón por la que el paper es
célebre, pero no nos sirve para el trabajo.

---

## 2. Auer, Cesa-Bianchi, Freund & Schapire (2002) — *The Nonstochastic Multiarmed Bandit Problem*

`referencias/auer_etal_2002_exp3.pdf` · SIAM J. Comput. 32(1), 48-77 · **EXP3 y EXP4**

### Qué hace

Resuelve el problema de bandits **sin ningún supuesto estadístico** sobre cómo se generan las
recompensas: un adversario tiene control completo sobre los pagos. Es la contraparte adversarial de
los bandits estocásticos de la clase 2 (ε-greedy, UCB, Thompson).

La medida de desempeño es el **weak regret**: la diferencia entre la ganancia del mejor brazo fijo
en retrospectiva y la ganancia esperada del algoritmo.

### El algoritmo EXP3

*"Exponential-weight algorithm for Exploration and Exploitation"*. Es explícitamente **una variante
de Hedge** adaptada al caso en que no se observan todas las recompensas:

```
1.  p_i(t) = (1 − γ) · w_i(t)/Σ_j w_j(t)  +  γ/K
2.  se sortea el brazo i_t ~ p(t)
3.  se recibe la recompensa x_{i_t}(t) ∈ [0,1]
4.  x̂_j(t) = x_j(t)/p_j(t)  si j = i_t,  0 si no
    w_j(t+1) = w_j(t) · exp( γ · x̂_j(t) / K )
```

Dos ingredientes que no están en Hedge:

- **La mezcla con la uniforme** (`γ/K`): garantiza exploración forzada, que cada brazo se pruebe y
  que las probabilidades nunca colapsen a cero.
- **El estimador por importance sampling** (`x̂_j = x_j/p_j`): divide la recompensa observada por la
  probabilidad de haber elegido ese brazo. Es **insesgado**, `E[x̂_j(t) | historia] = x_j(t)`, y es
  lo que permite actualizar pesos habiendo visto un solo brazo.

### Cotas

**Teorema 3.1:** `G_max − E[G_EXP3] ≤ (e−1)·γ·G_max + K·ln K / γ`

**Corolario 3.2**, optimizando γ con `g ≥ G_max` conocido de antemano:

```
G_max − E[G_EXP3]  ≤  2√(e−1) · √(g · K · ln K)  ≤  2.63 · √(g · K · ln K)
```

Comparado con el `√(2 T ln K)` de Hedge, aparece un factor **√K**: es el precio de no observar las
recompensas de los brazos que no jugaste.

### Las variantes

| Algoritmo | Qué resuelve |
|---|---|
| **EXP3** | El caso base, pero necesita conocer una cota `g ≥ G_max` de antemano |
| **EXP3.1** | Procede por épocas y logra `O(√(K · G_max · ln K))` uniformemente en T, sin conocer g. Igual que en Freund & Schapire, la cota depende de `G_max` y no de T |
| **EXP3.P** | Cota `O(√(K T ln(KT/δ)))` **con probabilidad ≥ 1−δ**, no solo en esperanza |

### Cota inferior

Existe una asignación de recompensas que fuerza regret `Ω(√(K T))` a **cualquier** algoritmo;
concretamente, al menos `(1/20)·min{√(KT), T}`. Queda una brecha de `√(ln K)` respecto de la cota
superior, que los autores dejan como problema abierto.

### EXP4

*"Exponential-weight algorithm for Exploration and Exploitation using Expert advice"*. Es EXP3
ligeramente modificado para el caso en que hay **N expertos** que aconsejan sobre **K acciones**.

**Teorema 7.1:** `G̃_max − E[G_EXP4] ≤ (e−1)·γ·G̃_max + K·ln N / γ`, o sea `O(√(g·K·ln N))`.

Lo notable: la dependencia en la cantidad de expertos es solo **logarítmica**, así que N puede ser
enorme (incluso exponencial) mientras K sea chico.

**Requisito técnico:** la demostración necesita que el **experto uniforme** (el que reparte 1/K a
todas las acciones) esté en la familia. Se puede agregar siempre, a costa de N+1.

### Nota sobre el adversario

Las cotas de weak regret se prueban contra un adversario **oblivious**. Los autores lo dicen al
armar la cota inferior: *"the adversary strategy we have defined is oblivious to the actions of the
player"*. Esto conecta directamente con Cesa-Bianchi, Dekel & Shamir (paper 5).

---

## 3. Lowd & Meek (2005) — *Good Word Attacks on Statistical Spam Filters*

`referencias/lowd_meek_2005_good_word_attacks.pdf` · CEAS 2005 · **El ataque**

### Qué hace

Estudia cómo un spammer evade filtros estadísticos agregando palabras típicas de correo legítimo
("good words"). Ataca dos filtros: Naive Bayes y máxima entropía (maxent), ambos representables
como un conjunto de pesos por feature más un umbral.

### La distinción central: ataque pasivo vs. activo

| | Qué puede hacer el atacante | Resultado |
|---|---|---|
| **Pasivo** | Arma la lista de palabras **sin ningún feedback** del filtro. Son "conjeturas educadas" basadas en corpus públicos (diccionario, Reuters, USENET) | Con **≤150 palabras** agregadas pasa el 50% del spam que antes era bloqueado |
| **Activo** | Puede mandar mensajes de prueba al filtro y ver si los marca | Con **30 palabras** logra lo mismo |

El activo requiere acceso de usuario al filtro, así que no siempre es posible.

### Cómo miden la fuerza del ataque

Normalizan los pesos de cada filtro de modo que, con una tasa de falsos positivos fija del 10%, el
score mediano de un spam verdadero quede 1 por encima del umbral. Con esa normalización la lectura
es directa: **una lista de palabras cuyos pesos suman −1 alcanza para pasar la mitad del spam
bloqueado**. Un peso de −0.01 aporta el 1% de lo necesario.

### Conclusión de los autores

> *"By adding a relatively small number of easily found words, an attacker can get 50% of currently
> blocked spam past a typical spam filter. (...) **The only remedy we know of is frequent
> retraining**: if we cannot prevent attacks, we can still seek to limit their impact."*

Y agregan que el reentrenamiento funciona mejor si se **aumenta el peso de los ejemplos recientes
por duplicación**.

En trabajo futuro mencionan como pendiente *"characterizing other spam attacks (e.g., word
obfuscation)"* — o sea, ellos solo **agregan** palabras buenas, no **ofuscan** las malas.

---

## 4. Almeida, Gómez Hidalgo & Yamakami (2011) — *Contributions to the Study of SMS Spam Filtering*

`referencias/almeida_etal_2011_sms_spam.pdf` · DocEng'11 · **El dataset y sus baselines**

### Qué hace

Presenta el **SMS Spam Collection**, el corpus que vamos a usar, y evalúa sobre él una batería
grande de clasificadores para dejar baselines de comparación.

### El dataset

| | Cantidad | % |
|---|---|---|
| Ham | 4.827 | 86,60 |
| Spam | 747 | 13,40 |
| **Total** | **5.574** | 100 |

Tokens: 81.175 en total, 14,56 por mensaje en promedio.

**Dato que nos importa mucho:** el spam promedia **23,48 tokens** por mensaje y el ham **13,18**.
Los mensajes de spam son casi el doble de largos.

Tokens más frecuentes en spam: `to`, `call`, `a`, `your`, `you`, `for`, `or`, `the`, `free`, `txt`.
En ham: `i`, `you`, `to`, `a`, `the`, `in`, `and`, `u`, `me`, `is`.

### Metodología

Dos tokenizadores (`tok1` corta en puntos y comas, `tok2` conserva más símbolos), **sin** stemming,
**sin** eliminación de stopwords y **sin** reducción de dimensionalidad — porque los mensajes son
muy cortos. Split 70/30.

Métricas: **Spam Caught (SC%)**, **Blocked Hams (BH%)**, Accuracy y **MCC** (coeficiente de
correlación de Matthews), que es el criterio por el que ordenan los resultados.

### Resultados (Tabla 7, los relevantes)

| Clasificador | SC % | BH % | Acc % | MCC |
|---|---|---|---|---|
| SVM + tok1 | 83,10 | 0,18 | 97,64 | **0,893** |
| Boosted NB + tok2 | 84,48 | 0,53 | 97,50 | 0,887 |
| C4.5 + tok2 | 75,25 | 2,03 | 95,00 | 0,770 |
| Bernoulli NB + tok1 | 54,03 | 0,00 | 94,00 | 0,711 |
| Multinomial TF NB + tok1 | 52,06 | 0,00 | 93,74 | 0,697 |
| 1-NN + tok2 | 43,81 | 0,00 | 92,70 | 0,636 |
| Boolean NB + tok1 | 98,04 | 26,01 | 77,13 | 0,507 |
| **Trivial rejection (todo ham)** | **0,00** | **0,00** | **86,95** | — |

### La moraleja de esa tabla

El SVM lineal gana. Pero lo verdaderamente instructivo es el contraste entre las últimas dos filas:

- El clasificador **trivial que dice "todo es ham" saca 86,95% de accuracy** sin hacer nada.
- Naive Bayes multinomial saca 93,74% de accuracy pero **solo atrapa el 52% del spam**.
- Boolean NB atrapa el 98% del spam pero bloquea el 26% del correo legítimo: inservible.

Los autores lo resumen así: *"although most of them have obtained accuracy rate superior than 90%,
they have correctly filtered about only 50% of spams or even less"*.

---

## 5. Cesa-Bianchi, Dekel & Shamir (2013) — *Online Learning with Switching Costs and Other Adaptive Adversaries*

`referencias/cesabianchi_etal_2013_adaptive_adversaries.pdf` · arXiv:1302.4387v2 · **La teoría de adversarios adaptativos**

### Qué hace

Estudia el poder de distintos tipos de adversario **adaptativo** (o sea, no-oblivious) en predicción
con expertos, tanto con información completa como con feedback bandit.

### Aporte conceptual 1: la definición estándar de regret no sirve contra adversarios adaptativos

Con un adversario adaptativo la pérdida en la ronda t es `f_t(X_{1:t})`: depende de **toda** la
historia de acciones del jugador. Hay dos definiciones posibles de regret:

```
(1)  policy regret:  R_T = Σ_t f_t(X_{1:t})  −  min_x Σ_t f_t(x, x, ..., x)
(2)  regret usual:   R_T = Σ_t f_t(X_{1:t})  −  min_x Σ_t f_t(X_{1:t−1}, x)
```

La (2) es la más común en la literatura (y la de la slide 73), pero los autores la declaran
*"clearly inadequate for measuring a player's performance against an adaptive adversary"*: el
término `f_t(X_{1:t−1}, x)` pregunta "qué hubiera pasado si en esta ronda jugaba x", y esa cantidad
casi no tiene interpretación si el adversario venía reaccionando a lo que el jugador hacía.

La correcta es la (1), el **policy regret**: la acción alternativa se juega **desde el principio**,
y el adversario reacciona a ella.

### Aporte conceptual 2: contra adversarios adaptativos arbitrarios no hay nada que hacer

Citando a Arora et al. (2012): un adversario adaptativo sin restricciones puede **forzar regret
lineal** a cualquier algoritmo. Por eso la literatura restringe a adversarios de **memoria acotada**:
la pérdida de la ronda t solo puede depender de las últimas `m` acciones del jugador.

### Aporte conceptual 3: las tasas según el tipo de adversario (Tabla 1)

| Feedback | Oblivious | Switching costs | Memoria acotada | Adaptativo general |
|---|---|---|---|---|
| **Información completa** | `√T` | `√T` | `T^{2/3}` | `T` |
| **Bandit** | `√T` | `T^{2/3}` | `T^{2/3}` | `T` |

La contribución técnica propia del paper es la cota inferior `Ω(T^{2/3})` que cierra varias de esas
casillas.

### Advertencia que deja el paper

EXP3 tiene extensiones "al caso adaptativo" con cota `O(√T)`, pero usan la definición (2), no policy
regret. **No son comparables** y es un error fácil de cometer.

---

# Parte 2 — Ideas que podemos usar

Ordenadas por cuánto cambian el trabajo.

## A. Ideas que cambian el contenido del paper

### A1. La teórica mezcla dos algoritmos distintos, y eso da material propio

**De dónde sale:** Freund & Schapire, comparado con las slides 71-73.

La slide 71 define la predicción como **voto pesado determinístico**:

```
ŷ_t = 1  si  Σ_i f^(i)(x_t) · w_t(i) > 1/2,   0 si no
```

Pero la cota `√(2T log K)` de la slide 73 es la de **Hedge**, que no es eso: en Hedge la pérdida de
la ronda es la de la **mezcla**, `Σ_i w_t(i) · ℓ_t(i)`, que en la práctica se realiza muestreando un
experto `i ~ w_t` y jugando su predicción.

No es un detalle de notación. Para un algoritmo **determinístico** no existe cota de regret
sublineal en el peor caso: el adversario ve tu predicción antes de fijar la etiqueta, te hace errar
siempre, y el mejor experto fijo erra la mitad — regret lineal. La cota clásica de Weighted Majority
es **multiplicativa** (del orden de `2,41 · (L_best + log₂ K)` con β=1/2), no aditiva. La
aleatorización no es un adorno de la demostración: es lo que hace posible la garantía.

**Qué hacemos:** implementar **las dos variantes**, la determinística de la slide y la randomizada
de Freund & Schapire, y mostrar empíricamente la brecha entre ambas y contra la cota. Cuesta muy
poco código y es exactamente "profundizar" un tema de la materia, que es lo que pide la consigna.

### A2. La cota correcta no es `√(2T log K)` sino la que depende de `L_best`

**De dónde sale:** Freund & Schapire, Lema 4 / ec. (11). Reaparece en EXP3.1 (Auer et al., §4), que
también consigue una cota en `G_max` en lugar de T.

La cota fina es `L_Hedge ≤ L_best + √(2 · L_best · ln N) + ln N`, que depende de la pérdida del
mejor experto y no del horizonte. Con nuestros números (estimación a confirmar en la corrida):

| | Cálculo | Valor aprox. |
|---|---|---|
| Cota de peor caso | `√(2 · 4459 · ln 5)` | ~120 errores |
| Cota small-loss con `L_best ≈ 150` | `√(2 · 150 · ln 5)` | ~22 errores |

Son órdenes distintos. Y lo interesante: **la cota small-loss predice el escalón del drift**. Antes
del ataque `L_best` es chico y la cota es apretada; después del ataque `L_best` crece y la cota se
afloja. O sea que la forma de la curva teórica debería seguir a la empírica, cosa que la cota
`√(2T log K)` —que solo crece con T— no puede hacer.

**Qué hacemos:** en la figura F3 graficar **las dos cotas** junto al regret empírico. Es el tipo de
resultado que justifica un paper: la teórica da la cota floja, nosotros mostramos cuál es la que
realmente describe lo que pasa.

### A3. ⚠️ El feedback bandit, tal como está en el plan, colapsa en información completa

**De dónde sale:** Auer et al., al leer con precisión qué se observa en cada ronda.

El competidor (iv) de §3 del plan dice: *"EXP3: como Hedge pero observando solo la pérdida del
experto jugado"*. **Eso no se sostiene en nuestro setting.** El razonamiento:

1. Los expertos son funciones determinísticas `f^(i)` y nosotros tenemos el mensaje `x_t`, así que
   podemos evaluar `f^(i)(x_t)` para los cinco sin costo.
2. Jugamos `ŷ_t = f^(I_t)(x_t)` y observamos `ℓ_t(I_t) = 1{f^(I_t)(x_t) ≠ y_t}`.
3. Pero **conocemos** `f^(I_t)(x_t)`. Saber si acertamos **revela `y_t`**.
4. Con `y_t` conocido, `ℓ_t(i) = 1{f^(i)(x_t) ≠ y_t}` es computable para los cinco expertos.

O sea: en clasificación binaria con la pérdida revelada, **el feedback bandit es información
completa**. No hay ningún precio que medir y EXP3 estaría resolviendo un problema que no tenemos.

El feedback bandit es genuinamente parcial cuando la recompensa contrafáctica **no se puede
inferir** — brazos que son anuncios distintos y nunca sabés si el otro hubiera sido clickeado, por
ejemplo. No es nuestro caso.

**Tres salidas posibles:**

| | Modelo | Veredicto |
|---|---|---|
| **(a)** | **Observación parcial de la etiqueta.** El usuario reporta solo algunos mensajes: `y_t` se revela con probabilidad ρ y en las rondas sin etiqueta nadie actualiza. Con estimador insesgado `ℓ̂ = ℓ/ρ`, el regret escala como `√(T ln K / ρ)` | **Recomendada.** Realista en spam, trivial de implementar (saltear la actualización), y conserva la pregunta 2 con una respuesta medible: cómo se degrada el regret al bajar ρ |
| **(b)** | **Feedback de un solo lado (*apple tasting*).** Si mandás el mensaje a spam el usuario no lo mira y nunca sabés si erraste; solo aprendés la etiqueta cuando predecís "ham" | Más fiel al problema real, pero necesita otro algoritmo y otra referencia que no tenemos |
| **(c)** | Dejar EXP3 declarando que el supuesto es artificial | Barato y flojo |

**Dónde sigue sirviendo Auer et al. si tomamos (a):** el estimador por importance sampling y la
mezcla con la uniforme son exactamente la maquinaria que necesita la opción (a) — el `1/ρ` es el
mismo truco que el `1/p_j`. Y EXP3/EXP4 quedan citados como los algoritmos del caso en que el
contrafáctico sí es inobservable, que es la diferencia que queremos explicar.

**Esto reemplaza la pregunta 2 de §1 del plan**, que pasa de "¿cuál es el precio de la información?"
a "¿cuánta etiqueta hace falta?". La respuesta esperada deja de ser un factor `√K` y pasa a ser
`1/√ρ`.

### A4. El paper tiene un interlocutor concreto

**De dónde sale:** Lowd & Meek, conclusión.

Ellos concluyen que *"the only remedy we know of is frequent retraining"*. Nuestra pregunta 1 —si
combinar expertos congelados puede sustituir al reentrenamiento— está poniendo a prueba una
afirmación publicada, no comparando algoritmos en el vacío.

**Qué hacemos:** reescribir la introducción alrededor de esa cita. El paper pasa a tener una tesis
discutible en vez de un "comparamos tres cosas".

Ojo con la trampa: ellos ya mostraron que reentrenar funciona, así que es probable que SGD-online
gane. **Nuestra contribución no es que Hedge gane**, es cuantificar qué fracción de la brecha
cubre Hedge sin tocar los expertos, y mostrar dónde está el límite de esa estrategia.

### A5. Policy regret justifica formalmente la decisión del adversario

**De dónde sale:** Cesa-Bianchi, Dekel & Shamir, secciones 1-1.2. Refuerza: Auer et al. también
prueban sus cotas contra un adversario oblivious.

Mi argumento en §5 del plan era práctico ("así todos rinden el mismo examen"). El argumento real es
más fuerte: contra un adversario adaptativo, la definición de regret que usa la teórica **no está
bien definida**, y hace falta policy regret. Y además, sin restringir la memoria del adversario, el
regret lineal es inevitable para cualquier algoritmo.

**Qué hacemos:** en §2 del paper, definir el regret y agregar un párrafo explicando por qué con
adversario oblivious la definición usual es legítima, citando a CBDS y notando que las cotas de
EXP3 se prueban bajo el mismo supuesto. Es media página que eleva bastante el nivel del trabajo.

## B. Ideas que cambian el experimento

### B1. No reportar accuracy

**De dónde sale:** Almeida, Tabla 7.

El clasificador trivial "todo es ham" saca **86,95% de accuracy**. Cualquier número de accuracy en
este dataset es engañoso.

**Qué hacemos:** cambiar §6 del plan. Reportar **Spam Caught (SC%)**, **Blocked Hams (BH%)** y
**MCC**, que es lo que usa el paper del dataset. La figura F1 pasa de "tasa de error" a SC en
ventana móvil, o a las dos series SC y BH.

**Consecuencia teórica que hay que pensar:** con pérdida 0-1 y 13,4% de spam, el experto trivial
tiene pérdida de solo 0,134. Si el ataque rompe a los expertos léxicos, **el "mejor experto fijo en
retrospectiva" podría terminar siendo el trivial**, y entonces el regret de Hedge se mide contra una
vara ridícula. Es justamente la limitación de Hedge que queremos mostrar, pero hay que reportarlo
explícitamente: decir siempre *quién* fue el mejor experto en retrospectiva, no solo el número.

### B2. Baselines concretos para verificar la etapa 2

**De dónde sale:** Almeida, Tabla 7.

En vez de "accuracy razonable", la etapa 2 del plan tiene ahora números objetivo sobre el mismo
corpus:

| Nuestro experto | Referencia de Almeida | SC % esperado |
|---|---|---|
| Naive Bayes multinomial | MN TF NB + tok1 | ~52 |
| Regresión logística | (cercano a SVM lineal) | ~80 |
| Árbol de decisión | C4.5 + tok2 | ~75 |
| Experto trivial | Trivial rejection | 0 |

Si alguno se desvía mucho, hay un bug.

### B3. El experto estructural deja de ser un invento nuestro

**De dónde sale:** Almeida, Tabla 2.

Spam promedia 23,48 tokens y ham 13,18. **La longitud discrimina**, y está documentado en el paper
del corpus. Eso resuelve buena parte de la decisión abierta #2 de §9 del plan: el experto
estructural no es un ingrediente ad-hoc metido para que el experimento funcione, es una familia de
features respaldada por la caracterización publicada del dataset. Igual conviene declarar que lo
elegimos sabiendo que es inmune al ataque léxico.

### B4. Calibrar la fuerza del ataque en vez de inventar un número

**De dónde sale:** Lowd & Meek, §2.3 y resultados.

El plan decía "los ~50 tokens de mayor peso", que es arbitrario. El criterio de ellos es mejor:
calibrar el ataque hasta que **el modelo estático pierda la mitad de su capacidad de detección**
(de ~80% SC a ~40% SC), que es exactamente el punto de comparación de su paper.

También podemos adoptar su normalización de pesos (una lista cuyos pesos suman −1 pasa la mitad del
spam bloqueado) para parametrizar la intensidad de manera interpretable.

### B5. Nuestro ataque es el que ellos dejaron pendiente

**De dónde sale:** Lowd & Meek, trabajo futuro.

Ellos **agregan** palabras buenas. Nosotros agregamos palabras buenas **y ofuscamos** las malas
(leetspeak). En su sección final piden justamente eso: *"characterizing other spam attacks (e.g.,
word obfuscation)"*.

**Qué hacemos:** presentar el ataque como *passive good word attack* (con cita) **extendido con
ofuscación léxica**, y decir que es la combinación que ellos señalaron como pendiente. Deja de ser
un ataque inventado por nosotros.

### B6. Decisiones de preprocesamiento con respaldo

**De dónde sale:** Almeida, §3.1.

Sin stemming, sin stopwords, sin reducción de dimensionalidad, porque los mensajes son muy cortos.
Adoptamos el mismo criterio citándolos, en vez de justificarlo por nuestra cuenta.

### B7. La corrida adaptativa, si se hace, tiene una hipótesis

**De dónde sale:** CBDS, Tabla 1.

Si hacemos la corrida secundaria con adversario adaptativo de memoria acotada, la predicción teórica
es que el regret se degrada de `√T` a `T^{2/3}`. Eso la convierte en un experimento con hipótesis
falsable en lugar de un apéndice.

**Costo:** hay que definir memoria acotada, medir policy regret, y ajustar una ley de potencia al
regret empírico para estimar el exponente. Es media página más de formalismo en un paper que ya
está justo en espacio.

### B8. Si implementamos algo tipo EXP3, los parámetros ya están dados

**De dónde sale:** Auer et al., Figura 1 y Corolario 3.2.

No hay que inventar nada: `p_i(t) = (1−γ)·w_i/Σw + γ/K`, estimador `x̂_j = x_j/p_j`, actualización
`w_j ← w_j·exp(γ x̂_j/K)`, y `γ = min{1, √(K ln K / ((e−1)g))}`. Si no queremos fijar `g` de
antemano, EXP3.1 lo evita con épocas.

Y si en algún momento queremos cotas **con alta probabilidad** en vez de en esperanza (útil porque
vamos a correr 20 semillas y reportar bandas), EXP3.P da `O(√(K T ln(KT/δ)))` con probabilidad
`1−δ`.

### B9. Riesgo a tener en cuenta: hay poco spam

Con 747 spams en total y warm-up del 20%, quedan ~598 en el stream y solo **~300 sufren el ataque**
(los de la segunda mitad). El regret total se mueve en decenas de errores, no en miles. Conviene:

- Correr las 20 semillas sí o sí (ya está en el plan), porque la varianza va a ser alta.
- Considerar un warm-up más chico, o repetir el stream, si las curvas quedan demasiado ruidosas.

## C. Ideas menores, para la discusión

### C1. Prior no uniforme en Hedge

La cota de Freund & Schapire tiene `−ln w_1(i)` y no `ln N`: los pesos iniciales son un prior, y la
garantía es más fuerte contra los expertos a los que les diste más peso inicial. Como a priori uno
esperaría que el experto estructural sea el peor, darle peso inicial bajo empeora la garantía justo
contra el experto que termina siendo el bueno. Es un párrafo de discusión, no un experimento.

### C2. Reentrenar pesando lo reciente

Lowd & Meek encontraron que el reentrenamiento funciona mejor **duplicando los ejemplos recientes**.
Es una variante barata de nuestro competidor SGD-online y conecta con el decaimiento temporal de
Time Weight CF (slide 96 de la clase 3), si queremos tender un puente con otra clase.

### C3. No confundir las dos nociones de regret al citar EXP3

Advertencia explícita de CBDS: las cotas `O(√T)` de EXP3 "adaptativo" usan la definición vieja. Si
citamos a Auer et al. para EXP3, hay que aclarar en qué definición estamos. Las cotas originales de
Auer et al. son de *weak regret* contra adversario oblivious, así que están del lado seguro.

### C4. EXP4 necesita el experto uniforme

Detalle curioso: la demostración del Teorema 7.1 requiere que la familia de expertos incluya al
**experto uniforme**, el que reparte 1/K entre todas las acciones. Ojo que **no** es nuestro experto
trivial "todo ham": el uniforme es el que tira una moneda. Si en algún momento usamos EXP4, hay que
agregarlo.

---

# Parte 3 — Dónde se cita cada uno

| Paper | Sección del paper | Para qué |
|---|---|---|
| Freund & Schapire (1997) | §2 Marco, §3 Algoritmos, §5 Resultados | Hedge original, la cota fina, la distinción determinístico/randomizado |
| Auer, Cesa-Bianchi, Freund & Schapire (2002) | §3 Algoritmos, §6 Discusión | EXP3/EXP4, el factor `√K` del feedback parcial, el estimador insesgado, y por qué **no** aplica a nuestro caso (A3) |
| Lowd & Meek (2005) | §1 Introducción, §4 Setup | La tesis a discutir, la taxonomía pasivo/activo, la calibración del ataque |
| Almeida et al. (2011) | §4 Setup, §5 Resultados | El dataset, el preprocesamiento, las métricas, los baselines |
| Cesa-Bianchi, Dekel & Shamir (2013) | §2 Marco, §4 Setup, §6 Discusión | Policy regret, imposibilidad con adversario libre, tasas por tipo de adversario |

La bibliografía está completa: ya no falta conseguir nada. El libro de Cesa-Bianchi & Lugosi (2006)
alcanza con citarlo, no hace falta tenerlo.

---

# Resumen ejecutivo: qué cambia en el plan

1. **Hay que rediseñar el eje 2** (A3): el competidor EXP3 no se sostiene porque en clasificación
   binaria con etiqueta revelada el feedback bandit colapsa en información completa. Propuesta:
   reemplazarlo por observación parcial de la etiqueta con probabilidad ρ. La pregunta 2 pasa de
   "¿cuál es el precio de la información?" a "¿cuánta etiqueta hace falta?", y la predicción pasa de
   `√K` a `1/√ρ`.
2. **Nuevo resultado propio** (A1): implementar Hedge determinístico y randomizado, y mostrar que la
   cota de la slide 73 aplica solo al segundo.
3. **Nueva figura** (A2): F3 con las dos cotas, la de peor caso y la small-loss.
4. **Nueva introducción** (A4): el paper responde a la afirmación de Lowd & Meek.
5. **Nuevo párrafo teórico** (A5): policy regret justifica el adversario oblivious.
6. **Cambian las métricas** (B1): SC, BH y MCC en lugar de accuracy.
7. **Se resuelve la decisión abierta #2** (B3): el experto estructural tiene respaldo en la Tabla 2
   de Almeida.
8. **Queda por decidir** (B7): si hacemos la corrida adaptativa con su hipótesis `T^{2/3}`, a costa
   de media página.
