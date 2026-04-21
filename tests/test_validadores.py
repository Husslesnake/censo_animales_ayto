"""Regresiones para _validar_nif y _validar_chip (backend validation)."""
from __future__ import annotations

import json


# ── _validar_nif ────────────────────────────────────────────────────────────


def test_nif_valido(app_module):
    # 12345678 % 23 = 14 → Z
    assert app_module._validar_nif("12345678Z") is None


def test_nif_letra_incorrecta(app_module):
    err = app_module._validar_nif("12345678A")
    assert err is not None
    assert "Letra" in err or "letra" in err


def test_nif_longitud_invalida(app_module):
    assert app_module._validar_nif("1234567Z") is not None
    assert app_module._validar_nif("123456789Z") is not None


def test_nif_acepta_minusculas_y_espacios(app_module):
    # Normalización: trim + upper
    assert app_module._validar_nif("  12345678z  ") is None


def test_nie_valido(app_module):
    # X1234567 → 01234567, 01234567 % 23 = 16 → L
    assert app_module._validar_nif("X1234567L") is None


def test_nie_letra_incorrecta(app_module):
    assert app_module._validar_nif("X1234567A") is not None


def test_nif_vacio(app_module):
    assert app_module._validar_nif("") is not None
    assert app_module._validar_nif(None) is not None  # type: ignore[arg-type]


def test_nif_caracteres_no_numericos(app_module):
    assert app_module._validar_nif("ABCDEFGHZ") is not None


# ── _validar_chip ───────────────────────────────────────────────────────────


def test_chip_laxo_acepta_legacy(app_module):
    assert app_module._validar_chip("CHIP0001") is None
    assert app_module._validar_chip("A1B2-C3D4_E") is None


def test_chip_laxo_rechaza_vacio_o_corto(app_module):
    assert app_module._validar_chip("") is not None
    assert app_module._validar_chip("ABC") is not None


def test_chip_laxo_rechaza_caracteres_raros(app_module):
    assert app_module._validar_chip("CHIP 0001") is not None  # espacio
    assert app_module._validar_chip("CHIP;DROP") is not None  # SQL injection attempt


def test_chip_iso_estricto_requiere_15_digitos(app_module):
    assert app_module._validar_chip("941000012345678", iso_estricto=True) is None
    assert app_module._validar_chip("CHIP0001", iso_estricto=True) is not None
    assert app_module._validar_chip("12345", iso_estricto=True) is not None
    assert app_module._validar_chip("123456789012345A", iso_estricto=True) is not None


# ── Integración: endpoints rechazan datos inválidos ────────────────────────


def test_post_propietarios_rechaza_nif_invalido(client):
    resp = client.post(
        "/api/propietarios",
        data=json.dumps({"DNI": "12345678A", "NOMBRE": "Test"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["ok"] is False
    assert "DNI" in data["error"]


def test_post_animales_rechaza_chip_con_espacios(client):
    resp = client.post(
        "/api/animales",
        data=json.dumps({"N_CHIP": "CHIP MALO", "DNI_PROPIETARIO": "12345678Z"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "Chip" in resp.get_json()["error"]


def test_post_animales_rechaza_nif_propietario_invalido(client):
    resp = client.post(
        "/api/animales",
        data=json.dumps({"N_CHIP": "CHIP0001", "DNI_PROPIETARIO": "99999999A"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "DNI" in resp.get_json()["error"]


def test_post_seguros_rechaza_chip_invalido(client):
    resp = client.post(
        "/api/seguros",
        data=json.dumps({
            "N_CHIP": "BAD;CHIP",
            "SEGURO_COMPANIA": "Mapfre",
            "SEGURO_POLIZA": "POL-1",
        }),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "Chip" in resp.get_json()["error"]
