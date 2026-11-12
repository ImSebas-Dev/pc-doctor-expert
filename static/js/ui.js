/* Componentes Fluent accesibles construidos con el DOM (nunca con innerHTML: el texto de usuarios no se interpreta como HTML). */
import { ErrorApi } from "./api.js";

export function h(etiqueta, props, ...hijos) {
  const el = document.createElement(etiqueta);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "for") el.htmlFor = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k in el && !k.includes("-")) el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  el.append(...hijos.flat(Infinity).filter((x) => x != null && x !== false));
  return el;
}

const RUTAS_ICONO = {
  info: "M10 2a8 8 0 100 16 8 8 0 000-16zm0 3.5a1 1 0 110 2 1 1 0 010-2zM9 9h2v5H9z",
  exito: "M10 2a8 8 0 100 16 8 8 0 000-16zm-1.2 11.4L5.6 10.2l1.4-1.4 1.8 1.8 4.2-4.2 1.4 1.4z",
  advertencia: "M10 2l8.5 15H1.5zM9 7h2v5H9zm0 6h2v2H9z",
  error: "M10 2a8 8 0 100 16 8 8 0 000-16zm3.5 10.1l-1.4 1.4L10 11.4l-2.1 2.1-1.4-1.4L8.6 10 6.5 7.9l1.4-1.4L10 8.6l2.1-2.1 1.4 1.4L11.4 10z",
};
export function icono(nombre) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 20 20"); svg.setAttribute("class", "icono"); svg.setAttribute("aria-hidden", "true");
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", RUTAS_ICONO[nombre]); svg.append(p);
  return svg;
}

export function mensaje(tipo, texto) {
  return h("div", { class: `mensaje ${tipo}`, role: tipo === "error" ? "alert" : "status" }, icono(tipo === "info" ? "info" : tipo), h("p", null, texto));
}

export function anunciar(texto) {
  const r = document.getElementById("anuncios");
  r.textContent = "";
  setTimeout(() => { r.textContent = texto; }, 50);
}

export const fecha = (iso) => new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
export const porcentaje = (n) => `${n.toLocaleString("es-CO", { maximumFractionDigits: 1 })} %`;

/* Campo de formulario con etiqueta, ayuda y error asociados (WCAG 1.3.1, 3.3.1, 3.3.2, 1.3.5). */
let contador = 0;
export function campo({ nombre, etiqueta, tipo = "text", valor = "", ayuda = "", autocompletar, requerido = true, maximo, minimo, opciones, filas, soloLectura }) {
  const id = `c${++contador}-${nombre}`;
  const aria = `${id}-ayuda ${id}-error`;
  const comun = { id, name: nombre, "aria-describedby": aria, autocomplete: autocompletar, required: requerido, "aria-required": requerido ? "true" : null };
  let entrada, raiz;
  if (tipo === "casilla") {
    entrada = h("input", { ...comun, type: "checkbox", checked: !!valor, required: false, "aria-required": null });
    raiz = h("div", { class: "campo" }, h("div", { class: "casilla" }, entrada, h("label", { for: id }, etiqueta)), h("p", { id: `${id}-ayuda`, class: "ayuda" }, ayuda), h("p", { id: `${id}-error`, class: "error-campo" }));
  } else {
    if (tipo === "select") entrada = h("select", comun, opciones.map((o) => h("option", { value: o.valor, selected: o.valor === valor }, o.texto)));
    else if (tipo === "textarea") entrada = h("textarea", { ...comun, rows: filas || 5, maxLength: maximo, value: valor });
    else entrada = h("input", { ...comun, type: tipo, value: valor, maxLength: maximo, min: minimo, max: maximo && tipo === "number" ? maximo : null, inputMode: tipo === "number" ? "numeric" : null, readOnly: soloLectura });
    raiz = h("div", { class: "campo" }, h("label", { for: id }, etiqueta, requerido ? h("span", { "aria-hidden": "true" }, " *") : null), entrada,
      h("p", { id: `${id}-ayuda`, class: "ayuda" }, ayuda), h("p", { id: `${id}-error`, class: "error-campo" }));
  }
  const errorEl = raiz.querySelector(".error-campo");
  return {
    nombre, raiz, entrada, requerido: requerido && tipo !== "casilla", id,
    valor: () => (tipo === "casilla" ? entrada.checked : tipo === "number" ? (entrada.value === "" ? "" : Number(entrada.value)) : tipo === "textarea" ? entrada.value : entrada.value),
    fallar(texto) { entrada.setAttribute("aria-invalid", "true"); errorEl.textContent = texto; },
    limpiar() { entrada.removeAttribute("aria-invalid"); errorEl.textContent = ""; },
  };
}

/* Formulario con validación, resumen de errores enfocable y estado de envío. */
export function formulario({ campos, enviar, boton = "Guardar", extra }) {
  const resumen = h("div", { class: "resumen-errores", role: "alert", tabindex: "-1", hidden: true });
  const btn = h("button", { class: "boton primario", type: "submit" }, boton);
  const mostrar = (errores) => {
    resumen.replaceChildren(h("p", null, errores.length === 1 ? "Hay un problema por corregir:" : `Hay ${errores.length} problemas por corregir:`),
      h("ul", null, errores.map((e) => h("li", null, e.campo ? h("button", { type: "button", class: "enlace", onclick: () => e.campo.entrada.focus() }, e.texto) : e.texto))));
    resumen.hidden = false;
    resumen.focus();
  };
  const form = h("form", { novalidate: true, onsubmit: async (ev) => {
    ev.preventDefault();
    resumen.hidden = true;
    campos.forEach((c) => c.limpiar());
    const datos = {}, errores = [];
    for (const c of campos) {
      datos[c.nombre] = c.valor();
      if (c.requerido && (datos[c.nombre] === "" || datos[c.nombre] == null)) { c.fallar("Este dato es obligatorio."); errores.push({ campo: c, texto: `${c.raiz.querySelector("label").textContent.replace(" *", "")}: este dato es obligatorio.` }); }
    }
    if (errores.length) return mostrar(errores);
    btn.disabled = true; form.setAttribute("aria-busy", "true");
    try { await enviar(datos); }
    catch (e) {
      if (!(e instanceof ErrorApi)) throw e;
      const c = campos.find((x) => x.nombre === e.campo);
      if (c) c.fallar(e.message);
      mostrar([{ campo: c, texto: e.message }]);
    } finally { btn.disabled = false; form.removeAttribute("aria-busy"); }
  } }, resumen, campos.map((c) => c.raiz), h("div", { class: "acciones" }, btn, extra));
  return form;
}

/* Diálogo modal nativo: atrapa el foco, se cierra con Esc y devuelve el foco a quien lo abrió. */
export function dialogo(titulo, ...contenido) {
  const id = `d${++contador}`;
  const d = h("dialog", { "aria-labelledby": id }, h("h2", { id }, titulo), ...contenido);
  d.addEventListener("close", () => d.remove());
  document.body.append(d);
  d.showModal();
  return d;
}

export function confirmar(titulo, texto, boton) {
  return new Promise((resolver) => {
    const d = dialogo(titulo, h("p", null, texto), h("div", { class: "acciones" },
      h("button", { class: "boton primario", type: "button", onclick: () => { resolver(true); d.close(); } }, boton),
      h("button", { class: "boton", type: "button", onclick: () => d.close() }, "Cancelar")));
    d.addEventListener("close", () => resolver(false));
  });
}

export const cargando = (texto = "Cargando…") => h("p", { class: "cargando", role: "status" }, h("span", { class: "spinner", "aria-hidden": "true" }), texto);

export function tabla(titulo, columnas, filas) {
  return h("div", { class: "tabla-scroll", role: "region", "aria-label": titulo, tabindex: "0" },
    h("table", null, h("caption", null, titulo), h("thead", null, h("tr", null, columnas.map((c) => h("th", { scope: "col" }, c)))),
      h("tbody", null, filas.map((f) => h("tr", null, f.map((c) => h("td", null, c)))))));
}

/* Aviso que se muestra una sola vez en la página siguiente (por ejemplo, tras guardar). */
export const avisos = { pendiente: null };
export const avisar = (tipo, texto) => { avisos.pendiente = { tipo, texto }; };
