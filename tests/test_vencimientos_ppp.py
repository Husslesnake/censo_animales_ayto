"""Regresiones para /api/vencimientos_licencias_ppp (RD 287/2002 art. 3.4).

Verifica:
- El endpoint está registrado.
- Acepta los query params documentados (dias, incluir_caducadas).
- Calcula el vencimiento como FECHA_EXPEDICION + 5 años (SQL DATE_ADD INTERVAL 5 YEAR).
- La migración 06 crea el índice idempotentemente.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_PY = ROOT / "api" / "app.py"
MIGRATION = ROOT / "db" / "migrations" / "06_licencia_ppp_indice.sql"


def test_endpoint_registrado(app_module):
    rules = {str(r) for r in app_module.app.url_map.iter_rules()}
    assert "/api/vencimientos_licencias_ppp" in rules


def test_calcula_5_anios_desde_expedicion():
    src = APP_PY.read_text(encoding="utf-8")
    # DATE_ADD(FECHA_EXPEDICION_LICENCIA, INTERVAL 5 YEAR) debe aparecer en el endpoint
    m = re.search(
        r"def vencimientos_licencias_ppp\(\):.*?(?=\n@app\.route|\ndef\s+\w)",
        src,
        re.S,
    )
    assert m, "No se encontró la función vencimientos_licencias_ppp"
    body = m.group(0)
    assert "INTERVAL 5 YEAR" in body, (
        "El endpoint debe usar INTERVAL 5 YEAR (RD 287/2002 art. 3.4)"
    )
    assert "FECHA_EXPEDICION_LICENCIA" in body


def test_acepta_incluir_caducadas():
    src = APP_PY.read_text(encoding="utf-8")
    m = re.search(
        r"def vencimientos_licencias_ppp\(\):.*?(?=\n@app\.route|\ndef\s+\w)",
        src,
        re.S,
    )
    assert m
    assert "incluir_caducadas" in m.group(0), (
        "Debe soportar ?incluir_caducadas=1 para reportes de infracción"
    )


def test_migracion_06_idempotente():
    assert MIGRATION.exists()
    src = MIGRATION.read_text(encoding="utf-8")
    assert "information_schema.STATISTICS" in src
    assert "idx_licencias_fecha_exp" in src


def test_endpoint_responde_500_sin_db(client):
    """Sin BD real, el endpoint debe devolver 500 con error — no 404/crash."""
    resp = client.get("/api/vencimientos_licencias_ppp?dias=30")
    assert resp.status_code == 500
    data = resp.get_json()
    assert data["ok"] is False
