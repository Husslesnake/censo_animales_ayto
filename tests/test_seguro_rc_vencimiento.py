"""Regresiones para el vencimiento de la póliza RC (Ley 7/2023 art. 30).

Verifica:
- El schema base declara la columna FECHA_VENCIMIENTO_RC.
- La migración 05 es idempotente y añade columna + índice.
- El INSERT de /api/seguros incluye FECHA_VENCIMIENTO_RC.
- El SELECT de /api/seguros proyecta FECHA_VENCIMIENTO_RC.
- Existe el endpoint /api/vencimientos_seguros registrado.
- El formulario HTML tiene el input obligatorio.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "db" / "censo_animales.sql"
MIGRATION = ROOT / "db" / "migrations" / "05_seguro_rc_vencimiento.sql"
APP_PY = ROOT / "api" / "app.py"
FORM = ROOT / "web" / "pages" / "seguros.html"


def test_schema_base_tiene_columna_vencimiento():
    src = SCHEMA.read_text(encoding="utf-8")
    m = re.search(r"CREATE TABLE `SEGUROS`.*?\) ENGINE", src, re.S)
    assert m, "No se encontró CREATE TABLE SEGUROS"
    assert "FECHA_VENCIMIENTO_RC" in m.group(0), (
        "La tabla SEGUROS debe declarar FECHA_VENCIMIENTO_RC"
    )


def test_migracion_05_existe_y_es_idempotente():
    assert MIGRATION.exists(), "Falta db/migrations/05_seguro_rc_vencimiento.sql"
    src = MIGRATION.read_text(encoding="utf-8")
    # Debe consultar information_schema antes de ALTER para ser idempotente
    assert "information_schema.COLUMNS" in src
    assert "ADD COLUMN `FECHA_VENCIMIENTO_RC`" in src
    # También debe crear índice condicional
    assert "idx_seguros_vencimiento" in src


def test_insert_seguros_incluye_vencimiento():
    src = APP_PY.read_text(encoding="utf-8")
    # Buscar el INSERT dentro de insertar_seguro
    m = re.search(
        r"INSERT INTO SEGUROS[^)]*FECHA_VENCIMIENTO_RC[^)]*\)\s*\"\s*\"VALUES[^)]*\)",
        src,
    )
    assert m, "El INSERT de /api/seguros no incluye FECHA_VENCIMIENTO_RC"


def test_select_seguros_proyecta_vencimiento():
    src = APP_PY.read_text(encoding="utf-8")
    # El SELECT de listar_seguros debe proyectar s.FECHA_VENCIMIENTO_RC
    assert "s.FECHA_VENCIMIENTO_RC" in src, (
        "El SELECT de /api/seguros debe incluir s.FECHA_VENCIMIENTO_RC"
    )


def test_endpoint_vencimientos_seguros_registrado(app_module):
    rules = {str(r) for r in app_module.app.url_map.iter_rules()}
    assert "/api/vencimientos_seguros" in rules, (
        f"Falta /api/vencimientos_seguros en url_map. Rules: {rules}"
    )


def test_formulario_tiene_input_vencimiento_obligatorio():
    html = FORM.read_text(encoding="utf-8")
    # Input tipo date, name correcto, required
    m = re.search(
        r'<input\s+[^>]*name="FECHA_VENCIMIENTO_RC"[^>]*>',
        html,
        re.S,
    )
    assert m, "Falta input FECHA_VENCIMIENTO_RC en seguros.html"
    tag = m.group(0)
    assert 'type="date"' in tag, "El input debe ser type=date"
    assert "required" in tag, "El input debe ser required (Ley 7/2023 art. 30)"
