"""Tests del cálculo de diff antes/después para auditoría."""
from datetime import date, datetime


def test_diff_detecta_cambios(app_module):
    antes = {"nombre": "Rex", "edad": 5, "esterilizado": 0}
    despues = {"nombre": "Rex", "edad": 5, "esterilizado": 1}
    d = app_module._diff_dict(antes, despues)
    assert list(d.keys()) == ["esterilizado"]
    assert d["esterilizado"] == {"antes": 0, "despues": 1}


def test_diff_ignora_campos_iguales(app_module):
    antes = {"a": 1, "b": 2}
    assert app_module._diff_dict(antes, antes) == {}


def test_diff_detecta_nuevos_campos(app_module):
    d = app_module._diff_dict({"a": 1}, {"a": 1, "b": 2})
    assert "b" in d
    assert d["b"]["antes"] is None
    assert d["b"]["despues"] == 2


def test_diff_normaliza_datetime(app_module):
    fecha_a = datetime(2024, 1, 1, 12, 0, 0)
    fecha_b = datetime(2024, 1, 1, 12, 0, 0)
    # Mismos valores después de normalización
    assert app_module._diff_dict({"f": fecha_a}, {"f": fecha_b}) == {}
    # Distintos
    fecha_c = datetime(2025, 1, 1, 12, 0, 0)
    d = app_module._diff_dict({"f": fecha_a}, {"f": fecha_c})
    assert "f" in d
    assert d["f"]["antes"] == fecha_a.isoformat()
    assert d["f"]["despues"] == fecha_c.isoformat()


def test_diff_con_snapshot_none(app_module):
    # Robustez: un snapshot None (p.ej. animal borrado) debe devolver dict válido
    assert app_module._diff_dict(None, {"a": 1}) == {"a": {"antes": None, "despues": 1}}
    assert app_module._diff_dict({"a": 1}, None) == {"a": {"antes": 1, "despues": None}}
