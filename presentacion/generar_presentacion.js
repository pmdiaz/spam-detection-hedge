// Genera la presentacion "Combinar o reentrenar" en estilo editorial (20 diapositivas, 20 minutos).
//
// Una misma descripcion produce dos salidas:
//   - el .pptx, para abrir en PowerPoint o importar en Canva (texto y formas quedan editables);
//   - una vista previa HTML con las mismas posiciones, para revisar el diseño sin PowerPoint.
//
// Los graficos son las imagenes de visuales/ (las genera visuales.py desde los resultados).
//
// Uso:
//   SKILL_DIR=<skill pptx> NODE_PATH=<node_modules con pptxgenjs> \
//     node generar_presentacion.js salida.pptx vista_previa.html
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");
const { applyTheme } = require(process.env.SKILL_DIR + "/scripts/apply_theme.js");

const SALIDA_PPTX = process.argv[2];
const SALIDA_HTML = process.argv[3];
const VISUALES = path.join(__dirname, "visuales");

// ---------------------------------------------------------------------------
// Estilo: papel calido, titulares con serif, un color por entidad (los del paper).
// ---------------------------------------------------------------------------
const SERIF = "Georgia";
const SANS = "Arial";
const HEX = {
  papel: "F7F5F0", tinta: "1F2430", tinta2: "5A6274", tenue: "9AA1AE", regla: "D9D6CE",
  blanco: "FFFFFF", claroOscuro: "C8CEDA", reglaOscura: "3A4152", hedgeClaro: "AFCBEE",
  hedge: "2A78D6", estatico: "EB6834", sgd: "1BAF7A", estructural: "4A3AA7",
  otros: "008300", smallLoss: "E87BA4", deterministico: "E34948",
};
const THEME = {
  name: "Combinar o reentrenar",
  headFontFace: SERIF,
  bodyFontFace: SANS,
  colors: {
    dk1: HEX.tinta, lt1: HEX.blanco, dk2: HEX.tinta2, lt2: HEX.papel,
    accent1: HEX.hedge, accent2: HEX.estatico, accent3: HEX.sgd,
    accent4: HEX.estructural, accent5: HEX.otros, accent6: HEX.deterministico,
    hlink: HEX.hedge, folHlink: HEX.estructural,
  },
};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13,333 x 7,5 pulgadas
pres.theme = { headFontFace: SERIF, bodyFontFace: SANS };
pres.title = "Combinar o reentrenar";
pres.author = "Pablo Díaz y Ezequiel Martinez";
const FORMA = pres.ShapeType;

// Mezcla dos colores hex: sirve para "transparencias" que se ven igual en PowerPoint y en Canva.
function mezclar(color, fondo, proporcion) {
  const a = parseInt(color, 16), b = parseInt(fondo, 16);
  let resultado = 0;
  for (const corrimiento of [16, 8, 0]) {
    const ca = (a >> corrimiento) & 255, cb = (b >> corrimiento) & 255;
    resultado += Math.round(ca * proporcion + cb * (1 - proporcion)) << corrimiento;
  }
  return resultado.toString(16).padStart(6, "0").toUpperCase();
}

// ---------------------------------------------------------------------------
// Layouts. El titulo de las diapositivas de contenido es un placeholder.
// ---------------------------------------------------------------------------
const TITULO = { x: 0.6, y: 0.8, w: 11.4, h: 0.62, fontSize: 30 };
const NUMERO = { x: 12.13, y: 6.97, w: 0.6, h: 0.3, fontSize: 10 };

pres.defineSlideMaster({
  title: "CONTENIDO",
  background: { color: HEX.papel },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: TITULO.x, y: TITULO.y, w: TITULO.w, h: TITULO.h,
      fontSize: TITULO.fontSize, fontFace: SERIF, bold: false, color: HEX.tinta, valign: "top", margin: 0 }, text: "" } },
    { line: { x: 0.6, y: 6.88, w: 12.13, h: 0, line: { color: HEX.regla, width: 0.75 } } },
  ],
  slideNumber: { x: NUMERO.x, y: NUMERO.y, w: NUMERO.w, h: NUMERO.h, fontSize: NUMERO.fontSize,
    fontFace: SANS, color: HEX.tenue, align: "right" },
});

pres.defineSlideMaster({
  title: "OSCURA",
  background: { color: HEX.tinta },
  objects: [],
});

// ---------------------------------------------------------------------------
// Primitivas: cada una dibuja en el .pptx y registra lo mismo para la vista previa.
// ---------------------------------------------------------------------------
const vista = [];   // una entrada por diapositiva: { fondo, numero, elementos }
let actual = null;

function nuevaDiapositiva(layout, seccion) {
  const slide = pres.addSlide({ masterName: layout, sectionTitle: seccion });
  actual = { fondo: layout === "OSCURA" ? HEX.tinta : HEX.papel, numero: vista.length + 1, contenido: layout === "CONTENIDO", elementos: [] };
  vista.push(actual);
  return slide;
}

// Normaliza el contenido de un texto a una lista de corridas { text, options }.
function corridas(contenido) {
  if (typeof contenido === "string") return [{ text: contenido, options: {} }];
  return contenido;
}

function texto(slide, contenido, o) {
  const opciones = Object.assign({ fontFace: SANS, fontSize: 16, color: HEX.tinta, margin: 0, valign: "top",
    isTextBox: true, lineSpacingMultiple: 1.0 }, o);
  slide.addText(contenido, opciones);
  actual.elementos.push({ tipo: "texto", corridas: corridas(contenido), o: opciones });
}

function forma(slide, tipo, o) {
  const opciones = { x: o.x, y: o.y, w: o.w, h: o.h, objectName: o.nombre,
    fill: o.relleno ? { color: o.relleno } : { type: "none" },
    line: o.borde ? { color: o.borde, width: o.grosor || 1 } : { type: "none" } };
  if (tipo === "rect" && o.radio) opciones.rectRadius = o.radio;
  const formaPptx = tipo === "ellipse" ? FORMA.ellipse : (o.radio ? FORMA.roundRect : FORMA.rect);
  slide.addShape(formaPptx, opciones);
  actual.elementos.push({ tipo, o });
}

function circulo(slide, x, y, d, relleno, nombre, borde) {
  forma(slide, "ellipse", { x, y, w: d, h: d, relleno, borde, grosor: 1.25, nombre });
}

function regla(slide, x, y, w, h, color) {
  slide.addShape(FORMA.line, { x, y, w, h, line: { color: color || HEX.regla, width: 0.75 } });
  actual.elementos.push({ tipo: "linea", o: { x, y, w, h, color: color || HEX.regla } });
}

function tamanoPng(archivo) {
  const datos = fs.readFileSync(archivo);
  return { ancho: datos.readUInt32BE(16), alto: datos.readUInt32BE(20) };
}

// Ubica una imagen dentro de una caja respetando su proporcion; la alinea arriba a la izquierda.
function imagen(slide, nombre, x, y, wMax, hMax, descripcion) {
  const archivo = path.join(VISUALES, nombre);
  const { ancho, alto } = tamanoPng(archivo);
  let w = wMax, h = wMax * alto / ancho;
  if (h > hMax) { h = hMax; w = hMax * ancho / alto; }
  slide.addImage({ path: archivo, x, y, w, h, altText: descripcion });
  actual.elementos.push({ tipo: "imagen", archivo, o: { x, y, w, h } });
  return { w, h };
}

function titulo(slide, contenido) {
  slide.addText(contenido, { placeholder: "title" });
  actual.elementos.push({ tipo: "texto", corridas: corridas(contenido),
    o: Object.assign({ fontFace: SERIF, color: HEX.tinta, valign: "top", lineSpacingMultiple: 1.0 }, TITULO) });
}

// Encabezado de contenido: antetitulo, titular, bajada y el indicador de hallazgos.
function encabezado(slide, antetitulo, titular, bajada, hallazgo) {
  texto(slide, antetitulo, { x: 0.6, y: 0.45, w: 8, h: 0.25, fontSize: 11, bold: true, color: HEX.tinta2, charSpacing: 2 });
  titulo(slide, titular);
  if (bajada) texto(slide, bajada, { x: 0.6, y: 1.43, w: 11.4, h: 0.35, fontSize: 15, color: HEX.tinta2 });
  // Motivo de toda la charla: cuatro hallazgos, el actual relleno.
  texto(slide, "HALLAZGOS", { x: 10.1, y: 0.47, w: 1.7, h: 0.22, fontSize: 9, bold: true, color: HEX.tenue,
    align: "right", charSpacing: 2 });
  for (let i = 1; i <= 4; i++) {
    const x = 11.92 + (i - 1) * 0.22;
    if (i === hallazgo) circulo(slide, x, 0.5, 0.15, HEX.tinta, "hallazgo " + i + " (actual)");
    else circulo(slide, x, 0.5, 0.15, null, "hallazgo " + i, HEX.tenue);
  }
}

function fuente(slide, contenido) {
  texto(slide, contenido, { x: 0.6, y: 6.97, w: 11.2, h: 0.3, fontSize: 10, color: HEX.tenue });
}

// Cifra grande con su explicacion debajo.
function cifra(slide, valor, color, explicacion, x, y, w, tamano) {
  texto(slide, valor, { x, y, w, h: (tamano || 54) / 60, fontSize: tamano || 54, bold: true, color });
  texto(slide, explicacion, { x, y: y + (tamano || 54) / 60 + 0.08, w, h: 0.75, fontSize: 15, color: HEX.tinta });
}

// Fila de leyenda: punto de color, nombre en negrita y descripcion.
function filaPunto(slide, color, nombre, descripcion, x, y, w) {
  circulo(slide, x, y + 0.06, 0.24, color, "punto " + nombre);
  texto(slide, nombre, { x: x + 0.42, y, w: w - 0.42, h: 0.32, fontSize: 16, bold: true });
  if (descripcion) texto(slide, descripcion, { x: x + 0.42, y: y + 0.36, w: w - 0.42, h: 0.5, fontSize: 13, color: HEX.tinta2 });
}

function llamada(slide, numero, contenido, x, y, w) {
  circulo(slide, x, y, 0.42, HEX.tinta, "llamada " + numero);
  texto(slide, numero, { x, y, w: 0.42, h: 0.42, fontSize: 15, bold: true, color: HEX.blanco, align: "center", valign: "middle" });
  texto(slide, contenido, { x: x + 0.62, y: y - 0.02, w: w - 0.62, h: 1.3, fontSize: 15 });
}

const FUENTE_SEMILLAS = "Media de 20 permutaciones (semillas) del SMS Spam Collection. Ataque desde la mitad del stream.";

// ===========================================================================
// 1 · El problema (orador A)
// ===========================================================================
const S1 = "1 · El problema";
pres.addSection({ title: S1 });

// --- 1. Portada -------------------------------------------------------------
{
  const s = nuevaDiapositiva("OSCURA", S1);
  texto(s, "TÓPICOS AVANZADOS EN CIENCIA DE DATOS · MCD210 · UDESA", { x: 0.8, y: 1.15, w: 8, h: 0.3,
    fontSize: 11, bold: true, color: HEX.tenue, charSpacing: 2 });
  texto(s, "Combinar\no reentrenar", { x: 0.8, y: 1.9, w: 7.4, h: 2.3, fontSize: 64, fontFace: SERIF,
    color: HEX.blanco, lineSpacingMultiple: 0.92 });
  texto(s, "Hedge contra reentrenamiento online en un filtro de spam bajo ataque", { x: 0.8, y: 4.45, w: 6.4, h: 0.85,
    fontSize: 20, color: HEX.claroOscuro });
  texto(s, "Pablo Díaz · Ezequiel Martinez", { x: 0.8, y: 5.85, w: 7, h: 0.4, fontSize: 16, bold: true, color: HEX.blanco });
  // Las palabras que el ataque altera, cada vez mas tenues.
  const palabras = ["reeply", "wiin", "weeekly", "cuup", "stoop", "seervice"];
  palabras.forEach((palabra, i) => {
    texto(s, palabra, { x: 8.7 + (i % 2) * 0.85, y: 0.95 + i * 0.86, w: 3.6, h: 0.75, fontSize: 40, fontFace: SERIF,
      italic: true, color: mezclar(HEX.estatico, HEX.tinta, 1 - i * 0.14) });
  });
  texto(s, "lol", { x: 9.55, y: 0.95 + 6 * 0.86, w: 2, h: 0.75, fontSize: 40, fontFace: SERIF, italic: true,
    color: mezclar(HEX.hedge, HEX.tinta, 0.6) });
  s.addNotes("A · 0:30. Presentarse. Una frase de entrada: cuando el spammer se adapta al filtro, ¿conviene combinar modelos que ya tenemos o reentrenar uno? Las palabras de la derecha son reales: así queda un spam después de nuestro ataque.");
}

// --- 2. El ataque -----------------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S1);
  encabezado(s, "EL PROBLEMA", "Un spammer que aprende a esquivar el filtro",
    "Un SMS real del corpus, atacado por nuestro código: crece una sola palabra.", 0);
  imagen(s, "01_ataque_telefonos.png", 0.4, 2.2, 8.85, 4.6,
    "Dos teléfonos con el mismo SMS de spam, antes y después del ataque. En el atacado, siete palabras tienen una letra duplicada (reeply, wiin, weeekly) y se agrega la palabra lol.");
  texto(s, "SPAM QUE ATRAPA EL FILTRO ESTÁTICO", { x: 9.45, y: 2.15, w: 3.3, h: 0.25, fontSize: 10, bold: true,
    color: HEX.tinta2, charSpacing: 1 });
  texto(s, "85%", { x: 9.45, y: 2.5, w: 3.3, h: 0.9, fontSize: 54, bold: true, color: HEX.tenue });
  texto(s, "sin ataque", { x: 9.45, y: 3.4, w: 3.3, h: 0.3, fontSize: 14, color: HEX.tinta2 });
  texto(s, "42%", { x: 9.45, y: 3.85, w: 3.3, h: 0.9, fontSize: 54, bold: true, color: HEX.estatico });
  texto(s, "con ataque", { x: 9.45, y: 4.75, w: 3.3, h: 0.3, fontSize: 14, color: HEX.tinta2 });
  regla(s, 9.45, 5.3, 3.28, 0);
  circulo(s, 9.45, 5.5, 0.18, HEX.estatico, "leyenda alterada");
  texto(s, "vocal duplicada en las palabras que más delatan spam", { x: 9.75, y: 5.44, w: 3.0, h: 0.5, fontSize: 12, color: HEX.tinta2 });
  circulo(s, 9.45, 6.08, 0.18, HEX.hedge, "leyenda agregada");
  texto(s, "palabra típica de mensajes legítimos", { x: 9.75, y: 6.02, w: 3.0, h: 0.5, fontSize: 12, color: HEX.tinta2 });
  fuente(s, "Ataque «good word» de Lowd & Meek (2005) más ofuscación de las 800 palabras más delatoras. " + FUENTE_SEMILLAS.split(".")[0] + ".");
  s.addNotes("A · 1:15. Leer el SMS original y después señalar las palabras en naranja: reply pasa a reeply, win a wiin, stop a stoop. La azul, lol, es una palabra típica de mensajes legítimos. El filtro estático pasa de atrapar el 85% del spam al 42%. El mensaje crece una sola palabra: no se lo puede detectar por el largo.");
}

// --- 3. Dos formas de defenderse --------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S1);
  encabezado(s, "EL PROBLEMA", "Dos formas de defenderse", null, 0);
  const columnas = [
    { x: 0.6, color: HEX.hedge, nombre: "Combinar", sub: "Hedge sobre 5 expertos congelados",
      cuerpo: "Cinco clasificadores entrenados una vez. Hedge no los toca: reparte la confianza entre ellos y la mueve hacia el que acierta.",
      cifra: "Aprende 5 pesos" },
    { x: 6.95, color: HEX.sgd, nombre: "Reentrenar", sub: "SGD online, un solo modelo",
      cuerpo: "Un modelo que se actualiza con cada mensaje etiquetado. Puede aprender palabras que nunca vio, como «wiin».",
      cifra: "Aprende un peso por palabra" },
  ];
  columnas.forEach((c, i) => {
    if (i === 0) {
      [HEX.estatico, HEX.otros, HEX.otros, HEX.otros, HEX.estructural].forEach((color, j) => {
        circulo(s, c.x + j * 0.5, 1.95, 0.36, color, "experto " + (j + 1));
      });
    } else {
      // Muchos pesos chicos: uno por palabra del vocabulario.
      for (let fila = 0; fila < 3; fila++) {
        for (let col = 0; col < 22; col++) {
          circulo(s, c.x + col * 0.2, 1.95 + fila * 0.14, 0.08, HEX.sgd, "peso " + (fila * 22 + col + 1));
        }
      }
    }
    texto(s, c.nombre, { x: c.x, y: 2.55, w: 5.6, h: 0.6, fontSize: 32, fontFace: SERIF, color: c.color });
    texto(s, c.sub, { x: c.x, y: 3.17, w: 5.6, h: 0.3, fontSize: 14, color: HEX.tinta2 });
    texto(s, c.cuerpo, { x: c.x, y: 3.6, w: 5.6, h: 0.95, fontSize: 16 });
    texto(s, c.cifra, { x: c.x, y: 4.6, w: 5.6, h: 0.35, fontSize: 16, bold: true, color: c.color });
  });
  regla(s, 6.65, 2.0, 0, 2.95);
  regla(s, 0.6, 5.3, 12.13, 0);
  texto(s, "“The only remedy we know of is frequent retraining.”", { x: 0.6, y: 5.5, w: 12.1, h: 0.55,
    fontSize: 26, fontFace: SERIF, italic: true });
  texto(s, "Lowd & Meek (2005), sobre ataques a filtros de spam. Es la tesis que ponemos a prueba.", {
    x: 0.6, y: 6.15, w: 12.1, h: 0.3, fontSize: 13, color: HEX.tinta2 });
  fuente(s, "Expertos: Naive Bayes, regresión logística, árbol, reglas y uno estructural que mira el formato.");
  s.addNotes("A · 1:00. Las dos defensas. Combinar: cinco modelos congelados, Hedge solo decide a cuál creerle; aprende cinco números. Reentrenar: un modelo que aprende de cada etiqueta; tiene un peso por palabra, por eso puede aprender «wiin». La cita de Lowd y Meek es la tesis que ponemos a prueba.");
}

// --- 4. Dos preguntas -------------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S1);
  encabezado(s, "EL PROBLEMA", "Dos preguntas", null, 0);
  const preguntas = [
    ["1", "¿Cuánto se recupera combinando expertos congelados, sin reentrenar nada?", "Lo responde el hallazgo 1"],
    ["2", "¿Cuánta etiqueta hace falta? En la práctica, el usuario reporta pocos mensajes.", "Lo responde el hallazgo 2"],
  ];
  preguntas.forEach(([n, p, quien], i) => {
    const x = 0.6 + i * 6.35;
    texto(s, n, { x, y: 1.6, w: 1.5, h: 1.85, fontSize: 110, fontFace: SERIF, color: HEX.hedge });
    texto(s, p, { x, y: 3.5, w: 5.7, h: 1.25, fontSize: 24, fontFace: SERIF });
    texto(s, quien, { x, y: 4.85, w: 5.7, h: 0.3, fontSize: 13, bold: true, color: HEX.tinta2 });
  });
  regla(s, 0.6, 5.45, 12.13, 0);
  texto(s, "Y dos precisiones sobre la teoría vista en clase: qué algoritmo garantiza la cota, y para qué tasa de aprendizaje vale (hallazgo 3). Al final, lecciones de método (hallazgo 4).", {
    x: 0.6, y: 5.65, w: 12.1, h: 0.75, fontSize: 16, color: HEX.tinta2 });
  s.addNotes("A · 0:40. Las dos preguntas ordenan la charla: los hallazgos 1 y 2 las responden. Anticipar que el hallazgo 3 son dos precisiones sobre la teoría, y el 4 lecciones de método. Los puntos de arriba a la derecha marcan en qué hallazgo estamos.");
}

// --- 5. Como lo medimos -----------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S1);
  encabezado(s, "DISEÑO", "Cómo lo medimos", "Cada mensaje del stream es una ronda: predecir, ver la etiqueta, actualizar.", 0);
  // El corpus como una barra, a escala.
  const total = 5574, warmup = 1114, mitad = 2230;
  const x0 = 0.6, ancho = 12.13, yBarra = 2.85, alto = 0.55;
  const tramos = [
    { n: warmup, relleno: HEX.regla, rotulo: "WARM-UP", color: HEX.tinta, cifra: "1.114 SMS",
      desc: "Se entrenan los modelos; los 5 expertos quedan congelados." },
    { n: mitad, relleno: "ECE9E2", rotulo: "STREAM SIN ATAQUE", color: HEX.tinta, cifra: "2.230 SMS",
      desc: "Los tres competidores ven la misma secuencia de mensajes." },
    { n: mitad, relleno: HEX.tinta, rotulo: "STREAM CON ATAQUE", color: HEX.blanco, cifra: "2.230 SMS",
      desc: "Todo spam llega ofuscado. Acá se mide quién se recupera." },
  ];
  let x = x0;
  tramos.forEach((t, i) => {
    const w = ancho * t.n / total;
    forma(s, "rect", { x, y: yBarra, w, h: alto, relleno: t.relleno, nombre: "tramo " + (i + 1) });
    texto(s, t.rotulo, { x: x + 0.15, y: yBarra, w: w - 0.3, h: alto, fontSize: 11, bold: true, color: t.color,
      valign: "middle", charSpacing: 1 });
    texto(s, t.cifra, { x, y: yBarra - 0.55, w, h: 0.4, fontSize: 20, bold: true });
    texto(s, t.desc, { x, y: yBarra + alto + 0.15, w: w - 0.25, h: 0.75, fontSize: 13, color: HEX.tinta2 });
    x += w;
  });
  regla(s, 0.6, 4.55, 12.13, 0);
  texto(s, "QUÉ MEDIMOS", { x: 0.6, y: 4.75, w: 6, h: 0.25, fontSize: 10, bold: true, color: HEX.tinta2, charSpacing: 1 });
  texto(s, [
    { text: "Spam atrapado (SC): ", options: { bold: true } },
    { text: "qué parte del spam se detecta", options: { breakLine: true } },
    { text: "Legítimo bloqueado (BH): ", options: { bold: true } },
    { text: "qué parte del correo bueno se pierde", options: { breakLine: true } },
    { text: "MCC: ", options: { bold: true } },
    { text: "un resumen robusto al desbalance", options: { breakLine: true } },
    { text: "Errores en la mitad atacada: ", options: { bold: true } },
    { text: "la cifra que comparamos", options: {} },
  ], { x: 0.6, y: 5.1, w: 7.4, h: 1.6, fontSize: 15, lineSpacingMultiple: 1.15 });
  cifra(s, "87%", HEX.tinta, "de acierto sin marcar nada como spam: por eso no usamos accuracy.", 8.9, 4.75, 3.8);
  fuente(s, "SMS Spam Collection (Almeida et al., 2011): 5.574 SMS, 13,4% spam. 20 permutaciones del orden: media ± desvío.");
  s.addNotes("A · 1:20. Recorrer la barra de izquierda a derecha: está a escala. Warm-up del 20% para entrenar; después 4.460 rondas de predecir, ver la etiqueta y actualizar; el ataque arranca en la mitad. Los tres competidores ven exactamente la misma secuencia. Sobre métricas: con 13% de spam, no marcar nada acierta el 87%.");
}

// --- 6. Hedge en un minuto --------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S1);
  encabezado(s, "MÉTODO", "Hedge en un minuto", null, 0);
  regla(s, 0.6, 1.75, 6.5, 0);
  texto(s, [
    { text: "peso", options: {} },
    { text: "i", options: { subscript: true } },
    { text: "  ←  peso", options: {} },
    { text: "i", options: { subscript: true } },
    { text: " · e", options: {} },
    { text: "−η · error", options: { superscript: true } },
  ], { x: 0.6, y: 1.95, w: 6.5, h: 0.75, fontSize: 32, fontFace: SERIF });
  regla(s, 0.6, 2.9, 6.5, 0);
  const pasos = [
    "Los cinco expertos arrancan con el mismo peso: 1/5.",
    "Cada error achica el peso del experto que se equivocó.",
    "En cada mensaje se sortea un experto según los pesos.",
  ];
  pasos.forEach((p, i) => {
    texto(s, String(i + 1), { x: 0.6, y: 3.15 + i * 0.6, w: 0.4, h: 0.45, fontSize: 22, fontFace: SERIF, color: HEX.hedge });
    texto(s, p, { x: 1.1, y: 3.2 + i * 0.6, w: 6.0, h: 0.45, fontSize: 16 });
  });
  texto(s, [
    { text: "Regret: ", options: { bold: true } },
    { text: "cuántos errores de más comete Hedge frente al mejor experto fijo. La teoría garantiza que crece como √T, no como T.", options: {} },
  ], { x: 0.6, y: 5.25, w: 6.5, h: 0.9, fontSize: 15, color: HEX.tinta2 });
  texto(s, "LOS CINCO EXPERTOS", { x: 7.95, y: 1.85, w: 4.8, h: 0.25, fontSize: 10, bold: true, color: HEX.tinta2, charSpacing: 1 });
  const expertos = [
    [HEX.estatico, "Naive Bayes", "léxico; también es el modelo estático"],
    [HEX.otros, "Regresión logística", "léxica"],
    [HEX.otros, "Árbol de decisión", "léxico"],
    [HEX.otros, "Reglas", "léxico"],
    [HEX.estructural, "Estructural", "9 rasgos de formato: largo, dígitos, teléfonos, £, mayúsculas…"],
  ];
  expertos.forEach(([color, nombre, desc], i) => filaPunto(s, color, nombre, desc, 7.95, 2.3 + i * 0.85, 4.8));
  fuente(s, "Freund & Schapire (1997). Los colores de los expertos se mantienen en todos los gráficos.");
  s.addNotes("A · 1:15. La regla es una línea: cada error multiplica el peso del experto por e a la menos eta. Hedge sortea a qué experto creerle según los pesos. Presentar a los cinco expertos con sus colores: cuatro miran palabras y uno, el estructural en violeta, mira formato. Regret: errores de más contra el mejor experto fijo.");
}

// ===========================================================================
// 2 · Hallazgos
// ===========================================================================
const S2 = "2 · Hallazgos";
pres.addSection({ title: S2 });

// --- 7. Hallazgo 1: la brecha -----------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 1 · ¿CUÁNTO SE RECUPERA SIN REENTRENAR?", "Combinar recupera casi la mitad, sin reentrenar",
    "Errores en la mitad atacada: Hedge recorre el 46% del camino entre no adaptarse y reentrenar.", 1);
  imagen(s, "02_brecha_hallazgo1.png", 0.75, 2.2, 11.8, 3.85,
    "Recta de errores en la mitad atacada: el estático comete 190, Hedge 133 y SGD online 73. Hedge cubre el 46% de la brecha.");
  regla(s, 0.6, 6.1, 12.13, 0);
  texto(s, "46% ± 13 entre semillas. Reentrenar sigue siendo lo mejor con todas las etiquetas, como dicen Lowd & Meek; combinar hace casi la mitad del trabajo sin tocar ningún modelo.", {
    x: 0.6, y: 6.2, w: 12.1, h: 0.6, fontSize: 14, color: HEX.tinta2 });
  fuente(s, FUENTE_SEMILLAS);
  s.addNotes("A · 1:00. Respuesta a la pregunta 1. Con ataque, el estático comete 190 errores, Hedge 133 y SGD 73. Hedge recorre el 46% de esa distancia sin reentrenar nada. Reentrenar gana, pero combinar hace casi la mitad del trabajo.");
}

// --- 8. En mensajes ---------------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 1", "De 305 spams atacados, Hedge atrapa 52 más",
    "Cada punto es un spam de la mitad atacada; en color, los que el filtro detecta.", 1);
  imagen(s, "03_puntos_spam_atacado.png", 0.6, 2.0, 12.1, 4.75,
    "Tres grillas de 305 puntos. El estático atrapa 128 (42%), Hedge 180 (59%) y SGD online 252 (83%).");
  fuente(s, FUENTE_SEMILLAS);
  s.addNotes("A · 0:45. La misma comparación en mensajes concretos. De los 305 spams que llegan atacados, el estático atrapa 128, Hedge 180 y SGD 252. Hedge atrapa 52 más que el estático; SGD, 72 más que Hedge.");
}

// --- 9 a 11. La figura del paper, en tres pasos ------------------------------
const pasosFigura = [
  ["Con el ataque, el estático cae y no se recupera",
   "Spam atrapado por el estático: ~85% antes del ataque, cae a 43% y no se recupera.",
   "A · 0:30. Primero solo el estático: atrapa ~85% del spam; con el ataque cae a ~43% y se queda ahí."],
  ["Hedge cae con él, pero se recupera a medias",
   "Se suma Hedge: cae junto con el estático y se recupera hasta 62%.",
   "A · 0:30. Hedge cae con el estático, porque al principio le cree a Naive Bayes, y después se recupera hasta ~60%."],
  ["Reentrenar aprende las palabras nuevas",
   "Se suma SGD online: cae menos y vuelve a 89%, casi el nivel previo al ataque.",
   "A · 0:30. SGD también cae, menos, y vuelve casi al nivel previo: aprende «wiin» como palabra de spam. Hedge no puede, porque sus expertos están congelados."],
];
pasosFigura.forEach(([titular, descripcion, nota], i) => {
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 1", titular, "Spam atrapado en una ventana móvil de 300 mensajes.", 1);
  imagen(s, "04_spam_atrapado_paso" + (i + 1) + ".png", 0.45, 1.95, 11.6, 4.85,
    descripcion);
  fuente(s, FUENTE_SEMILLAS + " Es la figura 1 del paper.");
  s.addNotes(nota);
});

// --- 12. Por que funciona ---------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 1", "Por qué funciona: la apuesta ya estaba cubierta",
    "Peso de cada experto en Hedge a lo largo del stream.", 1);
  imagen(s, "05_pesos_hedge.png", 0.45, 2.0, 8.75, 4.7,
    "Área apilada con el peso de cada experto. Al llegar el ataque el peso está repartido en tercios; después migra al estructural, que termina con 0,96.");
  llamada(s, "1", "Al llegar el ataque, el peso estaba repartido en tercios: Naive Bayes 0,36, estructural 0,33, el resto 0,31.", 9.45, 2.2, 3.3);
  llamada(s, "2", "El ataque rompe a los léxicos y el peso migra al estructural en unos 1.000 mensajes: termina con 0,96.", 9.45, 3.75, 3.3);
  regla(s, 9.45, 5.3, 3.28, 0);
  texto(s, "El estructural mira formato, no palabras: este ataque no lo toca.", { x: 9.45, y: 5.45, w: 3.3, h: 0.8,
    fontSize: 15, bold: true, color: HEX.estructural });
  fuente(s, FUENTE_SEMILLAS);
  s.addNotes("A · 1:15 (y pasa a B). El porqué. Hedge no había apostado todo al mejor del momento: al llegar el ataque tenía el peso en tercios. Cuando el ataque rompe a Naive Bayes, el peso migra al estructural, que mira formato y no palabras. Pase: «Esto con todas las etiquetas. Ezequiel muestra qué pasa cuando escasean.»");
}

// --- 13. Hallazgo 2: el cruce ------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 2 · ¿CUÁNTA ETIQUETA HACE FALTA?", "Con pocas etiquetas, combinar le gana a reentrenar",
    "Errores en la mitad atacada, según cuántos mensajes reporta el usuario.", 2);
  imagen(s, "06_cruce_etiquetas.png", 0.45, 1.95, 7.6, 4.85,
    "Errores según la fracción de mensajes etiquetados. Con todas las etiquetas SGD comete 73 y Hedge 133; con 1 de cada 20, SGD 210 y Hedge 189, frente a 190 del estático.");
  cifra(s, "15 de 20", HEX.hedge, "semillas en las que gana Hedge cuando el usuario reporta 1 de cada 20 mensajes", 8.45, 2.1, 4.3);
  cifra(s, "210 > 190", HEX.sgd, "errores: con tan pocas etiquetas, SGD termina peor que no adaptarse", 8.45, 4.0, 4.3, 44);
  texto(s, "Con 1 de cada 5 o más, reentrenar gana en al menos 18 de 20 semillas.", { x: 8.45, y: 5.95, w: 4.3, h: 0.6,
    fontSize: 13, color: HEX.tinta2 });
  fuente(s, "Barrido de ρ, la probabilidad de ver la etiqueta. Hedge usa el estimador ℓ/ρ con η_ρ = √ρ · η_T. " + FUENTE_SEMILLAS.split(".")[0] + ".");
  s.addNotes("B · 1:30. Respuesta a la pregunta 2. Con todas las etiquetas, reentrenar gana claro: 73 contra 133. A medida que el usuario reporta menos, SGD se degrada mucho más rápido. Las curvas se cruzan entre 1 de cada 5 y 1 de cada 20: ahí Hedge gana en 15 de 20 semillas, y SGD termina peor que no adaptarse.");
}

// --- 14. No es un artefacto --------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 2", "No es un artefacto de cómo se pondera",
    "Errores en la mitad atacada con 1 de cada 20 mensajes etiquetado.", 2);
  imagen(s, "07_reponderacion_sgd.png", 0.45, 2.0, 7.6, 4.7,
    "SGD online sin reponderar comete 210 errores; reponderado por 1 sobre raíz de rho, 240; por 1 sobre rho, 323. Hedge comete 189.");
  texto(s, "¿Y si SGD compensa las etiquetas que faltan pesando más cada ejemplo, como hace Hedge?", {
    x: 8.45, y: 2.1, w: 4.3, h: 1.2, fontSize: 20, fontFace: SERIF });
  texto(s, "Empeora: con pocos ejemplos, pasos más grandes sobreajustan a cada uno.", { x: 8.45, y: 3.4, w: 4.3, h: 0.6,
    fontSize: 15, color: HEX.tinta2 });
  regla(s, 8.45, 4.3, 4.28, 0);
  texto(s, "Hedge aprende 5 pesos. Reentrenar, uno por cada palabra nueva.", { x: 8.45, y: 4.5, w: 4.3, h: 1.15,
    fontSize: 22, fontFace: SERIF, color: HEX.hedge });
  texto(s, "Lo que sí paga Hedge es varianza: con ρ = 0,05 cada observación pesa ≈ 4,5 veces más.", { x: 8.45, y: 5.8, w: 4.3, h: 0.6,
    fontSize: 13, color: HEX.tinta2 });
  fuente(s, FUENTE_SEMILLAS);
  s.addNotes("B · 1:15. Un revisor nos objetó que SGD perdía por no reponderar como Hedge. Lo probamos: reponderar lo empeora, de 210 a 240 o 323 errores. La razón es de conteo: Hedge aprende 5 pesos; reentrenar necesita un peso por cada palabra nueva. Lo que sí sufre Hedge es la varianza del estimador.");
}

// --- 15. Hallazgo 3: deterministico contra randomizado -----------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 3 · LA TEORÍA, CON PRECISIÓN", "La cota de la teoría no es la del voto pesado", null, 3);
  texto(s, "En clase se presentan juntos:", { x: 0.6, y: 1.95, w: 5, h: 0.3, fontSize: 15, color: HEX.tinta2 });
  filaPunto(s, HEX.deterministico, "Voto pesado determinístico", "predice lo que dice la mayoría ponderada", 0.6, 2.45, 5.0);
  filaPunto(s, HEX.hedge, "Hedge randomizado", "sortea un experto según los pesos: para este vale la cota", 0.6, 3.35, 5.0);
  regla(s, 0.6, 4.35, 5.0, 0);
  texto(s, "Si el jugador es predecible, un adversario lo simula y etiqueta lo contrario: lo hace errar siempre.", {
    x: 0.6, y: 4.55, w: 5.0, h: 1.1, fontSize: 20, fontFace: SERIF });
  texto(s, "En nuestro stream de spam, que es benigno, el determinístico incluso anda mejor (regret −2,6).", {
    x: 0.6, y: 5.85, w: 5.0, h: 0.6, fontSize: 13, color: HEX.tinta2 });
  imagen(s, "08_duelo_deterministico.png", 5.95, 1.9, 6.85, 4.9,
    "Regret frente a un adversario que simula al jugador. El voto pesado determinístico llega a 2.000, T sobre 2; Hedge randomizado queda en 14, bajo su cota de 37.");
  fuente(s, "Secuencia sintética de 4.000 rondas con 2 expertos. Slides 71 y 73 de la clase 2.");
  s.addNotes("B · 1:30. Primera precisión sobre la teoría. Las slides 71 y 73 presentan juntos el voto pesado y la cota, pero la cota es del Hedge randomizado. Construimos un adversario que simula al determinístico y le etiqueta lo contrario: su regret crece lineal, T/2. El randomizado queda en 14, bajo su cota de 37. En el stream real el determinístico anda mejor: la diferencia es de peor caso.");
}

// --- 16. Cada cota con su eta ------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 3", "Cada cota vale para su tasa de aprendizaje",
    "Regret de Hedge en el stream atacado, con dos formas de elegir η.", 3);
  imagen(s, "09_cotas_por_eta.png", 0.45, 1.95, 7.6, 4.85,
    "Regret de Hedge con eta de peor caso: 31, bajo su cota de 60. Con eta small-loss: 15, bajo su cota de 25.");
  texto(s, "Las dos cotas se cumplen en las 20 semillas, cada una con su propio η.", { x: 8.45, y: 2.1, w: 4.3, h: 0.95,
    fontSize: 20, fontFace: SERIF });
  filaPunto(s, HEX.hedge, "η de peor caso", "sintonizado por T: regret 31, cota 60", 8.45, 3.3, 4.3);
  filaPunto(s, HEX.smallLoss, "η small-loss", "sintonizado por la pérdida del mejor: regret 15, cota 25", 8.45, 4.2, 4.3);
  regla(s, 8.45, 5.15, 4.28, 0);
  texto(s, "La small-loss es mejor algoritmo, pero necesita saber de antemano cuántos errores comete el mejor experto: información de oráculo.", {
    x: 8.45, y: 5.3, w: 4.3, h: 1.0, fontSize: 14, color: HEX.tinta2 });
  fuente(s, "La √(2T ln K) de la clase vale 120: correcta, pero el doble de lo necesario. " + FUENTE_SEMILLAS.split(".")[0] + ".");
  s.addNotes("B · 1:15. Segunda precisión. Hay dos cotas y cada una vale para su propia tasa de aprendizaje. Las dos se cumplen en las 20 semillas. La small-loss da la mitad de regret, pero requiere saber cuántos errores comete el mejor experto, algo que bajo ataque no sabemos. Notar cómo esa cota cambia de pendiente con el ataque.");
}

// --- 17. Hallazgo 4: lecciones de metodo -------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S2);
  encabezado(s, "HALLAZGO 4 · LECCIONES DE MÉTODO", "Tres cosas que sirven fuera de este trabajo", null, 4);
  const lecciones = [
    ["87%", HEX.tinta, "La accuracy engaña", "Con 13% de spam, no marcar nada acierta el 87%. Medimos spam atrapado, legítimo bloqueado y MCC."],
    ["8 de 20", HEX.sgd, "La validación cruzada no mide adaptación", "Sin ataque en el warm-up, eligió mal la regularización de SGD en 8 de 20 semillas: 125 a 153 errores, contra 65 a 83."],
    ["0,995", HEX.estatico, "Combinar necesita un experto que sobreviva", "Si ningún experto resiste el ataque, Hedge deja 0,995 del peso en el modelo dañado y no recupera nada."],
  ];
  lecciones.forEach(([valor, color, t, d], i) => {
    const x = 0.6 + i * 4.18;
    if (i > 0) regla(s, x - 0.25, 2.0, 0, 4.4);
    texto(s, valor, { x, y: 1.95, w: 3.8, h: 1.0, fontSize: 54, bold: true, color });
    texto(s, t, { x, y: 3.15, w: 3.75, h: 0.95, fontSize: 19, bold: true });
    texto(s, d, { x, y: 4.2, w: 3.75, h: 2.0, fontSize: 15, color: HEX.tinta2 });
  });
  fuente(s, "El 0,995 es de la primera versión del experto estructural, con 5 rasgos, en la semilla de desarrollo.");
  s.addNotes("B · 1:30. Tres cosas que sirven fuera de este trabajo. Accuracy engaña con datos desbalanceados. La validación cruzada sobre datos sin cambio no sirve para elegir hiperparámetros de adaptación: tuvimos que fijar el alfa de SGD. Y combinar solo funciona si algún experto sobrevive: con la primera versión del estructural, Hedge no recuperaba nada.");
}

// ===========================================================================
// 3 · Cierre (orador B)
// ===========================================================================
const S3 = "3 · Cierre";
pres.addSection({ title: S3 });

// --- 18. Cuando combinar y cuando reentrenar ---------------------------------
{
  const s = nuevaDiapositiva("OSCURA", S3);
  texto(s, "EN RESUMEN", { x: 0.6, y: 0.45, w: 8, h: 0.25, fontSize: 11, bold: true, color: HEX.tenue, charSpacing: 2 });
  texto(s, "Cuándo combinar y cuándo reentrenar", { x: 0.6, y: 0.8, w: 12, h: 0.7, fontSize: 34, fontFace: SERIF, color: HEX.blanco });
  const filas = [
    [HEX.sgd, "Etiquetas abundantes", "Reentrenar: SGD online comete 73 errores, contra 133 de Hedge."],
    [HEX.hedge, "Etiquetas escasas", "Combinar expertos diversos, con al menos uno robusto al ataque."],
    [HEX.claroOscuro, "Siempre", "Medir spam atrapado y legítimo bloqueado por separado, no accuracy."],
  ];
  filas.forEach(([color, t, d], i) => {
    const y = 2.0 + i * 1.15;
    regla(s, 0.6, y - 0.2, 12.13, 0, HEX.reglaOscura);
    circulo(s, 0.6, y + 0.08, 0.3, color, "fila " + (i + 1));
    texto(s, t, { x: 1.15, y, w: 4.2, h: 0.5, fontSize: 24, fontFace: SERIF, color: HEX.blanco });
    texto(s, d, { x: 5.5, y: y + 0.05, w: 7.2, h: 0.8, fontSize: 18, color: HEX.claroOscuro });
  });
  regla(s, 0.6, 2.0 + 3 * 1.15 - 0.2, 12.13, 0, HEX.reglaOscura);
  texto(s, "Pregunta abierta: ¿y si el modelo que reentrena fuera uno más de los expertos de Hedge? No lo probamos.", {
    x: 0.6, y: 5.75, w: 12.1, h: 0.7, fontSize: 20, fontFace: SERIF, italic: true, color: HEX.hedgeClaro });
  s.addNotes("B · 1:00. La conclusión práctica. Lowd y Meek tenían razón a medias: reentrenar seguido funciona si hay etiquetas seguido. Cuando escasean, combinar es más robusto porque tiene muchos menos parámetros. Cerrar con la pregunta abierta, aclarando que no la probamos.");
}

// --- 19. Limitaciones ---------------------------------------------------------
{
  const s = nuevaDiapositiva("CONTENIDO", S3);
  encabezado(s, "LIMITACIONES", "Lo que este trabajo no muestra", null, 0);
  const limites = [
    ["Drift sintético", "El corpus no tiene fechas: el orden y el ataque son nuestros."],
    ["Adversario que no reacciona", "Uno adaptativo degradaría las tasas de √T a T^(2/3)."],
    ["Experto robusto por construcción", "El ataque no toca dígitos ni símbolos; uno que lo hiciera lo rompería."],
    ["Pérdida 0-1 simétrica", "Bloquear un mensaje legítimo cuesta más que dejar pasar spam."],
    ["Etiqueta de dos lados", "En la práctica solo se ven los errores de lo que se entrega."],
    ["Un solo corpus", "5.574 SMS en inglés, ~305 spams atacados por semilla."],
  ];
  limites.forEach(([t, d], i) => {
    const col = i % 3, fila = Math.floor(i / 3);
    const x = 0.6 + col * 4.18, y = 2.0 + fila * 2.3;
    regla(s, x, y, 3.85, 0, HEX.tinta);
    texto(s, t, { x, y: y + 0.2, w: 3.8, h: 0.7, fontSize: 19, fontFace: SERIF });
    texto(s, d, { x, y: y + 0.95, w: 3.8, h: 0.95, fontSize: 15, color: HEX.tinta2 });
  });
  fuente(s, "Detalle en la sección de limitaciones del paper.");
  s.addNotes("B · 0:45. Mencionar rápido, sin leer todas. Las dos más importantes: el drift es sintético y el experto robusto lo es para este ataque en particular.");
}

// --- 20. Preguntas -------------------------------------------------------------
{
  const s = nuevaDiapositiva("OSCURA", S3);
  texto(s, "¿Preguntas?", { x: 0.8, y: 2.1, w: 8, h: 1.2, fontSize: 64, fontFace: SERIF, color: HEX.blanco });
  texto(s, "Combinar o reentrenar · Pablo Díaz y Ezequiel Martinez", { x: 0.8, y: 3.5, w: 9, h: 0.45, fontSize: 20, color: HEX.claroOscuro });
  regla(s, 0.8, 4.9, 6.0, 0, HEX.reglaOscura);
  texto(s, "Código, datos y paper", { x: 0.8, y: 5.1, w: 8, h: 0.3, fontSize: 13, color: HEX.tenue });
  texto(s, "github.com/pmdiaz/spam-detection-hedge", { x: 0.8, y: 5.45, w: 9, h: 0.45, fontSize: 20, bold: true, color: HEX.hedgeClaro });
  [HEX.estatico, HEX.otros, HEX.otros, HEX.otros, HEX.estructural].forEach((color, j) => {
    circulo(s, 10.3 + j * 0.5, 5.5, 0.36, color, "experto " + (j + 1));
  });
  s.addNotes("B · 0:15 + preguntas. Agradecer y abrir preguntas. Verificar antes que el repositorio sea público si se muestra el enlace.");
}

// ---------------------------------------------------------------------------
// Vista previa HTML: mismas posiciones, en pixeles (96 por pulgada).
// ---------------------------------------------------------------------------
function escapar(t) {
  return t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function htmlElemento(e) {
  const o = e.o;
  const caja = `left:${o.x * 96}px;top:${o.y * 96}px;width:${o.w * 96}px;height:${o.h * 96}px;`;
  // La vista previa se sirve junto a un enlace "visuales" a la carpeta de imagenes.
  if (e.tipo === "imagen") return `<img src="visuales/${path.basename(e.archivo)}" style="position:absolute;${caja}">`;
  if (e.tipo === "linea") {
    const borde = o.h === 0 ? "border-top" : "border-left";
    return `<div style="position:absolute;${caja}${borde}:1px solid #${o.color}"></div>`;
  }
  if (e.tipo === "rect" || e.tipo === "ellipse") {
    const radio = e.tipo === "ellipse" ? "50%" : (o.radio ? o.radio * 96 + "px" : "0");
    const fondo = o.relleno ? `background:#${o.relleno};` : "";
    const borde = o.borde ? `border:${o.grosor || 1}px solid #${o.borde};box-sizing:border-box;` : "";
    return `<div style="position:absolute;${caja}${fondo}${borde}border-radius:${radio}"></div>`;
  }
  const alinear = { top: "flex-start", middle: "center", bottom: "flex-end" }[o.valign || "top"];
  const estilo = `${caja}display:flex;flex-direction:column;justify-content:${alinear};` +
    `font-family:${o.fontFace};font-size:${o.fontSize * 96 / 72}px;color:#${o.color};` +
    `line-height:${1.2 * (o.lineSpacingMultiple || 1)};text-align:${o.align || "left"};` +
    `letter-spacing:${(o.charSpacing || 0) * 96 / 72}px;font-weight:${o.bold ? 700 : 400};font-style:${o.italic ? "italic" : "normal"};` +
    `outline:1px dashed rgba(255,0,0,.18);`;
  let contenido = "";
  for (const c of e.corridas) {
    const co = c.options || {};
    let span = escapar(c.text).replace(/\n/g, "<br>");
    const s = [];
    if (co.bold) s.push("font-weight:700");
    if (co.italic) s.push("font-style:italic");
    if (co.color) s.push(`color:#${co.color}`);
    if (co.superscript) span = `<sup>${span}</sup>`;
    if (co.subscript) span = `<sub>${span}</sub>`;
    contenido += `<span style="${s.join(";")}">${span}</span>` + (co.breakLine ? "<br>" : "");
  }
  return `<div style="position:absolute;${estilo}"><div>${contenido}</div></div>`;
}

function escribirVistaPrevia(archivo) {
  const diapositivas = vista.map((d) => {
    const extras = d.contenido
      ? `<div style="position:absolute;left:${0.6 * 96}px;top:${6.88 * 96}px;width:${12.13 * 96}px;border-top:1px solid #${HEX.regla}"></div>` +
        `<div style="position:absolute;left:${NUMERO.x * 96}px;top:${NUMERO.y * 96}px;width:${NUMERO.w * 96}px;text-align:right;font:${NUMERO.fontSize * 96 / 72}px ${SANS};color:#${HEX.tenue}">${d.numero}</div>`
      : "";
    return `<section id="d${d.numero}" style="position:relative;width:1280px;height:720px;background:#${d.fondo};overflow:hidden;margin:0 0 24px">` +
      d.elementos.map(htmlElemento).join("") + extras + "</section>";
  });
  fs.writeFileSync(archivo, `<!doctype html><html><head><meta charset="utf-8"><title>Vista previa</title>` +
    `<style>body{margin:0;padding:24px;background:#888}</style></head><body>${diapositivas.join("\n")}</body></html>`);
}

pres.writeFile({ fileName: SALIDA_PPTX }).then(async () => {
  await applyTheme(SALIDA_PPTX, THEME);
  if (SALIDA_HTML) escribirVistaPrevia(SALIDA_HTML);
  console.log("escrito:", SALIDA_PPTX, vista.length, "diapositivas");
});
