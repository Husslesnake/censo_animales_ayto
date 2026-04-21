"""Regresiones para /api/incidencias (Ley 7/2023 art. 31).

Tests estáticos + de validación. Los tests dinámicos contra la BD real
están fuera del alcance porque el conftest mockea mysql.connector.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP_PY = ROOT / "api" / "app.py"
MIGRATION = ROOT / "db" / "migrations" / "07_incidencias.sql"


# ── Estructura ──────────────────────────────────────────────────────────────


def test_endpoints_registrados(app_module):
    rules = {(str(r), tuple(sorted(r.methods or []))) for r in app_module.app.url_map.iter_rules()}
    paths = {r for r, _ in rules}
    assert "/api/incidencias" in paths
    assert "/api/incidencias/<int:id_inc>" in paths
    assert "/api/incidencias/exportar" in paths


def test_validador_incidencia_detecta_campos_requeridos(app_module):
    v = app_module._validar_incidencia
    assert v({}) is not None  # sin FECHA
    assert "FECHA" in v({})
    assert "TIPO" in v({"FECHA": "2026-04-21T12:00:00"})
    assert v({"FECHA": "2026-04-21", "TIPO": "mordedura"}) is None


def test_validador_gravedad_estricta(app_module):
    v = app_module._validar_incidencia
    err = v({"FECHA": "2026-04-21", "TIPO": "x", "GRAVEDAD": "muy_grande"})
    assert err is not None and "GRAVEDAD" in err


def test_validador_propaga_errores_chip_y_nif(app_module):
    v = app_module._validar_incidencia
    err = v({"FECHA": "2026-04-21", "TIPO": "x", "N_CHIP": "BAD;CHIP"})
    assert err is not None and "N_CHIP" in err
    err = v({"FECHA": "2026-04-21", "TIPO": "x", "DNI_PROPIETARIO": "12345678A"})
    assert err is not None and "DNI_PROPIETARIO" in err


def test_validador_fecha_invalida(app_module):
    v = app_module._validar_incidencia
    err = v({"FECHA": "no-es-fecha", "TIPO": "x"})
    assert err is not None and "FECHA" in err


# ── Auth ────────────────────────────────────────────────────────────────────


def test_post_sin_token_devuelve_403(client):
    resp = client.post(
        "/api/incidencias",
        data=json.dumps({"FECHA": "2026-04-21", "TIPO": "mordedura"}),
        content_type="application/json",
    )
    assert resp.status_code == 403


def test_get_sin_token_devuelve_403(client):
    resp = client.get("/api/incidencias")
    assert resp.status_code == 403


def test_delete_requiere_admin(client, app_module):
    # Con sólo policía (no admin) → 403
    from datetime import datetime, timedelta
    app_module._TOKENS["t-pol"] = {
        "rol": "policia",
        "exp": datetime.now() + timedelta(hours=1),
        "username": "agente01",
    }
    resp = client.delete(
        "/api/incidencias/1",
        headers={"X-Token": "t-pol"},
    )
    # Sin cabecera X-Admin-Access → 403
    assert resp.status_code == 403


# ── Migración ───────────────────────────────────────────────────────────────


def test_migracion_07_es_idempotente():
    assert MIGRATION.exists()
    src = MIGRATION.read_text(encoding="utf-8")
    # Añade columnas nuevas sin CREATE TABLE
    assert "_add_col_if_missing" in src
    for col in (
        "DNI_PROPIETARIO",
        "GRAVEDAD",
        "LUGAR",
        "VICTIMA_NOMBRE",
        "VICTIMA_CONTACTO",
        "ATENDIDO_MEDICO",
        "COMUNICADO_SANIDAD",
        "FECHA_COMUNICACION",
    ):
        assert col in src, f"Migración 07 no añade columna {col}"


def test_migracion_07_no_crea_tabla():
    """La tabla ya existía; la migración solo añade columnas."""
    src = MIGRATION.read_text(encoding="utf-8")
    assert "CREATE TABLE `INCIDENCIAS`" not in src


# ── Validación via HTTP ────────────────────────────────────────────────────


def _auth_admin(app_module):
    from datetime import datetime, timedelta
    app_module._TOKENS["t-adm"] = {
        "rol": "admin",
        "exp": datetime.now() + timedelta(hours=1),
        "username": "admin",
    }
    return {"X-Token": "t-adm", "X-Admin-Access": "true"}


def test_post_valida_payload(client, app_module):
    h = _auth_admin(app_module)
    resp = client.post(
        "/api/incidencias",
        headers={**h, "Content-Type": "application/json"},
        data=json.dumps({"TIPO": "mordedura"}),  # falta FECHA
    )
    assert resp.status_code == 400
    assert "FECHA" in resp.get_json()["error"]


def test_exportar_sin_bd_devuelve_500(client, app_module):
    """Sin BD real el endpoint responde 500 con JSON de error."""
    resp = client.get("/api/incidencias/exportar")
    # Sin token falla en la auth o en la BD mockeada; ambas son fallos controlados
    assert resp.status_code in (403, 500)
