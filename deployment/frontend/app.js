"use strict";

const $ = (id) => document.getElementById(id);
const estado = { metricas: null, totalFiltrado: 0 };
const nombresGrupo = { 0: "Intermedio", 1: "Adultos", 2: "Jóvenes" };

function escapar(valor) {
  return String(valor).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[c]);
}

async function api(ruta, params = {}, opciones = {}) {
  const url = new URL(window.BACKEND_URL + ruta);
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor !== "" && valor !== null && valor !== undefined) {
      url.searchParams.set(clave, valor);
    }
  });
  const respuesta = await fetch(url, opciones);
  if (!respuesta.ok) {
    const texto = await respuesta.text();
    throw new Error(`${ruta} → ${respuesta.status}: ${texto}`);
  }
  return respuesta.json();
}

function filtros() {
  const a = parseFloat($("filtro-edad-min").value);
  const b = parseFloat($("filtro-edad-max").value);
  return {
    grupo: $("filtro-grupo").value,
    etiqueta: $("filtro-etiqueta").value,
    sexo: $("filtro-sexo").value,
    edad_min: Math.min(a, b),
    edad_max: Math.max(a, b),
  };
}

function textoFiltros(f) {
  const partes = [];
  if (f.grupo !== "") partes.push("grupo " + (nombresGrupo[f.grupo] || f.grupo).toLowerCase());
  if (f.etiqueta !== "") partes.push(f.etiqueta === "1" ? "solo quienes tienen la condición" : "solo quienes no la tienen");
  if (f.sexo !== "") partes.push(f.sexo === "1" ? "hombres" : "mujeres");
  if (Number(f.edad_min) > -3 || Number(f.edad_max) < 3) {
    partes.push("edades entre " + f.edad_min + " y " + f.edad_max);
  }
  return partes.length ? partes.join(" · ") : "Todas las personas";
}

function sincronizarEtiquetas() {
  $("edad-min-valor").textContent = $("filtro-edad-min").value;
  $("edad-max-valor").textContent = $("filtro-edad-max").value;
  $("corte-valor").textContent = $("corte-slider").value;
  $("filtros-activos").innerHTML =
    '<span class="punto-vivo"></span>' + escapar(textoFiltros(filtros()));
}

let temporizadorFiltros = null;
function alMoverFiltro() {
  sincronizarEtiquetas();
  clearTimeout(temporizadorFiltros);
  temporizadorFiltros = setTimeout(() => {
    cargarConteo().then(cargarMuestra).catch(mostrarError);
  }, 80);
}

function tablaHTML(filas) {
  if (!filas || filas.length === 0) return "<p>No hay datos con estos filtros.</p>";
  const columnas = Object.keys(filas[0]);
  const cabecera = columnas.map((c) => `<th>${escapar(c)}</th>`).join("");
  const cuerpo = filas.map((f) =>
    `<tr>${columnas.map((c) => `<td>${escapar(f[c])}</td>`).join("")}</tr>`
  ).join("");
  return `<table><thead><tr>${cabecera}</tr></thead><tbody>${cuerpo}</tbody></table>`;
}

function barrasHTML(items, claveValor, claveTexto, maximo, activo) {
  if (!items || items.length === 0) return "<p>No hay datos.</p>";
  const tope = maximo || Math.max(...items.map((i) => Number(i[claveValor]) || 0)) || 1;
  return items.map((item) => {
    const valor = Number(item[claveValor]) || 0;
    const ancho = Math.max(2, Math.round((valor / tope) * 100));
    const marca = activo !== undefined && String(item[claveTexto]) === String(activo) ? " activa" : "";
    return `<div class="barra${marca}">
      <span>${escapar(item[claveTexto])}</span>
      <div class="pista"><div class="relleno" style="width:${ancho}%"></div></div>
      <span class="valor">${valor.toFixed(3)}</span>
    </div>`;
  }).join("");
}

function mostrarError(error) {
  console.error(error);
  $("descarga-estado").textContent = "No pudimos cargar los datos: " + error.message;
}

async function cargarResumen() {
  const datos = await api("/resumen");
  $("card-filas").textContent = datos.filas.toLocaleString("es-ES");
  $("card-columnas").textContent = datos.columnas;
  $("card-duplicados").textContent = datos.duplicados;
}

async function cargarConteo() {
  const datos = await api("/datos/conteo", filtros());
  estado.totalFiltrado = datos.personas;
  $("card-personas").textContent = datos.personas.toLocaleString("es-ES");
  $("card-prevalencia").textContent = (datos.prevalencia * 100).toFixed(0) + "%";
  const entradas = Object.entries(datos.por_grupo);
  if (entradas.length) {
    const [grupo] = entradas.reduce((a, b) => (b[1] > a[1] ? b : a));
    $("card-grupo").textContent = nombresGrupo[grupo] || grupo;
  } else {
    $("card-grupo").textContent = "—";
  }
}

async function cargarClasificacion() {
  estado.metricas = await api("/metricas");
  renderBarrido();
}

async function cargarDesacuerdos(k) {
  try {
    const datos = await api("/clasificacion/desacuerdos", { k, limit: 10 });
    $("desacuerdos-table").innerHTML = tablaHTML(datos);
  } catch (error) {
    mostrarError(error);
  }
}

function renderBarrido() {
  if (!estado.metricas) return;
  const k = Number($("k-select").value);
  const filas = estado.metricas.barrido
    .filter((f) => f.weights === "uniform")
    .map((f) => ({ ...f, etiqueta: f.k + " parecidos" }));
  $("barrido-chart").innerHTML = barrasHTML(
    filas, "accuracy_test", "etiqueta", 1, k + " parecidos"
  );

  const elegida = estado.metricas.detalle.find((f) => Number(f.k) === k);
  if (!elegida) return;

  const aciertos = Math.round(elegida.accuracy_test * 1000);
  $("k-grande").textContent = aciertos;
  $("k-frase").textContent =
    `Al mirar ${k} ${k === 1 ? "parecido" : "parecidos"}, el modelo acierta ` +
    `${aciertos} de cada 1000 casos en la prueba.`;
  $("k-resumen").innerHTML =
    `Cuando dice que sí, acierta ${Math.round(elegida.precision_test * 1000)} de cada 1000. ` +
    `<span class="tecnico">F1 ${elegida.f1_test.toFixed(3)} · recall ${elegida.recall_test.toFixed(3)}</span>`;

  const nb = estado.metricas.modelos.find((m) => m.modelo === "GaussianNB") || {};
  $("metricas-table").innerHTML = tablaHTML([
    {
      modelo: "Naive Bayes",
      accuracy_test: nb.accuracy_test,
      precision_test: nb.precision_test,
      recall_test: nb.recall_test,
      f1_test: nb.f1_test,
    },
    {
      modelo: `KNN · ${k} ${k === 1 ? "parecido" : "parecidos"}`,
      accuracy_test: elegida.accuracy_test,
      precision_test: elegida.precision_test,
      recall_test: elegida.recall_test,
      f1_test: elegida.f1_test,
    },
  ]);
  $("matrices-table").innerHTML = tablaHTML(
    estado.metricas.matrices.map((m) => ({
      modelo: m.modelo,
      TN: m.TN, FP: m.FP, FN: m.FN, TP: m.TP,
    }))
  );
  cargarDesacuerdos(k);
}

async function cargarPerfil() {
  const datos = await api("/clustering/perfil");
  $("perfil-table").innerHTML = tablaHTML(datos);
  $("perfil-cards").innerHTML = datos.map((f) => `
    <div class="cifra">
      <span class="numero">${escapar(nombresGrupo[f.cluster] || f.cluster)}</span>
      <span class="etiqueta">${Number(f.personas).toLocaleString("es-ES")} personas</span>
      <span class="etiqueta">${(f.prevalencia_diabetes_obesidad_colesterol * 100).toFixed(0)} de cada 100 tienen la condición</span>
    </div>`).join("");
}

async function cargarComparacion() {
  const datos = await api("/clustering/comparacion");
  $("comparacion-grid").innerHTML = `
    <div class="cifra"><span class="numero">${Number(datos.ari_jerarquico_vs_kmeans).toFixed(2)}</span><span class="etiqueta">de 1 · cuánto coinciden</span></div>
    <div class="cifra"><span class="numero">${Number(datos.corte_3_grupos_desde).toFixed(0)}–${Number(datos.corte_3_grupos_hasta).toFixed(0)}</span><span class="etiqueta">altura que dio 3 grupos</span></div>
    <div class="cifra"><span class="numero">${Number(datos.tiempo_jerarquico_s).toFixed(1)} s</span><span class="etiqueta">tiempo que tardó</span></div>
    <div class="cifra"><span class="numero">${Number(datos.pico_memoria_jerarquico_mb).toFixed(0)} MB</span><span class="etiqueta">memoria que usó</span></div>`;
  $("dendrograma").src = window.BACKEND_URL + "/figura/dendrograma";
}

async function cargarCorte() {
  const altura = $("corte-slider").value;
  const datos = await api("/clustering/corte", { altura });
  $("corte-grande").textContent = datos.grupos;
  $("corte-resultado").textContent =
    `Al cortar a la altura ${datos.altura} salen ${datos.grupos} grupos (de 5 000 personas miradas).`;
  const items = Object.entries(datos.tamanos).map(([nombre, cantidad]) => ({
    etiqueta: "Grupo " + nombre,
    cantidad,
  }));
  $("corte-barras").innerHTML = barrasHTML(items, "cantidad", "etiqueta", 5000);
}

async function cargarMuestra() {
  const datos = await api("/clustering/muestra", { ...filtros(), limit: 20 });
  $("muestra-table").innerHTML = tablaHTML(datos);
  $("muestra-rango").textContent =
    `Mostrando ${datos.length} de ${estado.totalFiltrado.toLocaleString("es-ES")} personas.`;
}

function leerFormulario(formulario) {
  const datos = new FormData(formulario);
  return {
    edad: Number(datos.get("edad")),
    cintura: Number(datos.get("cintura")),
    calorias: Number(datos.get("calorias")),
    sexo: Number(datos.get("sexo")),
  };
}

let temporizadorPrediccion = null;
function alMoverFormulario(formulario, funcion) {
  clearTimeout(temporizadorPrediccion);
  temporizadorPrediccion = setTimeout(() => funcion(), 180);
}

async function predecirClasificacion() {
  try {
    const cuerpo = {
      ...leerFormulario($("form-clasificacion")),
      k: Number($("k-select").value),
    };
    const datos = await api("/clasificacion/predecir", {}, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });
    $("clas-resultado").textContent =
      `Con ${datos.k} ${datos.k === 1 ? "parecido" : "parecidos"}: ` +
      `${datos.frase} Un modelo dice ${datos.predice_knn} (seguridad ${Math.round(datos.prob_knn * 100)}%) ` +
      `y el otro dice ${datos.predice_nb} (seguridad ${Math.round(datos.prob_nb * 100)}%).`;
  } catch (error) {
    mostrarError(error);
  }
}

async function predecirCluster() {
  try {
    const datos = await api("/clustering/predecir", {}, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(leerFormulario($("form-clustering"))),
    });
    $("clus-resultado").textContent = `Grupo ${nombresGrupo[datos.grupo] || datos.grupo}. ${datos.frase}`;
  } catch (error) {
    mostrarError(error);
  }
}

async function inicializar() {
  try {
    sincronizarEtiquetas();
    await cargarResumen();
    await Promise.all([
      cargarConteo(),
      cargarClasificacion(),
      cargarPerfil(),
      cargarComparacion(),
      cargarCorte(),
      cargarMuestra(),
    ]);
    await predecirClasificacion();
    await predecirCluster();
  } catch (error) {
    mostrarError(error);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("modo-sencillo").addEventListener("click", () => {
    document.body.classList.remove("modo-tecnico");
    $("modo-sencillo").classList.add("activo");
    $("modo-tecnico").classList.remove("activo");
  });
  $("modo-tecnico").addEventListener("click", () => {
    document.body.classList.add("modo-tecnico");
    $("modo-tecnico").classList.add("activo");
    $("modo-sencillo").classList.remove("activo");
  });

  ["filtro-grupo", "filtro-etiqueta", "filtro-sexo", "filtro-edad-min", "filtro-edad-max"].forEach((id) => {
    $(id).addEventListener("input", alMoverFiltro);
    $(id).addEventListener("change", alMoverFiltro);
  });

  $("limpiar-filtros").addEventListener("click", () => {
    $("filtro-grupo").value = "";
    $("filtro-etiqueta").value = "";
    $("filtro-sexo").value = "";
    $("filtro-edad-min").value = -3;
    $("filtro-edad-max").value = 3;
    alMoverFiltro();
  });

  $("k-select").addEventListener("input", () => {
    renderBarrido();
    alMoverFormulario($("form-clasificacion"), predecirClasificacion);
  });
  $("k-select").addEventListener("change", () => renderBarrido());

  let temporizadorCorte = null;
  $("corte-slider").addEventListener("input", () => {
    $("corte-valor").textContent = $("corte-slider").value;
    clearTimeout(temporizadorCorte);
    temporizadorCorte = setTimeout(() => cargarCorte().catch(mostrarError), 80);
  });

  $("form-clasificacion").addEventListener("input", () => {
    alMoverFormulario($("form-clasificacion"), predecirClasificacion);
  });
  $("form-clustering").addEventListener("input", () => {
    alMoverFormulario($("form-clustering"), predecirCluster);
  });
  $("form-clasificacion").addEventListener("submit", (evento) => {
    evento.preventDefault();
    predecirClasificacion();
  });
  $("form-clustering").addEventListener("submit", (evento) => {
    evento.preventDefault();
    predecirCluster();
  });

  $("descarga-btn").addEventListener("click", () => {
    const url = new URL(window.BACKEND_URL + "/datos/descarga");
    Object.entries(filtros()).forEach(([clave, valor]) => {
      if (valor !== "" && valor !== null) url.searchParams.set(clave, valor);
    });
    window.location.href = url.toString();
    $("descarga-estado").textContent = "Bajando el archivo con lo que está viendo…";
  });

  inicializar();
});
