"""Fixtures pytest: carga de app.py con auth.json temporal.
No requiere MariaDB — las rutas que tocan la BD se omiten o se testean por
validaciones previas (permisos, parámetros, path traversal, etc.).
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
API_DIR = ROOT / "api"


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    """Carga api/app.py con AUTH_FILE, LOG_DIR y BACKUP_DIR redirigidos a tmp."""
    auth_file = tmp_path / "auth.json"
    log_dir = tmp_path / "logs"
    backup_dir = tmp_path / "backups"
    log_dir.mkdir()
    backup_dir.mkdir()

    monkeypatch.setenv("AUTH_FILE", str(auth_file))
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("BACKUP_DIR", str(backup_dir))

    # Evitar que la importación de app.py bloquee intentando conectar a MariaDB:
    # parcheamos mysql.connector.connect antes de importar el módulo.
    import mysql.connector

    def _fake_connect(*a, **kw):
        raise mysql.connector.Error("DB mocked in tests")

    monkeypatch.setattr(mysql.connector, "connect", _fake_connect)

    monkeypatch.syspath_prepend(str(API_DIR))
    if "app" in sys.modules:
        del sys.modules["app"]
    module = importlib.import_module("app")
    yield module
    if "app" in sys.modules:
        del sys.modules["app"]


@pytest.fixture
def client(app_module):
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def auth_admin_sha(app_module):
    """Crea una cuenta admin con hash SHA-256 legacy (sin bcrypt) para testear migración."""
    password = "admin123"
    salt = "s" * 16
    h = app_module._hash_password(password, salt)
    auth = {"admin": {"salt": salt, "hash": h}}
    with open(app_module.AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth, f)
    return password


@pytest.fixture
def auth_admin_bcrypt(app_module):
    password = "AdminPass1!"
    bhash = app_module._hash_bcrypt(password)
    auth = {"admin": {"bcrypt": bhash}}
    with open(app_module.AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(auth, f)
    return password
