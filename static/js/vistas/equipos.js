/* Equipos del usuario: listar, agregar, editar y eliminar (RF-01). */
import { api } from "../api.js";
import { anunciar, campo, confirmar, dialogo, formulario, h, mensaje } from "../ui.js";

const CAMPOS = [["nombre", "Nombre del equipo", "Por ejemplo: Portátil de la oficina"], ["procesador", "Procesador", "Por ejemplo: Intel Core i7"],
  ["ram_gb", "Memoria RAM (GB)", ""], ["gpu", "Tarjeta gráfica", "Por ejemplo: NVIDIA GTX 1660 o integrada"], ["almacenamiento", "Almacenamiento", "Por ejemplo: SSD 512 GB"], ["sistema_operativo", "Sistema operativo", "Por ejemplo: Windows 11"]];

function editor(equipo, alGuardar) {
  const campos = CAMPOS.map(([nombre, etiqueta, ayuda]) => campo({ nombre, etiqueta, ayuda, valor: equipo?.[nombre] ?? "", tipo: nombre === "ram_gb" ? "number" : "text", minimo: nombre === "ram_gb" ? 1 : undefined, maximo: nombre === "ram_gb" ? 1024 : 80 }));
  const d = dialogo(equipo ? "Editar equipo" : "Agregar equipo", h("p", { class: "ayuda" }, "Los campos con asterisco (*) son obligatorios."),
    formulario({ campos, boton: "Guardar", extra: h("button", { type: "button", class: "boton", onclick: () => d.close() }, "Cancelar"),
      enviar: async (datos) => { await api(equipo ? "put" : "post", equipo ? `/api/equipos/${equipo.id}` : "/api/equipos", datos); d.close(); await alGuardar(); } }));
}

export async function equipos() {
  const lista = h("div", { class: "rejilla" });
  const pintar = async (anuncio) => {
    const { equipos: es } = await api("get", "/api/equipos");
    lista.replaceChildren(...(es.length ? es.map((e) => h("section", { class: "tarjeta", "aria-labelledby": `eq-${e.id}` },
      h("h2", { id: `eq-${e.id}` }, e.nombre),
      h("dl", { class: "datos" }, ...[["Procesador", e.procesador], ["Memoria RAM", `${e.ram_gb} GB`], ["Tarjeta gráfica", e.gpu], ["Almacenamiento", e.almacenamiento], ["Sistema", e.sistema_operativo]].flatMap(([t, v]) => [h("dt", null, t), h("dd", null, v)])),
      h("div", { class: "acciones" },
        h("a", { class: "boton primario", href: `#/diagnostico?equipo=${e.id}` }, "Diagnosticar", h("span", { class: "solo-lector" }, ` ${e.nombre}`)),
        h("button", { class: "boton", type: "button", onclick: () => editor(e, () => pintar(`Equipo ${e.nombre} actualizado`)) }, "Editar", h("span", { class: "solo-lector" }, ` ${e.nombre}`)),
        h("button", { class: "boton peligro", type: "button", onclick: async () => {
          if (await confirmar("Eliminar equipo", `Se eliminará «${e.nombre}» y también sus diagnósticos. Esta acción no se puede deshacer.`, "Eliminar")) {
            await api("delete", `/api/equipos/${e.id}`, {}); await pintar(`Equipo ${e.nombre} eliminado`); document.querySelector("#contenido h1").focus(); } } }, "Eliminar", h("span", { class: "solo-lector" }, ` ${e.nombre}`)))))
      : [mensaje("info", "Aún no tienes equipos. Agrega el primero para poder hacer un diagnóstico.")]));
    if (anuncio) anunciar(anuncio);
  };
  await pintar();
  const nodo = h("div", null, h("div", { class: "cabecera-pagina" }, h("h1", null, "Mis equipos"),
    h("button", { class: "boton primario", type: "button", onclick: () => editor(null, () => pintar("Equipo agregado")) }, "Agregar equipo")), lista);
  return { titulo: "Mis equipos", nodo };
}
