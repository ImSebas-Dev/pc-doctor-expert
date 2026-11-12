"""Crea el esquema, carga el conocimiento y el primer administrador si la base está vacía (idempotente).

Uso manual:  DATABASE_URL=... ADMIN_CORREO=... ADMIN_CLAVE=... python -m sistema.instalador
"""
import logging
import os
from pathlib import Path

import psycopg

from . import claves
from .validacion import CORREO

log = logging.getLogger("pcdoctor.instalador")
SQL = Path(__file__).resolve().parent.parent / "sql"


def instalar(url: str, correo: str | None, clave: str | None) -> None:
    with psycopg.connect(url, connect_timeout=15) as cx:
        if cx.execute("SELECT to_regclass('kb.hipotesis')").fetchone()[0] is None:
            for archivo in sorted(SQL.glob("0*.sql")):
                cx.execute(archivo.read_text(encoding="utf-8"))
            log.info("Esquema y conocimiento cargados")
        if cx.execute("SELECT 1 FROM tx.usuario u JOIN tx.rol r ON r.id = u.rol_id WHERE r.nombre = 'administrador'").fetchone():
            return
        if not (correo and clave and CORREO.match(correo)) or claves.error_de_politica(clave, correo):
            log.warning("No hay administrador: define ADMIN_CORREO y ADMIN_CLAVE (mínimo %s caracteres) y reinicia el servicio", claves.MIN_LARGO)
            return
        cx.execute("INSERT INTO tx.usuario(nombre,correo,clave_hash,rol_id) VALUES ('Administrador',%s,%s,(SELECT id FROM tx.rol WHERE nombre='administrador'))",
                   (correo.lower(), claves.crear_hash(clave)))
        log.info("Administrador creado")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    instalar(os.environ["DATABASE_URL"], os.environ.get("ADMIN_CORREO"), os.environ.get("ADMIN_CLAVE"))
