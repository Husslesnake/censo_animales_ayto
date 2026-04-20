"""Tests de rutas /api/auth/* sin base de datos."""
import json


def _dev_headers():
    return {"X-Device-Id": "test-device-0001"}


def test_estado_sin_configurar(client):
    res = client.get("/api/auth/estado", headers=_dev_headers())
    data = res.get_json()
    assert res.status_code == 200
    assert data.get("configurado") is False


def test_login_admin_bcrypt_ok(client, app_module, auth_admin_bcrypt):
    res = client.post(
        "/api/auth/login",
        headers={**_dev_headers(), "X-Admin-Access": "true"},
        json={"password": auth_admin_bcrypt},
    )
    data = res.get_json()
    assert data.get("ok") is True
    assert data.get("rol") == "admin"
    assert data.get("token")


def test_login_admin_password_erronea(client, app_module, auth_admin_bcrypt):
    res = client.post(
        "/api/auth/login",
        headers={**_dev_headers(), "X-Admin-Access": "true"},
        json={"password": "incorrecta"},
    )
    data = res.get_json()
    assert data.get("ok") is False


def test_login_migra_sha256_a_bcrypt(client, app_module, auth_admin_sha):
    # Login con SHA legacy → debe aceptar y migrar a bcrypt en disco
    res = client.post(
        "/api/auth/login",
        headers={**_dev_headers(), "X-Admin-Access": "true"},
        json={"password": auth_admin_sha},
    )
    assert res.get_json().get("ok") is True
    with open(app_module.AUTH_FILE, "r", encoding="utf-8") as f:
        auth = json.load(f)
    assert "bcrypt" in auth["admin"]
    assert "hash" not in auth["admin"]
    assert "salt" not in auth["admin"]


def test_rate_limit_por_usuario_bloquea(client, app_module, auth_admin_bcrypt):
    # Tras _LOGIN_MAX_INTENTOS_USER fallos, el usuario debe quedar bloqueado.
    maximo = app_module._LOGIN_MAX_INTENTOS_USER
    for _ in range(maximo + 1):
        client.post(
            "/api/auth/login",
            headers={**_dev_headers(), "X-Admin-Access": "true"},
            json={"password": "mala"},
        )
    # Incluso con la contraseña correcta ahora debe fallar por bloqueo o seguir rechazando
    res = client.post(
        "/api/auth/login",
        headers={**_dev_headers(), "X-Admin-Access": "true"},
        json={"password": auth_admin_bcrypt},
    )
    data = res.get_json()
    # El login correcto no debería tener éxito con el IP/user bloqueados
    assert data.get("ok") is False


def test_verificar_token_invalido(client):
    res = client.get("/api/auth/verificar", headers={"X-Token": "token-que-no-existe"})
    data = res.get_json()
    assert data.get("ok") is False


def test_verificar_token_valido(client, app_module, auth_admin_bcrypt):
    res = client.post(
        "/api/auth/login",
        headers={**_dev_headers(), "X-Admin-Access": "true"},
        json={"password": auth_admin_bcrypt},
    )
    token = res.get_json().get("token")
    assert token
    res2 = client.get("/api/auth/verificar", headers={"X-Token": token})
    data = res2.get_json()
    assert data.get("ok") is True
    assert data.get("rol") == "admin"


def test_recuperar_genera_respuesta_generica(client, app_module):
    res = client.post(
        "/api/auth/recuperar",
        headers=_dev_headers(),
        json={"username": "usuario.inexistente", "motivo": "test"},
    )
    data = res.get_json()
    # Respuesta genérica (para no revelar si existe)
    assert data.get("ok") is True
