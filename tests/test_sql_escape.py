"""Regresión: _sql_escape debe manejar date y datetime sin confundir sus APIs
(`datetime.isoformat(sep=...)` existe; `date.isoformat(sep=...)` NO)."""
from datetime import date, datetime


def test_datetime_usa_separador_espacio(app_module):
    v = datetime(2026, 4, 21, 12, 42, 56)
    assert app_module._sql_escape(v) == "'2026-04-21 12:42:56'"


def test_date_sin_argumentos(app_module):
    v = date(2026, 4, 21)
    assert app_module._sql_escape(v) == "'2026-04-21'"


def test_escape_tipos_varios(app_module):
    assert app_module._sql_escape(None) == "NULL"
    assert app_module._sql_escape(True) == "1"
    assert app_module._sql_escape(False) == "0"
    assert app_module._sql_escape(42) == "42"
    assert app_module._sql_escape("it's") == "'it''s'"
    assert app_module._sql_escape(b"\x00\xff") == "0x00ff"
