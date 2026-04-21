"""Regresiones para recordatorios por email."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
MIGRATION = ROOT / "db" / "migrations" / "08_propietarios_email.sql"


# ── Configuración / validación ──────────────────────────────────────────────


def test_migracion_08_idempotente():
    assert MIGRATION.exists()
    src = MIGRATION.read_text(encoding="utf-8")
    assert "information_schema.COLUMNS" in src
    assert "ADD COLUMN `EMAIL`" in src
    assert "RECORDATORIOS_ENVIADOS" in src


def test_validar_email(app_module):
    v = app_module._validar_email
    assert v("a@b.co")
    assert v("  a@b.co  ".strip())
    assert not v("")
    assert not v("sin-arroba")
    assert not v("a@b")


def test_smtp_no_configurado_por_defecto(app_module):
    # En tests no hay SMTP_HOST → _smtp_configurado debe ser False.
    # (Los fixtures no setean SMTP_*.)
    assert app_module._smtp_configurado() is False


def test_enviar_email_sin_smtp_devuelve_no_smtp(app_module):
    ok, err = app_module._enviar_email("a@b.co", "s", "b")
    assert ok is False
    assert err == "no-smtp"


def test_enviar_email_valida_destinatario(app_module, monkeypatch):
    # Forzar SMTP configurado para pasar el primer guard
    monkeypatch.setattr(app_module, "SMTP_HOST", "localhost")
    monkeypatch.setattr(app_module, "SMTP_FROM", "x@y.z")
    ok, err = app_module._enviar_email("no-es-email", "s", "b")
    assert ok is False
    assert err == "email_invalido"


def test_formato_email_recordatorio(app_module):
    subject, body = app_module._formatear_email_recordatorio({
        "dni": "12345678Z",
        "email": "a@b.co",
        "nombre": "Ana Test",
        "items": [
            {"tipo": "seguro_rc", "referencia": "CHIP1 — Mapfre/POL",
             "vence": "2026-05-01", "dias_restantes": 10},
            {"tipo": "vacuna_antirrabica", "referencia": "CHIP2 (Firu)",
             "vence": "2026-04-25", "dias_restantes": 4},
        ],
    })
    assert "Navalcarnero" in subject
    assert "Ana Test" in body
    assert "Vacuna antirrábica" in body
    assert "Seguro de responsabilidad civil" in body
    assert "Ley 7/2023" in body


def test_job_sin_db_no_lanza(app_module):
    # _recopilar_recordatorios captura excepciones de BD y devuelve []
    res = app_module._enviar_recordatorios_job(dry_run=True)
    assert res["total_destinatarios"] == 0
    assert res["enviados"] == 0


# ── Endpoint admin ──────────────────────────────────────────────────────────


def test_endpoint_requiere_admin(client):
    resp = client.post("/api/admin/enviar_recordatorios")
    assert resp.status_code == 403


def test_endpoint_dry_run_admin(client):
    resp = client.post(
        "/api/admin/enviar_recordatorios?dry_run=1",
        headers={"X-Admin-Access": "true"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "smtp_configurado" in data


def test_endpoint_registrado(app_module):
    rules = {str(r) for r in app_module.app.url_map.iter_rules()}
    assert "/api/admin/enviar_recordatorios" in rules


def test_scheduler_job_registrado():
    """El job recordatorios_vencimientos debe estar en el código del scheduler."""
    src = (ROOT / "api" / "app.py").read_text(encoding="utf-8")
    assert "recordatorios_vencimientos" in src
    assert "_enviar_recordatorios_job" in src
