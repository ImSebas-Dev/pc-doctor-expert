/* Arranque: sesión, navegación por hash con gestión de foco y título (WCAG 2.4.2, 2.4.3, 4.1.3). */
import { api, sesion } from "./api.js";
import { anunciar, avisar, avisos, cargando, h, icono, mensaje } from "./ui.js";
import { ayuda, ingresar, perfil, registro } from "./vistas/cuenta.js";
import { detalle, historial } from "./vistas/historial.js";
import { diagnostico } from "./vistas/diagnostico.js";
import { equipos } from "./vistas/equipos.js";
import { inicio } from "./vistas/inicio.js";
import { conocimiento, pruebas, reglas, usuarios } from "./vistas/admin.js";

const RUTAS = [
  ["/", inicio, "usuario"], ["/equipos", equipos, "usuario"], ["/diagnostico", diagnostico, "usuario"], ["/historial", historial, "usuario"],
  ["/historial/:id", detalle, "usuario"], ["/perfil", perfil, "usuario"], ["/ayuda", ayuda, "publica"],
  ["/ingresar", ingresar, "anonima"], ["/registro", registro, "anonima"],
  ["/admin/usuarios", usuarios, "admin"], ["/admin/conocimiento", conocimiento, "admin"], ["/admin/reglas", reglas, "admin"], ["/admin/pruebas", pruebas, "admin"],
];
const NAV = [["/", "Inicio", "inicio"], ["/equipos", "Equipos", "equipos"], ["/diagnostico", "Diagnóstico", "diagnostico"], ["/historial", "Historial", "historial"]];
const NAV_ADMIN = [["/admin/usuarios", "Admin", "admin"]];
const raiz = document.getElementById("contenido");

function coincidir(ruta) {
  const [camino, consulta = ""] = ruta.split("?");
  const partes = camino.split("/");
  for (const [patron, vista, acceso] of RUTAS) {
    const p = patron.split("/");
    if (p.length !== partes.length) continue;
    const params = Object.fromEntries(new URLSearchParams(consulta));
    if (p.every((x, i) => (x.startsWith(":") ? !!(params[x.slice(1)] = partes[i]) : x === partes[i]))) return { vista, acceso, params, camino };
  }
  return null;
}

function pintarCabecera(camino) {
  const u = sesion.usuario;
  const enlaces = u ? [...NAV, ...(u.rol === "administrador" ? NAV_ADMIN : [])] : [];
  const actual = (ruta) => (ruta === "/" ? camino === "/" : camino.startsWith(ruta.split("/").slice(0, 2).join("/")));
  document.getElementById("nav").replaceChildren(...enlaces.map(([ruta, texto, ic]) => h("a", { href: `#${ruta}`, "aria-current": actual(ruta) ? "page" : null }, icono(ic), h("span", null, texto))));
  document.getElementById("cuenta").classList.toggle("anonima", !u);
  document.getElementById("cuenta").replaceChildren(...(u ? [h("a", { href: "#/perfil", class: "boton sutil perfil", "aria-label": `Mi perfil (${u.nombre})` }, h("span", { class: "avatar", "aria-hidden": "true" }, u.nombre.trim().charAt(0).toUpperCase()), h("span", { class: "nombre-usuario" }, u.nombre)),
    h("button", { type: "button", class: "boton", onclick: cerrarSesion }, "Salir", h("span", { class: "solo-lector" }, " de la sesión"))] : [h("a", { href: "#/ingresar", class: "boton sutil" }, "Iniciar sesión"), h("a", { href: "#/registro", class: "boton primario" }, "Crear cuenta")]));
}

async function cerrarSesion() {
  await api("post", "/api/logout", {});
  sesion.usuario = null;
  avisar("exito", "Cerraste la sesión.");
  location.hash = "#/ingresar";
}

async function navegar() {
  const ruta = location.hash.slice(1) || "/";
  const destino = coincidir(ruta);
  if (!destino) { raiz.replaceChildren(h("h1", { tabindex: "-1" }, "Página no encontrada"), h("p", null, h("a", { href: "#/" }, "Volver al inicio"))); return; }
  const u = sesion.usuario;
  if (destino.acceso === "anonima" && u) { location.replace("#/"); return; }
  if (["usuario", "admin"].includes(destino.acceso) && !u) { location.replace("#/ingresar"); return; }
  if (destino.acceso === "admin" && u.rol !== "administrador") { location.replace("#/"); return; }
  pintarCabecera(destino.camino);
  raiz.setAttribute("aria-busy", "true");
  raiz.replaceChildren(cargando());
  try {
    const { titulo, nodo } = await destino.vista(destino.params);
    document.title = `${titulo} · PC Doctor Expert`;
    raiz.replaceChildren(...(avisos.pendiente ? [mensaje(avisos.pendiente.tipo, avisos.pendiente.texto)] : []), nodo);
    avisos.pendiente = null;
  } catch (e) {
    document.title = "Error · PC Doctor Expert";
    raiz.replaceChildren(h("h1", { tabindex: "-1" }, "No se pudo cargar la página"), mensaje("error", e.message), h("button", { class: "boton", type: "button", onclick: navegar }, "Reintentar"));
  } finally { raiz.removeAttribute("aria-busy"); }
  const titulo = raiz.querySelector("h1");
  (titulo || raiz).setAttribute("tabindex", "-1");
  (titulo || raiz).focus();
  anunciar(document.title);
}

document.getElementById("saltar").addEventListener("click", (e) => { e.preventDefault(); raiz.focus(); });
document.addEventListener("sesion-vencida", () => { sesion.usuario = null; avisar("advertencia", "Tu sesión venció por inactividad. Inicia sesión de nuevo."); location.hash = "#/ingresar"; });
window.addEventListener("hashchange", navegar);
const s = await api("get", "/api/sesion").catch(() => ({ usuario: null, csrf: "" }));
sesion.usuario = s.usuario; sesion.csrf = s.csrf;
navegar();
