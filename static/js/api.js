/* Cliente de la API: cabecera CSRF, errores tipados y aviso de sesión vencida. */
export const sesion = { usuario: null, csrf: "" };

export class ErrorApi extends Error {
  constructor(estado, mensaje, campo) { super(mensaje); this.estado = estado; this.campo = campo; }
}

export async function api(metodo, ruta, datos) {
  let r;
  try {
    r = await fetch(ruta, {
      method: metodo, credentials: "same-origin",
      headers: datos === undefined ? {} : { "Content-Type": "application/json", "X-CSRF-Token": sesion.csrf },
      body: datos === undefined ? undefined : JSON.stringify(datos),
    });
  } catch {
    throw new ErrorApi(0, "No hay conexión con el servidor. Revisa tu Internet e inténtalo de nuevo.");
  }
  const cuerpo = r.status === 204 ? {} : await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && sesion.usuario) document.dispatchEvent(new CustomEvent("sesion-vencida"));
    throw new ErrorApi(r.status, cuerpo.error || "Ocurrió un error. Inténtalo de nuevo.", cuerpo.campo);
  }
  if (cuerpo.csrf) sesion.csrf = cuerpo.csrf;
  return cuerpo;
}
