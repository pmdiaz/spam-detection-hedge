# Propuesta de trabajo final

**Tópicos Avanzados en Ciencia de Datos (MCD210)** · Pablo Díaz · Septiembre 2026
**Tema:** aprendizaje online con Hedge para detección de spam bajo drift adversarial

---

Tomo como punto de partida la tercera idea de la slide 79 —extender el caso de detección de spam a
un clasificador online con Hedge y compararlo contra un modelo estático— pero propongo separar dos
efectos que esa formulación deja mezclados. Un filtro que resiste a un spammer adaptativo puede
lograrlo por dos vías distintas: **combinando** clasificadores fijos con pesos que se reacomodan, o
**reentrenando** un único modelo con los datos que van llegando. Comparar Hedge contra un modelo
congelado mide las dos cosas juntas en un solo número. La pregunta central del trabajo es cuánto
aporta cada mecanismo por separado.

La pregunta tiene un interlocutor concreto en la literatura. Lowd & Meek (2005), el trabajo canónico
sobre evasión de filtros estadísticos, concluyen que *"the only remedy we know of is frequent
retraining"*. El experimento pone a prueba esa afirmación con tres competidores sobre la misma
secuencia de mensajes: un modelo estático, Hedge sobre cinco expertos congelados, y un modelo único
reentrenado online. El corpus es el SMS Spam Collection de Almeida et al. (2011), procesado como
stream, con un ataque adversarial —ofuscación léxica de los tokens más delatores, más inyección
acotada de vocabulario legítimo— que se activa a mitad de la secuencia. Las métricas son Spam
Caught, Blocked Hams y MCC; en un corpus con 13,4% de prevalencia positiva, la accuracy es
engañosa, ya que el clasificador trivial alcanza 86,95%.

Al preparar el marco formal apareció una observación que el trabajo desarrolla explícitamente: el
algoritmo de la slide 71 y la cota de la slide 73 no corresponden al mismo procedimiento. La slide
71 predice por voto pesado determinístico, mientras que la cota $\sqrt{2T\ln K}$ es la de Hedge,
donde la pérdida de cada ronda es la de la mezcla y se realiza muestreando un experto según los
pesos. La distinción no es de notación: contra un adversario que observa la predicción antes de
fijar la etiqueta, ningún algoritmo determinístico admite cota de regret sublineal, y la garantía
clásica de Weighted Majority es multiplicativa en lugar de aditiva. El trabajo implementa ambas
variantes y contrasta el regret empírico contra dos cotas, la de peor caso y la *small-loss* de
Freund & Schapire (1997), que depende de la pérdida del mejor experto y por eso reproduce el escalón
que produce el ataque.

La segunda pregunta es cuánta supervisión hace falta. El plan original incluía un competidor EXP3
para medir el precio del feedback parcial, pero lo descarté: como los expertos son funciones
determinísticas y el mensaje es observable, saber si la predicción jugada fue correcta revela la
etiqueta verdadera, y con ella la pérdida de todos los expertos. En clasificación binaria el
feedback bandit colapsa en información completa. El modelo realista de supervisión escasa en spam es
otro: la etiqueta llega solo cuando el usuario reporta el mensaje. Lo formalizo con una probabilidad
de observación $\rho$ y mido cómo se degrada el regret al reducirla, con la predicción teórica de un
crecimiento como $1/\sqrt{\rho}$.

El alcance está acotado deliberadamente para que entre en tres páginas. El adversario es *oblivious*
—fija la secuencia de antemano, sin personalizar el ataque por competidor—, lo que hace comparable
el regret entre algoritmos y evita tener que introducir *policy regret*; Cesa-Bianchi, Dekel &
Shamir (2013) muestran que contra adversarios adaptativos la definición usual de regret no es
adecuada y que sin memoria acotada el regret lineal es inevitable. La variante adaptativa queda
mencionada en la discusión con su degradación teórica a $T^{2/3}$, junto con las demás limitaciones:
pérdida 0-1 simétrica, expertos congelados y drift sintético. El diseño completo, los cinco papers
de referencia y el plan de implementación por etapas están documentados en el repositorio del
trabajo.
