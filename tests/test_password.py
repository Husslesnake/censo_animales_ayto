"""Tests unitarios de la política y hashing de contraseñas."""


def test_fortaleza_rechaza_corta(app_module):
    assert app_module._validar_fortaleza_password("Ab1!") is not None


def test_fortaleza_rechaza_sin_mayuscula(app_module):
    assert "mayúscula" in app_module._validar_fortaleza_password("abcdefg1!").lower()


def test_fortaleza_rechaza_sin_minuscula(app_module):
    assert "minúscula" in app_module._validar_fortaleza_password("ABCDEFG1!").lower()


def test_fortaleza_rechaza_sin_numero(app_module):
    assert "número" in app_module._validar_fortaleza_password("Abcdefgh!").lower()


def test_fortaleza_rechaza_sin_especial(app_module):
    assert "especial" in app_module._validar_fortaleza_password("Abcdefg1").lower()


def test_fortaleza_acepta_valida(app_module):
    assert app_module._validar_fortaleza_password("Abcdef1!") is None


def test_bcrypt_verifica_correcto(app_module):
    h = app_module._hash_bcrypt("Secreto1!")
    assert app_module._verificar_password("Secreto1!", {"bcrypt": h}) is True
    assert app_module._verificar_password("otraPass", {"bcrypt": h}) is False


def test_verifica_legacy_sha256(app_module):
    salt = "saltytest1234567"
    pwd = "legacy-pass"
    h = app_module._hash_password(pwd, salt)
    entrada = {"salt": salt, "hash": h}
    assert app_module._verificar_password(pwd, entrada) is True
    assert app_module._verificar_password("mal", entrada) is False


def test_migracion_sha256_a_bcrypt(app_module):
    salt = "saltytest1234567"
    pwd = "legacy-pass"
    entrada = {"salt": salt, "hash": app_module._hash_password(pwd, salt)}
    assert app_module._migrar_a_bcrypt(entrada, pwd) is True
    assert "bcrypt" in entrada
    assert "hash" not in entrada
    assert "salt" not in entrada
    # Segunda llamada no hace nada
    assert app_module._migrar_a_bcrypt(entrada, pwd) is False


def test_password_caducada(app_module):
    from datetime import datetime, timedelta
    antigua = (datetime.now() - timedelta(days=400)).isoformat()
    reciente = (datetime.now() - timedelta(days=30)).isoformat()
    assert app_module._password_caducada({"password_changed": antigua}) is True
    assert app_module._password_caducada({"password_changed": reciente}) is False
    # Sin fecha → no caducada (cuenta nueva)
    assert app_module._password_caducada({}) is False
