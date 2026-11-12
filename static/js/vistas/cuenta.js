/* Ingreso, registro, perfil y ayuda (RF-01). */
import { api, sesion } from "../api.js";
import { avisar, campo, formulario, h, icono } from "../ui.js";

/* Panel de bienvenida junto a los formularios de acceso (se oculta su lista en pantallas pequeñas). */
const lado = () => h("aside", { class: "acceso-lado" }, h("h2", null, "Diagnostica tu computador en minutos"),
  h("p", null, "Responde preguntas sencillas y obtén las causas más probables de la falla y qué hacer."),
  h("ul", null, ["Sin términos técnicos", "Recomendaciones paso a paso", "Historial de tus diagnósticos"].map((t) => h("li", null, icono("cumple"), t))));

const alternarClave = (...entradas) => h("div", { class: "campo casilla" },
  h("input", { type: "checkbox", id: "ver-clave", onchange: (e) => entradas.forEach((c) => { c.entrada.type = e.target.checked ? "text" : "password"; }) }),
  h("label", { for: "ver-clave" }, "Mostrar contraseña"));

async function entrar(ruta, datos) {
  const r = await api("post", ruta, datos);
  sesion.usuario = r.usuario;
  location.hash = "#/";
}

export async function ingresar() {
  const correo = campo({ nombre: "correo", etiqueta: "Correo electrónico", tipo: "email", autocompletar: "username" });
  const clave = campo({ nombre: "clave", etiqueta: "Contraseña", tipo: "password", autocompletar: "current-password" });
  const nodo = h("div", { class: "acceso" }, lado(), h("section", { class: "tarjeta" }, h("h1", null, "Iniciar sesión"),
    h("p", { class: "subtitulo" }, "Entra para registrar tus equipos y consultar tus diagnósticos."),
    formulario({ campos: [correo, clave], boton: "Iniciar sesión", enviar: (d) => entrar("/api/login", d) }),
    h("div", { class: "campo" }, alternarClave(clave)),
    h("p", null, "¿Aún no tienes cuenta? ", h("a", { href: "#/registro" }, "Crea una cuenta"))));
  return { titulo: "Iniciar sesión", nodo };
}

export async function registro() {
  const nombre = campo({ nombre: "nombre", etiqueta: "Nombre", autocompletar: "name", maximo: 80 });
  const correo = campo({ nombre: "correo", etiqueta: "Correo electrónico", tipo: "email", autocompletar: "username" });
  const clave = campo({ nombre: "clave", etiqueta: "Contraseña", tipo: "password", autocompletar: "new-password", ayuda: "Entre 10 y 128 caracteres. Puedes usar una frase y pegarla desde tu administrador de contraseñas." });
  const nodo = h("div", { class: "acceso" }, lado(), h("section", { class: "tarjeta" }, h("h1", null, "Crear cuenta"),
    h("p", { class: "subtitulo" }, "Los campos con asterisco (*) son obligatorios."),
    formulario({ campos: [nombre, correo, clave], boton: "Crear cuenta", enviar: (d) => entrar("/api/registro", d) }),
    alternarClave(clave),
    h("p", null, "¿Ya tienes cuenta? ", h("a", { href: "#/ingresar" }, "Inicia sesión"))));
  return { titulo: "Crear cuenta", nodo };
}

export async function perfil() {
  const u = sesion.usuario;
  const nombre = campo({ nombre: "nombre", etiqueta: "Nombre", valor: u.nombre, autocompletar: "name", maximo: 80 });
  const actual = campo({ nombre: "clave_actual", etiqueta: "Contraseña actual", tipo: "password", autocompletar: "current-password", requerido: false });
  const nueva = campo({ nombre: "clave_nueva", etiqueta: "Contraseña nueva", tipo: "password", autocompletar: "new-password", requerido: false, ayuda: "Déjala vacía si no quieres cambiarla. Entre 10 y 128 caracteres." });
  const nodo = h("div", null, h("h1", null, "Mi perfil"),
    h("section", { class: "tarjeta" }, h("p", null, "Correo: ", h("strong", null, u.correo), " · Rol: ", h("strong", null, u.rol)),
      formulario({ campos: [nombre, actual, nueva], boton: "Guardar cambios", enviar: async (d) => {
        const r = await api("put", "/api/perfil", d.clave_nueva ? d : { nombre: d.nombre });
        sesion.usuario = r.usuario; actual.entrada.value = ""; nueva.entrada.value = "";
        avisar("exito", "Tus cambios se guardaron."); location.hash = "#/"; } })));
  return { titulo: "Mi perfil", nodo };
}

export async function ayuda() {
  const nodo = h("article", null, h("h1", null, "Ayuda y accesibilidad"),
    h("section", { class: "tarjeta" },
      h("h2", null, "Cómo funciona"),
      h("ol", { class: "pasos" }, h("li", null, "Registra tu equipo con sus datos básicos."), h("li", null, "Responde las preguntas del diagnóstico. Si no sabes una respuesta, elige «No sé»."),
        h("li", null, "Recibe las cinco causas más probables con su porcentaje, las recomendaciones y la explicación de por qué el sistema llegó a ellas.")),
      h("p", null, "El sistema usa el conocimiento de un técnico: con cada respuesta ajusta qué tan probable es cada falla. El resultado es una orientación: no reemplaza la revisión de un técnico y no repara el equipo."),
      h("h2", null, "Qué datos se guardan"),
      h("p", null, "Tu nombre, correo, la contraseña (solo como un código irreversible), tus equipos y el historial de tus diagnósticos. Nadie más que tú puede ver tus diagnósticos."),
      h("h2", null, "Accesibilidad"),
      h("ul", { class: "limpia" }, h("li", null, "Se puede usar solo con teclado: Tab avanza, Mayús+Tab retrocede, Enter o Espacio activan, Esc cierra los cuadros de diálogo."),
        h("li", null, "Es compatible con lectores de pantalla, ampliación de texto y los modos claro, oscuro y de contraste alto del sistema."),
        h("li", null, "Los resultados siempre se indican con texto y no solo con color.")),
      h("p", null, "Si encuentras una barrera de accesibilidad, repórtala a la persona responsable del proyecto en tu curso.")));
  return { titulo: "Ayuda y accesibilidad", nodo };
}
