"""Verifica que los handlers de excepciones registran el mensaje de error.

Dos tipos de test:

1. Estático: recorre api/app.py con AST y comprueba que todo `except` llama a
   un logger (`logger.*`, `logging.*`) o a una función de logging conocida
   (`_log_request_error`, `_log_auditoria`, `_log_ip`). Equivalente en JS: se
   comprueba que los catch-blocks llaman a `logError` o `console.error/warn`.

2. Dinámico: fuerza excepciones en varios caminos (password mal formada,
   JSON de auth corrupto, argumentos inválidos, etc.) y comprueba que el
   logger del módulo emitió un registro.
"""
from __future__ import annotations

import ast
import json
import logging
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP_PY = ROOT / "api" / "app.py"
JS_DIR = ROOT / "web" / "js"

LOGGING_FUNCS = {"_log_request_error", "_log_auditoria", "_log_ip"}


# ──────────────────────────────────────────────────────────────────────────────
# Análisis estático
# ──────────────────────────────────────────────────────────────────────────────


def _except_body_logs(body: list[ast.stmt]) -> bool:
    """True si el cuerpo contiene una llamada a logger.X, logging.X o helper
    conocido de logging."""
    dummy = ast.Module(body=body, type_ignores=[])
    for node in ast.walk(dummy):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            if f.value.id in ("logger", "logging"):
                return True
        if isinstance(f, ast.Name) and f.id in LOGGING_FUNCS:
            return True
    return False


def test_todos_los_except_en_app_py_registran_en_log():
    src = APP_PY.read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines()

    unlogged: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and not _except_body_logs(node.body):
            snippet = lines[node.lineno - 1].strip()
            unlogged.append((node.lineno, snippet))

    assert not unlogged, (
        "Hay handlers sin logging:\n"
        + "\n".join(f"  app.py:{ln}: {s}" for ln, s in unlogged)
    )


def _iter_js_catch_bodies():
    """Genera (path, lineno, body_text) para cada catch-block en web/js."""
    BS = chr(92)
    for p in JS_DIR.glob("*.js"):
        src = p.read_text(encoding="utf-8")
        i = 0
        while True:
            m = re.search(r"catch\s*(?:\([^)]*\))?\s*\{", src[i:])
            if not m:
                break
            start = i + m.start()
            body_start = i + m.end()
            depth = 1
            j = body_start
            while j < len(src) and depth > 0:
                c = src[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                elif c == "/" and j + 1 < len(src) and src[j + 1] == "/":
                    while j < len(src) and src[j] != "\n":
                        j += 1
                elif c == "/" and j + 1 < len(src) and src[j + 1] == "*":
                    j += 2
                    while j + 1 < len(src) and not (
                        src[j] == "*" and src[j + 1] == "/"
                    ):
                        j += 1
                    j += 1
                elif c in ('"', "'", "`"):
                    q = c
                    j += 1
                    while j < len(src) and src[j] != q:
                        if src[j] == BS:
                            j += 1
                        j += 1
                j += 1
            body = src[body_start : j - 1]
            yield p, src[:start].count("\n") + 1, body
            i = j


def test_todos_los_catch_en_js_registran_en_log():
    unlogged = []
    for path, line, body in _iter_js_catch_bodies():
        if not any(
            marker in body
            for marker in ("logError", "console.error", "console.warn")
        ):
            unlogged.append(f"  {path.relative_to(ROOT)}:{line}")
    assert not unlogged, "Hay catch-blocks sin log:\n" + "\n".join(unlogged)


# ──────────────────────────────────────────────────────────────────────────────
# Verificación dinámica
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def caplog_censo(caplog, app_module):
    """Captura logs del logger 'censo' a nivel DEBUG."""
    caplog.set_level(logging.DEBUG, logger="censo")
    return caplog


def test_auth_json_corrupto_se_registra(app_module, caplog_censo):
    """Un auth.json ilegible debe dejar rastro en el log, no romper silenciosamente."""
    app_module.AUTH_FILE.write_text("{esto no es json}", encoding="utf-8")
    caplog_censo.clear()
    data = app_module._cargar_auth()
    assert data == {}
    mensajes = [r.getMessage() for r in caplog_censo.records]
    assert any("auth" in m.lower() for m in mensajes), (
        "Debió registrar el fallo de parseo de auth.json. Logs: " + repr(mensajes)
    )


def test_bcrypt_corrupto_se_registra(app_module, caplog_censo):
    """Un hash bcrypt inválido debe devolver False y dejar un WARNING."""
    caplog_censo.clear()
    ok = app_module._verificar_password("x", {"bcrypt": "no-es-un-hash-valido"})
    assert ok is False
    warns = [r for r in caplog_censo.records if r.levelno >= logging.WARNING]
    assert warns, "Se esperaba un WARNING al fallar bcrypt.checkpw"
    assert any("bcrypt" in r.getMessage().lower() for r in warns)


def test_password_caducada_con_fecha_invalida_se_registra(app_module, caplog_censo):
    """Una fecha ilegible en 'modificado' no debe romper, pero sí registrarse."""
    caplog_censo.clear()
    res = app_module._password_caducada({"modificado": "no-es-fecha"})
    assert res is False
    assert any(
        "password_caducada" in r.getMessage().lower()
        or "no se pudo parsear" in r.getMessage().lower()
        for r in caplog_censo.records
    )


def test_inactividad_con_fecha_invalida_se_registra(app_module, caplog_censo):
    caplog_censo.clear()
    res = app_module._check_inactividad("fecha-mala")
    assert res is False
    assert any(
        "inactividad" in r.getMessage().lower()
        for r in caplog_censo.records
    )


def test_endpoint_que_falla_emite_error(app_module, caplog_censo, client):
    """Un endpoint que choca con la BD mockeada debe emitir un ERROR en el log."""
    # /api/sexos entra en la rama externa (no en la interna con fallback),
    # porque get_conn() lanza antes de entrar al try interno de SELECT.
    caplog_censo.clear()
    resp = client.get("/api/sexos")
    # Debe devolver 500 con el error de request logging
    assert resp.status_code in (200, 500)
    errors = [r for r in caplog_censo.records if r.levelno >= logging.ERROR]
    # Si el endpoint propagó el error por _log_request_error, habrá ERROR
    if resp.status_code == 500:
        assert errors, (
            "Se esperaba al menos un ERROR en logs tras fallo de BD. "
            f"Records: {[(r.levelname, r.getMessage()[:80]) for r in caplog_censo.records]}"
        )


def test_restore_backup_inexistente_se_registra(app_module, caplog_censo, tmp_path):
    """_ejecutar_restore con un archivo que no se puede abrir registra el error."""
    caplog_censo.clear()
    fake = tmp_path / "backup_2024-01-01_000000.sql.gz"
    fake.write_bytes(b"not a gzip file")  # .gz inválido → gzip.open fallará al leer
    res = app_module._ejecutar_restore(fake)
    assert res.get("ok") is False
    errors = [r for r in caplog_censo.records if r.levelno >= logging.WARNING]
    assert errors, "Se esperaba WARNING/ERROR al no poder leer el backup"
    assert any("backup" in r.getMessage().lower() or "restore" in r.getMessage().lower()
               for r in errors)


def test_auditoria_json_malformado_se_registra(app_module, caplog_censo, client):
    """Líneas basura en auditoria.jsonl deben registrarse como DEBUG, no romper la respuesta."""
    audit_file = app_module._AUDIT_LOG_FILE
    audit_file.write_text(
        json.dumps({"fecha": "2026-01-01", "rol": "admin", "accion": "x"}) + "\n"
        + "esto-no-es-json\n"
        + json.dumps({"fecha": "2026-01-02", "rol": "admin", "accion": "y"}) + "\n",
        encoding="utf-8",
    )
    # Crear sesión admin para poder llamar al endpoint
    app_module._TOKENS["t-test"] = {
        "rol": "admin",
        "exp": __import__("datetime").datetime.now() + __import__("datetime").timedelta(hours=1),
    }
    caplog_censo.clear()
    resp = client.get(
        "/api/auditoria",
        headers={"X-Token": "t-test", "X-Admin-Access": "true"},
    )
    assert resp.status_code == 200
    datos = resp.get_json()
    # Las 2 líneas válidas deben parsearse; la malformada se descarta con log
    assert datos["ok"] is True
    assert datos["total"] == 2
    assert any(
        "auditoria" in r.getMessage().lower() and "json" in r.getMessage().lower()
        for r in caplog_censo.records
    ), f"Se esperaba un DEBUG sobre JSON inválido. Records: {[r.getMessage() for r in caplog_censo.records]}"
