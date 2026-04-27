#!/usr/bin/env python3
"""Inicializa la base de datos local sin Docker.

Crea (si no existe) la base 'censo_animales', carga el dump principal y
aplica todas las migraciones de db/migrations/ en orden alfabético.

Uso:
    python init_db_local.py            # crea + carga + migraciones
    python init_db_local.py --solo-migraciones
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parent
DUMP = ROOT / "db" / "censo_animales.sql"
MIGRACIONES = sorted((ROOT / "db" / "migrations").glob("*.sql"))

CFG_SERVIDOR = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "123"),
}
DB_NAME = os.environ.get("DB_NAME", "censo_animales")


def _ejecutar_script(cur, sql: str) -> None:
    """Ejecuta un script SQL multi-sentencia tolerando DELIMITER opcional."""
    sentencias: list[str] = []
    delim = ";"
    buf: list[str] = []
    for linea in sql.splitlines():
        s = linea.strip()
        if s.upper().startswith("DELIMITER "):
            if buf:
                sentencias.append("\n".join(buf))
                buf = []
            delim = s.split(None, 1)[1].strip()
            continue
        buf.append(linea)
        if linea.rstrip().endswith(delim):
            texto = "\n".join(buf)
            if delim != ";":
                texto = texto.rsplit(delim, 1)[0]
            sentencias.append(texto)
            buf = []
            if delim != ";" and s == delim:
                delim = ";"
    if buf:
        sentencias.append("\n".join(buf))

    for stmt in sentencias:
        if not stmt.strip() or stmt.strip().startswith("--"):
            continue
        try:
            cur.execute(stmt)
            while cur.nextset():
                pass
        except mysql.connector.Error as e:
            # Tolerar errores idempotentes en migraciones
            if e.errno in (1050, 1060, 1061, 1062, 1091, 1146):
                print(f"  [skip] {e.msg[:80]}")
            else:
                print(f"  [ERROR] {e}")
                raise


def crear_bd_y_cargar() -> None:
    print(f"[1/3] Conectando a MariaDB/MySQL en {CFG_SERVIDOR['host']}:{CFG_SERVIDOR['port']}…")
    conn = mysql.connector.connect(**CFG_SERVIDOR)
    cur = conn.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cur.execute(f"USE `{DB_NAME}`")

    # ¿Ya hay tablas?
    cur.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s",
        (DB_NAME,),
    )
    n = cur.fetchone()[0]
    if n > 0:
        print(f"  [ok] base '{DB_NAME}' ya tiene {n} tablas, no se recarga el dump")
    elif DUMP.is_file():
        print(f"[2/3] Cargando dump {DUMP.name}…")
        _ejecutar_script(cur, DUMP.read_text(encoding="utf-8"))
        conn.commit()
        print("  [ok] dump cargado")
    else:
        print(f"  [aviso] no se encontró {DUMP}")

    cur.close()
    conn.close()


def aplicar_migraciones() -> None:
    print(f"[3/3] Aplicando {len(MIGRACIONES)} migraciones…")
    conn = mysql.connector.connect(database=DB_NAME, **CFG_SERVIDOR)
    cur = conn.cursor()
    for m in MIGRACIONES:
        print(f"  → {m.name}")
        _ejecutar_script(cur, m.read_text(encoding="utf-8"))
        conn.commit()
    cur.close()
    conn.close()
    print("  [ok] migraciones aplicadas")


def main() -> None:
    if "--solo-migraciones" not in sys.argv:
        crear_bd_y_cargar()
    aplicar_migraciones()
    print("\nListo. Ejecuta 'python run_local.py' para arrancar la aplicación.")


if __name__ == "__main__":
    main()
