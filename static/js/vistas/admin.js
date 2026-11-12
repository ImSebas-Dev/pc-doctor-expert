/* Administración (solo rol administrador): usuarios, conocimiento, reglas y pruebas (RF-01, RF-04). */
import { api } from "../api.js";
import { anunciar, campo, dialogo, fecha, formulario, h, mensaje, tabla } from "../ui.js";

const SECCIONES = [["/admin/usuarios", "Usuarios"], ["/admin/conocimiento", "Conocimiento"], ["/admin/reglas", "Reglas"], ["/admin/pruebas", "Pruebas"]];
const marco = (actual, titulo, ...contenido) => h("div", null, h("h1", null, titulo),
  h("nav", { "aria-label": "Administración", class: "sub-nav" }, SECCIONES.map(([r, t]) => h("a", { href: `#${r}`, "aria-current": r === actual ? "page" : null }, t))), ...contenido);

export async function usuarios() {
  const { usuarios: lista, yo } = await api("get", "/api/admin/usuarios");
  const filas = lista.map((u) => {
    const rol = campo({ nombre: "rol", etiqueta: `Rol de ${u.nombre}`, tipo: "select", valor: u.rol, requerido: false, opciones: [{ valor: "usuario", texto: "Usuario" }, { valor: "administrador", texto: "Administrador" }] });
    const activo = campo({ nombre: "activo", etiqueta: `Cuenta activa de ${u.nombre}`, tipo: "casilla", valor: u.activo });
    const btn = h("button", { class: "boton", type: "button", onclick: async () => {
      btn.disabled = true;
      try { await api("patch", `/api/admin/usuarios/${u.id}`, { rol: rol.valor(), activo: activo.valor() }); anunciar(`Usuario ${u.nombre} actualizado`); rol.limpiar(); }
      catch (e) { rol.fallar(e.message); anunciar(e.message); } finally { btn.disabled = false; } } }, "Guardar", h("span", { class: "solo-lector" }, ` cambios de ${u.nombre}`));
    return [u.nombre + (u.id === yo ? " (tú)" : ""), u.correo, fecha(u.creado_en), rol.raiz, activo.raiz, btn];
  });
  return { titulo: "Administración · Usuarios", nodo: marco("/admin/usuarios", "Administración", h("h2", null, "Usuarios"), tabla("Usuarios registrados", ["Nombre", "Correo", "Alta", "Rol", "Estado", "Acción"], filas)) };
}

export async function conocimiento() {
  const { hipotesis } = await api("get", "/api/admin/hipotesis");
  const cuerpo = h("div");
  const editar = (x) => {
    const campos = [campo({ nombre: "nombre", etiqueta: "Nombre de la falla", valor: x.nombre, maximo: 80 }),
      campo({ nombre: "causa_probable", etiqueta: "Causa probable", tipo: "textarea", valor: x.causa_probable, maximo: 500, filas: 4 }),
      campo({ nombre: "recomendaciones", etiqueta: "Recomendaciones", tipo: "textarea", valor: x.recomendaciones.join("\n"), ayuda: "Una recomendación por línea (mínimo 2, máximo 8).", filas: 6 }),
      campo({ nombre: "validada", etiqueta: "Validada por el experto humano", tipo: "casilla", valor: x.validada })];
    const d = dialogo(`Editar ${x.codigo}`, formulario({ campos, boton: "Guardar", extra: h("button", { type: "button", class: "boton", onclick: () => d.close() }, "Cancelar"),
      enviar: async (v) => { await api("put", `/api/admin/hipotesis/${x.codigo}`, { ...v, recomendaciones: v.recomendaciones.split("\n").map((l) => l.trim()).filter(Boolean) });
        d.close(); Object.assign(x, v, { recomendaciones: v.recomendaciones.split("\n").map((l) => l.trim()).filter(Boolean), causa_probable: v.causa_probable }); pintar(); anunciar(`${x.codigo} actualizada`); } }));
  };
  const pintar = () => cuerpo.replaceChildren(tabla("Fallas y conocimiento asociado", ["Código", "Nombre", "Categoría", "Confianza", "Validada", "Acción"],
    hipotesis.map((x) => [x.codigo, x.nombre, x.categoria, x.confianza, x.validada ? h("span", { class: "insignia exito" }, "Sí") : h("span", { class: "insignia neutra" }, "Pendiente"),
      h("button", { class: "boton", type: "button", onclick: () => editar(x) }, "Editar", h("span", { class: "solo-lector" }, ` ${x.codigo} ${x.nombre}`))])));
  pintar();
  return { titulo: "Administración · Conocimiento", nodo: marco("/admin/conocimiento", "Administración", h("h2", null, "Conocimiento"),
    mensaje("info", "Los cambios se aplican de inmediato al motor de inferencia. Marca una falla como validada cuando el experto humano haya revisado su causa y recomendaciones."), cuerpo) };
}

export async function reglas() {
  const { reglas: lista } = await api("get", "/api/admin/reglas");
  return { titulo: "Administración · Reglas", nodo: marco("/admin/reglas", "Administración", h("h2", null, "Reglas SI–ENTONCES"),
    tabla(`Reglas de la base de conocimiento (${lista.length})`, ["Código", "Tipo", "Regla", "Confianza"], lista.map((r) => [r.codigo, r.tipo === "diagnostico" ? "Diagnóstico" : "Derivación", r.texto, r.confianza ?? "—"]))) };
}

export async function pruebas() {
  const cuerpo = h("div");
  const pintar = (lista) => {
    const ejecutadas = lista.filter((p) => p.aprobado !== null);
    const ok = ejecutadas.filter((p) => p.aprobado).length;
    cuerpo.replaceChildren(ejecutadas.length ? mensaje(ok === ejecutadas.length ? "exito" : "advertencia", `${ok} de ${ejecutadas.length} casos de prueba aprobados.`) : mensaje("info", "Aún no se han ejecutado las pruebas."),
      tabla("Resultado por caso de prueba", ["Caso", "Falla esperada", "Falla obtenida", "Resultado"], lista.map((p) => [p.caso, p.esperada, p.obtenida ?? "—", p.aprobado === null ? "Sin ejecutar" : p.aprobado ? "Aprobado" : "Fallido"])));
  };
  pintar((await api("get", "/api/admin/pruebas")).pruebas);
  const btn = h("button", { class: "boton primario", type: "button", onclick: async () => {
    btn.disabled = true;
    try { pintar((await api("post", "/api/admin/pruebas", {})).pruebas); anunciar("Pruebas ejecutadas"); } catch (e) { cuerpo.prepend(mensaje("error", e.message)); } finally { btn.disabled = false; } } }, "Ejecutar todas las pruebas");
  return { titulo: "Administración · Pruebas", nodo: marco("/admin/pruebas", "Administración", h("h2", null, "Casos de prueba del experto"),
    h("p", { class: "subtitulo" }, "Cada caso simula a un usuario que confirma los síntomas de una falla y comprueba que el motor la identifique."), h("div", { class: "acciones" }, btn), cuerpo) };
}
