"""Tests de endpoints /api/admin/backups/* (validaciones sin tocar MariaDB)."""


def _dev_headers():
    return {"X-Device-Id": "test-device-0001"}


def _login_admin(client, password):
    res = client.post(
        "/api/auth/login",
        headers={**_dev_headers(), "X-Admin-Access": "true"},
        json={"password": password},
    )
    return res.get_json().get("token")


def test_listar_sin_auth_prohibido(client):
    res = client.get("/api/admin/backups")
    assert res.status_code == 403


def test_listar_sin_backups_vacio(client, auth_admin_bcrypt):
    token = _login_admin(client, auth_admin_bcrypt)
    assert token
    res = client.get("/api/admin/backups", headers={"X-Token": token})
    data = res.get_json()
    assert data.get("ok") is True
    assert data.get("backups") == []
    assert data.get("retencion_dias") == 30


def test_descargar_rechaza_path_traversal(client, auth_admin_bcrypt):
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.get("/api/admin/backups/..%2F..%2Fetc%2Fpasswd",
                     headers={"X-Token": token})
    # Flask normaliza %2F → / y el router no matchea o el endpoint rechaza
    assert res.status_code in (400, 404)


def test_descargar_rechaza_nombre_invalido(client, auth_admin_bcrypt):
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.get("/api/admin/backups/malicioso.txt",
                     headers={"X-Token": token})
    assert res.status_code == 400


def test_descargar_inexistente_404(client, auth_admin_bcrypt):
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.get("/api/admin/backups/backup_2099-01-01_000000.sql.gz",
                     headers={"X-Token": token})
    assert res.status_code == 404


def test_listar_backups_existentes(client, app_module, auth_admin_bcrypt):
    import gzip
    ruta = app_module.BACKUP_DIR / "backup_2026-01-01_120000.sql.gz"
    with gzip.open(ruta, "wt", encoding="utf-8") as f:
        f.write("-- dummy backup\nSET NAMES utf8mb4;\n")
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.get("/api/admin/backups", headers={"X-Token": token})
    data = res.get_json()
    assert data.get("ok") is True
    nombres = [b["nombre"] for b in data["backups"]]
    assert "backup_2026-01-01_120000.sql.gz" in nombres


def test_eliminar_backup_existente(client, app_module, auth_admin_bcrypt):
    import gzip
    ruta = app_module.BACKUP_DIR / "backup_2026-02-02_120000.sql.gz"
    with gzip.open(ruta, "wt", encoding="utf-8") as f:
        f.write("-- dummy\n")
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.delete("/api/admin/backups/backup_2026-02-02_120000.sql.gz",
                        headers={"X-Token": token})
    assert res.get_json().get("ok") is True
    assert not ruta.exists()


def test_restaurar_sin_auth_prohibido(client):
    res = client.post("/api/admin/backups/backup_x.sql.gz/restaurar")
    assert res.status_code == 403


def test_restaurar_requiere_confirmacion(client, app_module, auth_admin_bcrypt):
    import gzip
    ruta = app_module.BACKUP_DIR / "backup_2026-03-01_120000.sql.gz"
    with gzip.open(ruta, "wt", encoding="utf-8") as f:
        f.write("-- dummy\nSET NAMES utf8mb4;\n")
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.post("/api/admin/backups/backup_2026-03-01_120000.sql.gz/restaurar",
                      headers={"X-Token": token},
                      json={})  # sin confirmación
    assert res.status_code == 400
    assert "confirmaci" in (res.get_json().get("error") or "").lower()


def test_restaurar_rechaza_nombre_invalido(client, auth_admin_bcrypt):
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.post("/api/admin/backups/malicioso.txt/restaurar",
                      headers={"X-Token": token},
                      json={"confirmacion": "RESTAURAR"})
    assert res.status_code == 400


def test_restaurar_archivo_inexistente_404(client, auth_admin_bcrypt):
    token = _login_admin(client, auth_admin_bcrypt)
    res = client.post("/api/admin/backups/backup_2099-01-01_000000.sql.gz/restaurar",
                      headers={"X-Token": token},
                      json={"confirmacion": "RESTAURAR"})
    assert res.status_code == 404


def test_sql_escape_seguro(app_module):
    assert app_module._sql_escape(None) == "NULL"
    assert app_module._sql_escape(42) == "42"
    assert app_module._sql_escape(True) == "1"
    # Comilla simple debe escaparse doblándose
    assert app_module._sql_escape("O'Brien") == "'O''Brien'"
    # Backslash debe duplicarse
    assert app_module._sql_escape("a\\b") == "'a\\\\b'"
