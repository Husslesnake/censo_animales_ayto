import atexit
import gzip
import hashlib
import json
import logging
import os
import secrets
import traceback
from datetime import date, datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import bcrypt
import mysql.connector
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# Configuración

app = Flask(__name__)
CORS(app)

# ── Logging ──────────────────────────────────────────────────────
LOG_DIR = Path(os.environ.get("LOG_DIR", "logs"))
LOG_DIR.mkdir(exist_ok=True)


def _make_logger():
    log = logging.getLogger("censo")
    log.setLevel(logging.DEBUG)
    if log.handlers:
        return log
    # Rotación diaria — genera logs/log_YYYY-MM-DD.txt
    fh = TimedRotatingFileHandler(
        LOG_DIR / "log.txt",
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    fh.suffix = "%Y-%m-%d"
    fh.namer = lambda name: str(LOG_DIR / f"log_{Path(name).suffix.lstrip('.')}.txt")
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh.setFormatter(fmt)
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(ch)
    return log


logger = _make_logger()


def _log_startup_message():
    """Registra un mensaje de inicio de la aplicación."""
    logger.info("=" * 80)
    logger.info("APPLICATION STARTUP - Timestamp: %s", datetime.now().isoformat())
    logger.info("=" * 80)


def _cleanup_old_logs():
    """
    Elimina automáticamente archivos de log con más de 30 días
    si no contienen ningún error (ERROR, CRITICAL).
    """
    try:
        now = datetime.now()
        cutoff_date = now - timedelta(days=30)
        
        for log_file in LOG_DIR.glob("log_*.txt"):
            # Obtener fecha de modificación
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # Si el archivo es más antiguo de 30 días, verificar si tiene errores
            if mtime < cutoff_date:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    
                    # Verificar si tiene errores o problemas críticos
                    has_errors = any(
                        marker in content 
                        for marker in ["ERROR", "CRITICAL", "EXCEPTION", "Traceback"]
                    )
                    
                    # Si no tiene errores, eliminar
                    if not has_errors:
                        log_file.unlink()
                        logger.info("Cleaned up old error-free log: %s", log_file.name)
                    else:
                        logger.debug("Kept log with errors: %s", log_file.name)
                        
                except Exception as e:
                    logger.warning(
                        "Error processing log file %s: %s", log_file.name, str(e)
                    )
            else:
                logger.debug("Log file %s is within 30-day retention: %s", 
                           log_file.name, mtime.isoformat())
    
    except Exception as e:
        logger.error("Error during log cleanup: %s\n%s", str(e), traceback.format_exc())


# Registrar startup y limpiar logs al importar el módulo
_log_startup_message()
_cleanup_old_logs()


# ── Autenticación basada en IP ────────────────────────────────────────────────
# Admin → accede por el puerto 8080 (solo localhost); nginx añade X-Admin-Access: true.
# Empleados → acceden por el puerto 80 (público); nginx deja X-Admin-Access vacío.

AUTH_FILE = Path(os.environ.get("AUTH_FILE", "auth.json"))

# ── Logger de accesos por IP ──────────────────────────────────────────────────
_IP_LOG_FILE = LOG_DIR / "log-ip.txt"

# Crear el fichero al arrancar si no existe (garantiza que el directorio y fichero están listos)
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not _IP_LOG_FILE.exists():
        _IP_LOG_FILE.write_text(
            f"# Registro de accesos por IP — creado {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            encoding="utf-8"
        )
except Exception as _e:
    logger.warning("No se pudo crear log-ip.txt: %s", _e)

def _log_ip(ip: str, rol: str, evento: str, exito: bool):
    """Registra en log-ip.txt cada intento de acceso con su IP, rol y resultado."""
    linea = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"{'OK  ' if exito else 'FAIL'} "
        f"ip={ip:<20} rol={rol:<10} evento={evento}\n"
    )
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_IP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception as e:
        logger.warning("No se pudo escribir en log-ip.txt: %s", e)


# ── Logger de auditoría (cambios en la BD) ────────────────────────────────────
# Cada línea es un objeto JSON independiente (.jsonl) para facilitar su lectura.
_AUDIT_LOG_FILE = LOG_DIR / "auditoria.jsonl"

try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not _AUDIT_LOG_FILE.exists():
        _AUDIT_LOG_FILE.touch()
except Exception as _e:
    logger.warning("No se pudo crear auditoria.jsonl: %s", _e)


def _usuario_desde_token() -> tuple[str, str]:
    """Devuelve (rol, usuario) del token actual. Usuario es:
       - 'admin' para admin
       - username real para policía
       - device_id (abreviado) para empleado
       - 'anónimo' si no hay token válido.
    """
    token = request.headers.get("X-Token", "")
    payload = _TOKENS.get(token)
    if not payload or datetime.now() > payload.get("exp", datetime.now()):
        # Si no hay token, intentamos inferir por cabecera de admin/empleado
        if _es_admin_request():
            return ("admin", "admin")
        dev = _get_device_id()
        return ("empleado", dev[:12] if dev else "anónimo")
    rol = payload.get("rol", "desconocido")
    if rol == "policia":
        return (rol, payload.get("username", "policia"))
    if rol == "admin":
        return (rol, "admin")
    # empleado → preferir username (cuenta nominal); fallback a device_id (legado)
    username = payload.get("username")
    if username:
        return (rol, username)
    dev = _get_device_id()
    return (rol, dev[:12] if dev else "empleado")


def _log_auditoria(accion: str, detalle: dict | None = None, exito: bool = True):
    """Registra un cambio en la base de datos en logs/auditoria.jsonl.
    Campos: fecha, ip, rol, usuario, accion, exito, detalle.
    Si no hay contexto de petición (p.ej. tarea programada), registra rol='sistema'.
    """
    try:
        try:
            rol, usuario = _usuario_desde_token()
            ip = _get_client_ip()
        except Exception as _ctx_err:
            logger.debug("AUDIT: sin contexto de petición (%s)", _ctx_err)
            rol, usuario, ip = "sistema", "scheduler", "—"
        entrada = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip": ip,
            "rol": rol,
            "usuario": usuario,
            "accion": accion,
            "exito": bool(exito),
            "detalle": detalle or {},
        }
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(_AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("No se pudo escribir en auditoria.jsonl: %s", e)


def _diff_dict(antes: dict | None, despues: dict | None) -> dict:
    """Compara dos snapshots y devuelve sólo los campos cuyo valor ha cambiado.
    Formato: {campo: {"antes": x, "despues": y}}.
    """
    antes = antes or {}
    despues = despues or {}
    claves = set(antes.keys()) | set(despues.keys())
    cambios = {}
    for k in claves:
        va, vd = antes.get(k), despues.get(k)
        # Normalizar datetime/date a iso para comparación estable
        if isinstance(va, (datetime, date)):
            va = va.isoformat()
        if isinstance(vd, (datetime, date)):
            vd = vd.isoformat()
        if va != vd:
            cambios[k] = {"antes": va, "despues": vd}
    return cambios


def _snapshot_animal(conn, chip: str) -> dict | None:
    """Captura el estado actual de un animal (+ póliza de seguro) para diff."""
    try:
        c = conn.cursor(buffered=True)
        c.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ANIMALES' "
            "ORDER BY ORDINAL_POSITION"
        )
        cols = [r[0] for r in c.fetchall()]
        chip_col = "N_CHIP" if "N_CHIP" in cols else ("NUMERO_CHIP" if "NUMERO_CHIP" in cols else cols[0])
        c.execute(f"SELECT * FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        row = c.fetchone()
        if not row:
            return None
        snap = {cols[i]: row[i] for i in range(len(cols))}
        # Añadir póliza vigente
        try:
            c2 = conn.cursor(buffered=True)
            c2.execute(f"SELECT SEGURO_POLIZA FROM SEGUROS WHERE `{chip_col}` = %s", (chip,))
            r2 = c2.fetchone()
            snap["SEGURO_POLIZA"] = r2[0] if r2 else None
        except Exception as e:
            logger.debug("snapshot_animal: póliza no disponible para chip=%s: %s", chip, e)
        return snap
    except Exception as e:
        logger.warning("snapshot_animal fallo para chip=%s: %s", chip, e)
        return None


# Tokens de sesión en memoria: {token: {"rol": "admin"|"empleado", "exp": datetime}}
_TOKENS: dict = {}
_TOKEN_TTL_HOURS = 12
_TOKEN_TTL_RECORDAR_DIAS = 365

# Inactividad: usuarios bloqueados si no han accedido en este número de días
_INACTIVIDAD_DIAS = 180


def _check_inactividad(ultimo_acceso_iso: str | None) -> bool:
    """Devuelve True si el usuario lleva más de _INACTIVIDAD_DIAS sin acceder."""
    if not ultimo_acceso_iso:
        return False  # Cuenta nueva sin acceso previo → no bloquear
    try:
        ultimo = datetime.fromisoformat(ultimo_acceso_iso)
        return (datetime.now() - ultimo).days > _INACTIVIDAD_DIAS
    except Exception as e:
        logger.debug("INACTIVIDAD: no se pudo parsear %r: %s", ultimo_acceso_iso, e)
        return False


def _cargar_tokens_persistidos():
    """Al arrancar, carga en _TOKENS los tokens de larga duración guardados en auth.json."""
    auth = _cargar_auth()
    ahora = datetime.now()
    cargados = 0
    for token, datos in auth.get("tokens_recordar", {}).items():
        try:
            exp = datetime.fromisoformat(datos["exp"])
            if exp > ahora:
                payload = {"rol": datos["rol"], "exp": exp, "persistido": True}
                if "username" in datos:
                    payload["username"] = datos["username"]
                _TOKENS[token] = payload
                cargados += 1
        except Exception as e:
            logger.warning("Token persistido inválido ignorado (%s…): %s", token[:8], e)
    if cargados:
        logger.info("AUTH: %d token(s) de larga duración restaurados desde auth.json", cargados)


def _guardar_token_persistido(token: str, rol: str, exp: datetime, **extra):
    """Persiste un token de larga duración en auth.json."""
    auth = _cargar_auth()
    tokens = auth.get("tokens_recordar", {})
    # Limpiar tokens expirados antes de escribir
    ahora = datetime.now()
    tokens = {t: d for t, d in tokens.items()
              if datetime.fromisoformat(d.get("exp", "2000-01-01")) > ahora}
    entry = {"rol": rol, "exp": exp.isoformat()}
    entry.update(extra)
    tokens[token] = entry
    auth["tokens_recordar"] = tokens
    _guardar_auth(auth)


def _eliminar_token_persistido(token: str):
    """Elimina un token de larga duración de auth.json."""
    auth = _cargar_auth()
    tokens = auth.get("tokens_recordar", {})
    if token in tokens:
        del tokens[token]
        auth["tokens_recordar"] = tokens
        _guardar_auth(auth)


def _get_client_ip() -> str:
    """Obtiene la IP real del cliente, respetando cabeceras de proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.remote_addr or "0.0.0.0"


def _es_admin_request() -> bool:
    """True si la petición llega por el puerto 8080 (admin).
    Nginx pone X-Admin-Access: true solo en ese server block; en el puerto 80 lo fuerza a vacío."""
    return request.headers.get("X-Admin-Access", "") == "true"


def _get_device_id() -> str:
    """Obtiene el identificador único de dispositivo enviado por el navegador."""
    return request.headers.get("X-Device-Id", "").strip()


def _hash_password(password: str, salt: str) -> str:
    """SHA-256 con sal — solo para verificar credenciales legacy. Usar _hash_bcrypt para nuevas."""
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def _hash_bcrypt(password: str) -> str:
    """Hash bcrypt con coste 12. Devuelve la cadena lista para almacenar."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def _verificar_password(password: str, entrada: dict) -> bool:
    """Verifica una contraseña contra una entrada que puede usar bcrypt o SHA-256 legacy."""
    bhash = entrada.get("bcrypt")
    if bhash:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), bhash.encode("utf-8"))
        except Exception as e:
            logger.warning("AUTH: bcrypt.checkpw falló: %s", e)
            return False
    # Legacy SHA-256
    salt = entrada.get("salt")
    h    = entrada.get("hash")
    if not salt or not h:
        return False
    return _hash_password(password, salt) == h


def _migrar_a_bcrypt(entrada: dict, password: str) -> bool:
    """Si la entrada usa SHA-256, la actualiza in-place a bcrypt. Devuelve True si migró."""
    if entrada.get("bcrypt"):
        return False
    entrada["bcrypt"] = _hash_bcrypt(password)
    entrada.pop("hash", None)
    entrada.pop("salt", None)
    return True


# ── Rate-limit y bloqueo de cuenta por intentos fallidos ─────────────────────
# {clave: [timestamps]} — limpiamos al pasar la ventana
_LOGIN_INTENTOS: dict[str, list[datetime]] = {}
_LOGIN_VENTANA_SEG       = 300   # 5 min
_LOGIN_MAX_INTENTOS_IP   = 20    # por IP en la ventana
_LOGIN_MAX_INTENTOS_USER = 5     # por usuario antes de bloquear cuenta


def _registrar_intento_fallido(clave: str) -> int:
    """Registra un intento y devuelve el nº de intentos en la ventana."""
    ahora = datetime.now()
    lista = _LOGIN_INTENTOS.setdefault(clave, [])
    lista.append(ahora)
    # Purgar antiguos
    limite = ahora - timedelta(seconds=_LOGIN_VENTANA_SEG)
    _LOGIN_INTENTOS[clave] = [t for t in lista if t > limite]
    return len(_LOGIN_INTENTOS[clave])


def _intentos_en_ventana(clave: str) -> int:
    ahora = datetime.now()
    limite = ahora - timedelta(seconds=_LOGIN_VENTANA_SEG)
    lista = [t for t in _LOGIN_INTENTOS.get(clave, []) if t > limite]
    _LOGIN_INTENTOS[clave] = lista
    return len(lista)


def _limpiar_intentos(clave: str):
    _LOGIN_INTENTOS.pop(clave, None)


# Caducidad de contraseña: empleados deben renovar tras este número de días
_PASSWORD_MAX_DIAS = 365


def _validar_fortaleza_password(password: str) -> str | None:
    """Comprueba requisitos de seguridad. Devuelve None si es válida o un mensaje de error."""
    if len(password) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if not any(c.islower() for c in password):
        return "Debe incluir al menos una letra minúscula."
    if not any(c.isupper() for c in password):
        return "Debe incluir al menos una letra mayúscula."
    if not any(c.isdigit() for c in password):
        return "Debe incluir al menos un número."
    if not any(not c.isalnum() for c in password):
        return "Debe incluir al menos un carácter especial (!@#$%…)."
    return None


def _password_caducada(entrada: dict) -> bool:
    """True si la contraseña fue cambiada hace más de _PASSWORD_MAX_DIAS días."""
    ref = entrada.get("password_changed") or entrada.get("modificado") or entrada.get("creado")
    if not ref:
        return False
    try:
        return (datetime.now() - datetime.fromisoformat(ref)).days > _PASSWORD_MAX_DIAS
    except Exception as e:
        logger.debug("PASSWORD_CADUCADA: no se pudo parsear %r: %s", ref, e)
        return False


def _cargar_auth() -> dict:
    """Carga el fichero auth.json. Devuelve {} si no existe.
    Migra automáticamente el formato antiguo (hash/salt plano) al nuevo (ips dict).
    """
    if AUTH_FILE.exists():
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("AUTH: no se pudo leer %s: %s", AUTH_FILE, e)
            return {}
    else:
        return {}

    # Migración: formato antiguo usaba "hash"/"salt" en raíz o en "ips".
    # Nuevo formato: auth["admin"] para el admin, auth["devices"] para empleados.
    migrado = False

    # Formato muy antiguo: hash en raíz
    if "hash" in data and "salt" in data and "admin" not in data:
        data["admin"] = {
            "hash": data.pop("hash"),
            "salt": data.pop("salt"),
            "rol": "admin",
            "creado": data.pop("creado", datetime.now().isoformat()),
        }
        data.pop("modificado", None)
        data.pop("empleado", None)
        migrado = True

    # Formato intermedio: hash en "ips"
    if "ips" in data and "admin" not in data:
        for _entrada in data["ips"].values():
            if _entrada.get("rol") == "admin":
                data["admin"] = _entrada
                break
        data.pop("ips", None)
        migrado = True

    if migrado:
        try:
            AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            logger.info("AUTH: auth.json migrado al nuevo formato")
        except Exception as e:
            logger.warning("AUTH: No se pudo guardar la migración: %s", e)

    return data


def _guardar_auth(data: dict):
    """Persiste auth.json."""
    AUTH_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _crear_token(rol: str, recordar: bool = False, **extra) -> str:
    """Genera un token aleatorio y lo registra.
    Si recordar=True, TTL de 1 año y se persiste en auth.json para sobrevivir reinicios.
    **extra permite adjuntar campos adicionales al payload (p.ej. username para policía)."""
    token = secrets.token_hex(32)
    if recordar:
        exp = datetime.now() + timedelta(days=_TOKEN_TTL_RECORDAR_DIAS)
        payload = {"rol": rol, "exp": exp, "persistido": True, **extra}
        _TOKENS[token] = payload
        _guardar_token_persistido(token, rol, exp, **extra)
    else:
        exp = datetime.now() + timedelta(hours=_TOKEN_TTL_HOURS)
        _TOKENS[token] = {"rol": rol, "exp": exp, "persistido": False, **extra}
    return token


def _validar_token(token: str) -> dict | None:
    """Devuelve el payload del token si es válido y no ha expirado.
    Para tokens de policía y empleado, verifica además que la cuenta/dispositivo
    siga activo en auth.json (revocación en sesión activa)."""
    payload = _TOKENS.get(token)
    if not payload:
        return None
    if datetime.now() > payload["exp"]:
        if payload.get("persistido"):
            _eliminar_token_persistido(token)
        del _TOKENS[token]
        return None
    if payload["rol"] == "policia":
        username = payload.get("username")
        if username:
            user = _cargar_auth().get("policia_usuarios", {}).get(username, {})
            if not user.get("activo", False):
                if payload.get("persistido"):
                    _eliminar_token_persistido(token)
                del _TOKENS[token]
                return None
    if payload["rol"] == "empleado":
        username = payload.get("username")
        if username:
            emp = _cargar_auth().get("empleado_usuarios", {}).get(username, {})
            if not emp.get("activo", False):
                if payload.get("persistido"):
                    _eliminar_token_persistido(token)
                del _TOKENS[token]
                return None
        else:
            device_id = payload.get("device_id")
            if device_id:
                dev = _cargar_auth().get("devices", {}).get(device_id, {})
                if not dev.get("activo", True):
                    if payload.get("persistido"):
                        _eliminar_token_persistido(token)
                    del _TOKENS[token]
                    return None
    return payload


def _limpiar_tokens_expirados():
    """Elimina tokens caducados del diccionario en memoria y de auth.json."""
    ahora = datetime.now()
    expirados = [t for t, p in list(_TOKENS.items()) if ahora > p["exp"]]
    persistidos_eliminados = 0
    for t in expirados:
        if _TOKENS[t].get("persistido"):
            persistidos_eliminados += 1
        del _TOKENS[t]
    if persistidos_eliminados:
        # Sincronizar auth.json eliminando los que ya no están en _TOKENS
        auth = _cargar_auth()
        tokens_validos = {t: d for t, d in auth.get("tokens_recordar", {}).items()
                         if t in _TOKENS}
        auth["tokens_recordar"] = tokens_validos
        _guardar_auth(auth)


# ── Endpoints de autenticación ────────────────────────────────────────────────

@app.route("/api/auth/estado", methods=["GET"])
def auth_estado():
    """
    Admin  → llega por puerto 8080; nginx pone X-Admin-Access: true.
    Empleado → llega por puerto 80;   nginx fuerza X-Admin-Access a vacío.
    Devuelve es_admin_ip y si ese usuario ya tiene contraseña creada.
    """
    ip = _get_client_ip()
    es_admin = _es_admin_request()
    auth = _cargar_auth()

    if es_admin:
        configurado = bool(auth.get("admin", {}).get("hash"))
    else:
        device_id = _get_device_id()
        configurado = bool(device_id and auth.get("devices", {}).get(device_id, {}).get("hash"))

    return jsonify({
        "ok": True,
        "es_admin_ip": es_admin,
        "configurado": configurado,
        "ip": ip,
    })


@app.route("/api/auth/setup", methods=["POST"])
def auth_setup():
    """
    Crea la contraseña por primera vez.
    Admin  → almacenada en auth["admin"].
    Empleado → almacenada en auth["devices"][device_id].
    """
    ip = _get_client_ip()
    es_admin = _es_admin_request()
    rol = "admin" if es_admin else "empleado"
    auth = _cargar_auth()

    if es_admin:
        if auth.get("admin", {}).get("hash"):
            return jsonify({"ok": False, "error": "Ya tienes contraseña configurada. Usa cambiar contraseña."})
    else:
        device_id = _get_device_id()
        if not device_id:
            return jsonify({"ok": False, "error": "Identificador de dispositivo no recibido."})
        if auth.get("devices", {}).get(device_id, {}).get("hash"):
            return jsonify({"ok": False, "error": "Ya tienes contraseña configurada. Usa cambiar contraseña."})

    data = request.get_json(silent=True) or {}
    password = data.get("password", "").strip()
    min_len = 6 if es_admin else 4
    if len(password) < min_len:
        return jsonify({"ok": False, "error": f"La contraseña debe tener al menos {min_len} caracteres."})

    entrada = {"bcrypt": _hash_bcrypt(password), "rol": rol,
               "creado": datetime.now().isoformat(),
               "password_changed": datetime.now().isoformat()}

    if es_admin:
        auth["admin"] = entrada
    else:
        auth.setdefault("devices", {})[device_id] = entrada

    _guardar_auth(auth)
    logger.info("AUTH: Contraseña creada — %s (rol=%s)", "admin" if es_admin else device_id, rol)
    _log_ip(ip, rol, "setup_password", True)

    token = _crear_token(rol, recordar=True)
    return jsonify({"ok": True, "token": token, "rol": rol})


@app.route("/api/auth/cambiar", methods=["POST"])
def auth_cambiar():
    """
    Cambia la contraseña del usuario actual.
    Requiere token de sesión activo y contraseña actual correcta.
    """
    ip = _get_client_ip()
    token_header = request.headers.get("X-Token", "")
    payload = _validar_token(token_header)
    if not payload:
        return jsonify({"ok": False, "error": "Se requiere sesión activa."})
    rol = payload.get("rol", "empleado")

    auth = _cargar_auth()

    if rol == "admin":
        entrada = auth.get("admin", {})
        bucket, key = "admin", None
    elif rol == "empleado" and payload.get("username"):
        key = payload["username"]
        entrada = auth.get("empleado_usuarios", {}).get(key, {})
        bucket = "empleado_usuarios"
    elif rol == "policia" and payload.get("username"):
        key = payload["username"]
        entrada = auth.get("policia_usuarios", {}).get(key, {})
        bucket = "policia_usuarios"
    else:
        device_id = _get_device_id()
        entrada = auth.get("devices", {}).get(device_id, {}) if device_id else {}
        bucket, key = "devices", device_id

    if not (entrada.get("bcrypt") or entrada.get("hash")):
        return jsonify({"ok": False, "error": "No hay contraseña configurada."})

    data = request.get_json(silent=True) or {}
    actual = data.get("actual", "").strip()
    nueva  = data.get("nueva",  "").strip()

    if not _verificar_password(actual, entrada):
        return jsonify({"ok": False, "error": "La contraseña actual no es correcta."})

    if nueva == actual:
        return jsonify({"ok": False, "error": "La nueva contraseña debe ser distinta de la actual."})

    if bucket in ("empleado_usuarios", "policia_usuarios", "admin"):
        err = _validar_fortaleza_password(nueva)
        if err:
            return jsonify({"ok": False, "error": err})
    else:
        if len(nueva) < 4:
            return jsonify({"ok": False, "error": "La nueva contraseña debe tener al menos 4 caracteres."})

    ahora_iso = datetime.now().isoformat()
    nuevos = {"bcrypt": _hash_bcrypt(nueva), "modificado": ahora_iso, "password_changed": ahora_iso}
    # Limpiar legacy si existían
    nuevos["hash"] = None
    nuevos["salt"] = None
    if bucket == "empleado_usuarios":
        nuevos["must_change"] = False

    if bucket == "admin":
        auth["admin"].update(nuevos)
    else:
        auth[bucket][key].update(nuevos)

    _guardar_auth(auth)
    logger.info("AUTH: Contraseña cambiada — %s (rol=%s)", key or "admin", rol)
    _log_ip(ip, rol, "cambio_password", True)

    extra = {"username": key} if bucket in ("empleado_usuarios", "policia_usuarios") else {}
    token = _crear_token(rol, **extra)
    return jsonify({"ok": True, "token": token, "rol": rol})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """
    Login con contraseña.
    Admin    → busca en auth["admin"].
    Empleado → busca en auth["devices"][device_id].
    Policía  → petición incluye campo "username"; busca en auth["policia_usuarios"].
    """
    ip = _get_client_ip()
    data = request.get_json(silent=True) or {}
    recordar = bool(data.get("recordar", False))

    # ── Rate-limit por IP ─────────────────────────────────────────────────────
    if _intentos_en_ventana("ip:" + ip) >= _LOGIN_MAX_INTENTOS_IP:
        return jsonify({"ok": False, "error": "Demasiados intentos desde tu red. Espera unos minutos."}), 429

    # ── Rama usuario nominal (policía o empleado) ──────────────────────────────
    username = data.get("username", "").strip().lower()
    if username:
        password = data.get("password", "").strip()
        if not password:
            return jsonify({"ok": False, "error": "Introduzca la contraseña."})
        if _intentos_en_ventana("user:" + username) >= _LOGIN_MAX_INTENTOS_USER:
            return jsonify({"ok": False, "error": "Cuenta bloqueada temporalmente por intentos fallidos. Espera 5 minutos o contacte con el administrador."}), 429
        auth = _cargar_auth()

        # Empleado por username (creado por admin)
        emp = auth.get("empleado_usuarios", {}).get(username)
        if emp and (emp.get("bcrypt") or emp.get("hash")):
            if not emp.get("activo", False):
                _log_ip(ip, "empleado", "login", False)
                return jsonify({"ok": False, "error": "Cuenta desactivada. Contacte con el administrador."})
            if _check_inactividad(emp.get("ultimo_acceso")):
                auth["empleado_usuarios"][username]["activo"] = False
                _guardar_auth(auth)
                _log_ip(ip, "empleado", "login_inactividad", False)
                logger.warning("AUTH: Cuenta empleado bloqueada por inactividad — %s", username)
                _log_auditoria("bloqueo_inactividad", {"username": username, "motivo": "sin_acceso_6_meses"})
                return jsonify({"ok": False, "error": "Cuenta bloqueada por inactividad. Contacte con el administrador."})
            if not _verificar_password(password, emp):
                _registrar_intento_fallido("ip:" + ip)
                fallos = _registrar_intento_fallido("user:" + username)
                logger.warning("AUTH: Login empleado fallido — %s desde %s (intento %d)", username, ip, fallos)
                _log_ip(ip, "empleado", "login", False)
                if fallos >= _LOGIN_MAX_INTENTOS_USER:
                    auth["empleado_usuarios"][username]["activo"] = False
                    _guardar_auth(auth)
                    _log_auditoria("bloqueo_intentos", {"username": username, "intentos": fallos})
                    return jsonify({"ok": False, "error": "Cuenta bloqueada por intentos fallidos. Contacte con el administrador."})
                return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos."})
            _limpiar_intentos("user:" + username)
            if _migrar_a_bcrypt(emp, password):
                logger.info("AUTH: Migrada a bcrypt — empleado %s", username)
            auth["empleado_usuarios"][username] = emp
            auth["empleado_usuarios"][username]["ultimo_acceso"] = datetime.now().isoformat()
            _guardar_auth(auth)
            token = _crear_token("empleado", recordar=recordar, username=username)
            logger.info("AUTH: Login empleado exitoso — %s desde %s", username, ip)
            _log_ip(ip, "empleado", "login", True)
            must_change = bool(emp.get("must_change")) or _password_caducada(emp)
            motivo_cambio = None
            if must_change:
                motivo_cambio = "caducada" if _password_caducada(emp) and not emp.get("must_change") else "primer_acceso"
            return jsonify({"ok": True, "token": token, "rol": "empleado",
                            "nombre": emp.get("nombre", username), "recordar": recordar,
                            "must_change": must_change, "motivo_cambio": motivo_cambio})

        user = auth.get("policia_usuarios", {}).get(username)
        if not user or not (user.get("bcrypt") or user.get("hash")):
            _log_ip(ip, "policia", "login", False)
            return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos."})
        if not user.get("activo", False):
            _log_ip(ip, "policia", "login", False)
            return jsonify({"ok": False, "error": "Cuenta desactivada. Contacte con el administrador."})
        if _check_inactividad(user.get("ultimo_acceso")):
            # Bloquear automáticamente y persistir el cambio
            auth["policia_usuarios"][username]["activo"] = False
            _guardar_auth(auth)
            _log_ip(ip, "policia", "login_inactividad", False)
            logger.warning("AUTH: Cuenta policía bloqueada por inactividad — %s", username)
            _log_auditoria("bloqueo_inactividad", {"username": username, "motivo": "sin_acceso_6_meses"})
            return jsonify({"ok": False, "error": "Cuenta bloqueada por inactividad. Contacte con el administrador."})
        if not _verificar_password(password, user):
            _registrar_intento_fallido("ip:" + ip)
            fallos = _registrar_intento_fallido("user:" + username)
            logger.warning("AUTH: Login policía fallido — %s desde %s (intento %d)", username, ip, fallos)
            _log_ip(ip, "policia", "login", False)
            if fallos >= _LOGIN_MAX_INTENTOS_USER:
                auth["policia_usuarios"][username]["activo"] = False
                _guardar_auth(auth)
                _log_auditoria("bloqueo_intentos", {"username": username, "intentos": fallos})
                return jsonify({"ok": False, "error": "Cuenta bloqueada por intentos fallidos. Contacte con el administrador."})
            return jsonify({"ok": False, "error": "Usuario o contraseña incorrectos."})
        _limpiar_intentos("user:" + username)
        if _migrar_a_bcrypt(user, password):
            logger.info("AUTH: Migrada a bcrypt — policía %s", username)
        auth["policia_usuarios"][username] = user
        auth["policia_usuarios"][username]["ultimo_acceso"] = datetime.now().isoformat()
        _guardar_auth(auth)
        token = _crear_token("policia", recordar=recordar, username=username)
        logger.info("AUTH: Login policía exitoso — %s desde %s", username, ip)
        _log_ip(ip, "policia", "login", True)
        return jsonify({"ok": True, "token": token, "rol": "policia",
                        "nombre": user.get("nombre", username), "recordar": recordar})

    # ── Rama admin / empleado ─────────────────────────────────────────────────
    es_admin = _es_admin_request()
    rol = "admin" if es_admin else "empleado"
    password = data.get("password", "").strip()
    recordar = bool(data.get("recordar", False))

    if not password:
        return jsonify({"ok": False, "error": "Introduzca la contraseña."})

    auth = _cargar_auth()

    if es_admin:
        entrada = auth.get("admin", {})
    else:
        device_id = _get_device_id()
        entrada = auth.get("devices", {}).get(device_id, {}) if device_id else {}

    if not (entrada.get("bcrypt") or entrada.get("hash")):
        return jsonify({"ok": False, "error": "configure_primero"})

    clave_intentos = "admin:" + ip if es_admin else "device:" + (_get_device_id() or ip)
    if _intentos_en_ventana(clave_intentos) >= _LOGIN_MAX_INTENTOS_USER:
        return jsonify({"ok": False, "error": "Demasiados intentos. Espera 5 minutos."}), 429

    if not _verificar_password(password, entrada):
        _registrar_intento_fallido("ip:" + ip)
        _registrar_intento_fallido(clave_intentos)
        logger.warning("AUTH: Login fallido desde %s (rol=%s)", ip, rol)
        _log_ip(ip, rol, "login", False)
        return jsonify({"ok": False, "error": "Contraseña incorrecta."})
    _limpiar_intentos(clave_intentos)
    if _migrar_a_bcrypt(entrada, password):
        logger.info("AUTH: Migrada a bcrypt — %s", "admin" if es_admin else "device " + _get_device_id()[:12])
        if es_admin:
            auth["admin"] = entrada
        else:
            auth["devices"][_get_device_id()] = entrada
        _guardar_auth(auth)

    # ── Comprobaciones post-contraseña para empleados (admin no caduca ni se bloquea) ──
    if rol == "empleado":
        # 1. Bloqueo manual tiene prioridad sobre cualquier otra razón
        if not entrada.get("activo", True):
            _log_ip(ip, rol, "login", False)
            return jsonify({"ok": False, "error": "Cuenta desactivada. Contacte con el administrador."})
        # 2. Inactividad → bloquear automáticamente
        if _check_inactividad(entrada.get("ultimo_acceso")):
            auth["devices"][device_id]["activo"] = False
            _guardar_auth(auth)
            _log_ip(ip, rol, "login_inactividad", False)
            logger.warning("AUTH: Dispositivo empleado bloqueado por inactividad — %s", device_id[:12])
            _log_auditoria("bloqueo_inactividad", {"device_id": device_id[:12], "motivo": "sin_acceso_6_meses"})
            return jsonify({"ok": False, "error": "Acceso bloqueado por inactividad. Contacte con el administrador."})
        # 3. Login correcto → actualizar último acceso
        auth["devices"][device_id]["ultimo_acceso"] = datetime.now().isoformat()
        _guardar_auth(auth)

    token = _crear_token(rol, recordar=recordar,
                         **({"device_id": device_id} if rol == "empleado" else {}))
    logger.info("AUTH: Login exitoso desde %s (rol=%s)", ip, rol)
    _log_ip(ip, rol, "login", True)
    return jsonify({"ok": True, "token": token, "rol": rol, "recordar": recordar})


@app.route("/api/auth/setup_empleado", methods=["POST"])
def auth_setup_empleado():
    """
    Configura o cambia la contraseña de empleado.
    Solo puede hacerlo el admin desde la IP local con su token.
    """
    ip = _get_client_ip()
    if not _es_admin_request():
        return jsonify({"ok": False, "error": "Solo se puede configurar desde el servidor local."})

    token = request.headers.get("X-Token", "")
    payload = _validar_token(token)
    if not payload or payload["rol"] != "admin":
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."})

    data = request.get_json(silent=True) or {}
    nueva = data.get("password", "").strip()
    if len(nueva) < 4:
        return jsonify({"ok": False, "error": "La contraseña de empleado debe tener al menos 4 caracteres."})

    auth = _cargar_auth()
    auth["empleado"] = {"bcrypt": _hash_bcrypt(nueva), "modificado": datetime.now().isoformat()}
    _guardar_auth(auth)
    logger.info("AUTH: Contraseña de empleado configurada por admin desde %s", ip)
    _log_ip(ip, "admin", "setup_password_empleado", True)
    return jsonify({"ok": True})


@app.route("/api/auth/verificar", methods=["GET"])
def auth_verificar():
    """Verifica si un token es válido y devuelve el rol."""
    _limpiar_tokens_expirados()
    token = request.headers.get("X-Token", "")
    payload = _validar_token(token)
    if not payload:
        return jsonify({"ok": False, "error": "Sesión expirada o inválida."})
    resp = {"ok": True, "rol": payload["rol"]}
    if payload["rol"] == "empleado" and payload.get("username"):
        emp = _cargar_auth().get("empleado_usuarios", {}).get(payload["username"], {})
        must = bool(emp.get("must_change")) or _password_caducada(emp)
        if must:
            resp["must_change"] = True
            resp["motivo_cambio"] = "caducada" if _password_caducada(emp) and not emp.get("must_change") else "primer_acceso"
    return jsonify(resp)


def _req_admin():
    """Devuelve el payload si el token pertenece a un admin, None en caso contrario."""
    token = request.headers.get("X-Token", "")
    payload = _validar_token(token)
    return payload if payload and payload["rol"] == "admin" else None


# ── Gestión de usuarios policía (solo admin) ──────────────────────────────────

@app.route("/api/auth/policia_usuarios", methods=["GET"])
def policia_usuarios_listar():
    """Lista todas las cuentas de policía. Requiere sesión de administrador."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    auth = _cargar_auth()
    usuarios = auth.get("policia_usuarios", {})
    datos = [
        {"username": u, "nombre": d.get("nombre", u),
         "activo": d.get("activo", False), "creado": d.get("creado", ""),
         "ultimo_acceso": d.get("ultimo_acceso", "")}
        for u, d in usuarios.items()
    ]
    return jsonify({"ok": True, "datos": datos})


@app.route("/api/auth/policia_usuarios", methods=["POST"])
def policia_usuarios_crear():
    """Crea una nueva cuenta de policía. Requiere sesión de administrador."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    nombre   = data.get("nombre", "").strip()
    password = data.get("password", "").strip()
    if not username or not nombre or not password:
        return jsonify({"ok": False, "error": "Usuario, nombre y contraseña son obligatorios."})
    if len(password) < 6:
        return jsonify({"ok": False, "error": "La contraseña debe tener al menos 6 caracteres."})
    auth = _cargar_auth()
    if username in auth.get("policia_usuarios", {}):
        return jsonify({"ok": False, "error": f"El usuario '{username}' ya existe."})
    auth.setdefault("policia_usuarios", {})[username] = {
        "bcrypt": _hash_bcrypt(password), "nombre": nombre,
        "activo": True, "creado": datetime.now().isoformat(),
        "password_changed": datetime.now().isoformat(),
    }
    _guardar_auth(auth)
    logger.info("AUTH: Cuenta policía creada — %s (%s)", username, nombre)
    _log_auditoria("crear_cuenta_policia", {"username": username, "nombre": nombre})
    return jsonify({"ok": True})


@app.route("/api/auth/policia_usuarios/<username>", methods=["PATCH"])
def policia_usuarios_actualizar(username):
    """Activa/desactiva o cambia la contraseña/nombre de una cuenta de policía."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    auth     = _cargar_auth()
    usuarios = auth.get("policia_usuarios", {})
    if username not in usuarios:
        return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
    data = request.get_json(silent=True) or {}
    if "activo" in data:
        usuarios[username]["activo"] = bool(data["activo"])
        if not data["activo"]:
            # Revocación inmediata: eliminar todos sus tokens activos
            to_revoke = [t for t, p in list(_TOKENS.items())
                         if p.get("rol") == "policia" and p.get("username") == username]
            for t in to_revoke:
                if _TOKENS[t].get("persistido"):
                    _eliminar_token_persistido(t)
                del _TOKENS[t]
    if "password" in data:
        nueva = data["password"].strip()
        if len(nueva) < 6:
            return jsonify({"ok": False, "error": "La contraseña debe tener al menos 6 caracteres."})
        ahora = datetime.now().isoformat()
        usuarios[username]["bcrypt"]           = _hash_bcrypt(nueva)
        usuarios[username]["modificado"]       = ahora
        usuarios[username]["password_changed"] = ahora
        usuarios[username].pop("hash", None)
        usuarios[username].pop("salt", None)
    if "nombre" in data:
        usuarios[username]["nombre"] = data["nombre"].strip()
    auth["policia_usuarios"] = usuarios
    _guardar_auth(auth)
    logger.info("AUTH: Cuenta policía actualizada — %s", username)
    campos = []
    if "activo" in data: campos.append("activo=" + ("sí" if data["activo"] else "no"))
    if "password" in data: campos.append("contraseña")
    if "nombre" in data: campos.append("nombre")
    _log_auditoria("actualizar_cuenta_policia", {"username": username, "cambios": campos})
    return jsonify({"ok": True})


@app.route("/api/auth/policia_usuarios/<username>", methods=["DELETE"])
def policia_usuarios_eliminar(username):
    """Elimina permanentemente una cuenta de policía y revoca sus tokens."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    auth     = _cargar_auth()
    usuarios = auth.get("policia_usuarios", {})
    if username not in usuarios:
        return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
    nombre_prev = usuarios[username].get("nombre", username)
    del usuarios[username]
    auth["policia_usuarios"] = usuarios
    to_revoke = [t for t, p in list(_TOKENS.items())
                 if p.get("rol") == "policia" and p.get("username") == username]
    for t in to_revoke:
        if _TOKENS[t].get("persistido"):
            _eliminar_token_persistido(t)
        del _TOKENS[t]
    _guardar_auth(auth)
    logger.info("AUTH: Cuenta policía eliminada — %s", username)
    _log_auditoria("eliminar_cuenta_policia", {"username": username, "nombre": nombre_prev})
    return jsonify({"ok": True})


# ── Gestión de usuarios empleado (solo admin) ─────────────────────────────────

@app.route("/api/auth/recuperar", methods=["POST"])
def auth_recuperar():
    """Empleado u oficial solicita ayuda al admin para recuperar contraseña.
    Solo registra la solicitud — el admin debe resetear manualmente desde el panel.
    Respuesta genérica para no revelar si el usuario existe."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    motivo   = data.get("motivo", "").strip()[:200]
    ip = _get_client_ip()
    if username:
        auth = _cargar_auth()
        existe = (username in auth.get("empleado_usuarios", {})
                  or username in auth.get("policia_usuarios", {}))
        _log_auditoria("solicitud_recuperacion",
                       {"username": username, "existe": existe, "motivo": motivo, "ip": ip})
        logger.info("AUTH: Solicitud de recuperación — %s desde %s", username, ip)
    return jsonify({"ok": True, "mensaje": "Si el usuario existe, el administrador recibirá tu solicitud."})


@app.route("/api/auth/empleado_usuarios", methods=["GET"])
def empleado_usuarios_listar():
    """Lista todas las cuentas de empleado. Requiere sesión de administrador."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    auth = _cargar_auth()
    usuarios = auth.get("empleado_usuarios", {})
    datos = [
        {"username": u, "nombre": d.get("nombre", u),
         "activo": d.get("activo", False), "creado": d.get("creado", ""),
         "ultimo_acceso": d.get("ultimo_acceso", "")}
        for u, d in usuarios.items()
    ]
    return jsonify({"ok": True, "datos": datos})


@app.route("/api/auth/empleado_usuarios", methods=["POST"])
def empleado_usuarios_crear():
    """Crea una nueva cuenta de empleado. Requiere sesión de administrador."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lower()
    nombre   = data.get("nombre", "").strip()
    password = data.get("password", "").strip()
    if not username or not nombre or not password:
        return jsonify({"ok": False, "error": "Usuario, nombre y contraseña son obligatorios."})
    if len(password) < 4:
        return jsonify({"ok": False, "error": "La contraseña debe tener al menos 4 caracteres."})
    auth = _cargar_auth()
    if username in auth.get("empleado_usuarios", {}):
        return jsonify({"ok": False, "error": f"El usuario '{username}' ya existe."})
    if username in auth.get("policia_usuarios", {}):
        return jsonify({"ok": False, "error": f"El nombre de usuario '{username}' ya está en uso."})
    ahora = datetime.now().isoformat()
    auth.setdefault("empleado_usuarios", {})[username] = {
        "bcrypt": _hash_bcrypt(password), "nombre": nombre,
        "activo": True, "creado": ahora,
        "must_change": True, "password_changed": ahora,
    }
    _guardar_auth(auth)
    logger.info("AUTH: Cuenta empleado creada — %s (%s)", username, nombre)
    _log_auditoria("crear_cuenta_empleado", {"username": username, "nombre": nombre})
    return jsonify({"ok": True})


@app.route("/api/auth/empleado_usuarios/<username>", methods=["PATCH"])
def empleado_usuarios_actualizar(username):
    """Activa/desactiva o cambia la contraseña/nombre de una cuenta de empleado."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    auth     = _cargar_auth()
    usuarios = auth.get("empleado_usuarios", {})
    if username not in usuarios:
        return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
    data = request.get_json(silent=True) or {}
    if "activo" in data:
        usuarios[username]["activo"] = bool(data["activo"])
        if not data["activo"]:
            to_revoke = [t for t, p in list(_TOKENS.items())
                         if p.get("rol") == "empleado" and p.get("username") == username]
            for t in to_revoke:
                if _TOKENS[t].get("persistido"):
                    _eliminar_token_persistido(t)
                del _TOKENS[t]
    if "password" in data:
        nueva = data["password"].strip()
        if len(nueva) < 4:
            return jsonify({"ok": False, "error": "La contraseña debe tener al menos 4 caracteres."})
        ahora = datetime.now().isoformat()
        usuarios[username]["bcrypt"]           = _hash_bcrypt(nueva)
        usuarios[username]["modificado"]       = ahora
        usuarios[username]["password_changed"] = ahora
        usuarios[username]["must_change"]      = True
        usuarios[username].pop("hash", None)
        usuarios[username].pop("salt", None)
    if "nombre" in data:
        usuarios[username]["nombre"] = data["nombre"].strip()
    auth["empleado_usuarios"] = usuarios
    _guardar_auth(auth)
    logger.info("AUTH: Cuenta empleado actualizada — %s", username)
    campos = []
    if "activo" in data: campos.append("activo=" + ("sí" if data["activo"] else "no"))
    if "password" in data: campos.append("contraseña")
    if "nombre" in data: campos.append("nombre")
    _log_auditoria("actualizar_cuenta_empleado", {"username": username, "cambios": campos})
    return jsonify({"ok": True})


@app.route("/api/auth/empleado_usuarios/<username>", methods=["DELETE"])
def empleado_usuarios_eliminar(username):
    """Elimina permanentemente una cuenta de empleado y revoca sus tokens."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    auth     = _cargar_auth()
    usuarios = auth.get("empleado_usuarios", {})
    if username not in usuarios:
        return jsonify({"ok": False, "error": "Usuario no encontrado."}), 404
    nombre_prev = usuarios[username].get("nombre", username)
    del usuarios[username]
    auth["empleado_usuarios"] = usuarios
    to_revoke = [t for t, p in list(_TOKENS.items())
                 if p.get("rol") == "empleado" and p.get("username") == username]
    for t in to_revoke:
        if _TOKENS[t].get("persistido"):
            _eliminar_token_persistido(t)
        del _TOKENS[t]
    _guardar_auth(auth)
    logger.info("AUTH: Cuenta empleado eliminada — %s", username)
    _log_auditoria("eliminar_cuenta_empleado", {"username": username, "nombre": nombre_prev})
    return jsonify({"ok": True})


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Invalida el token del cliente (memoria y auth.json si era persistido)."""
    token = request.headers.get("X-Token", "")
    if token in _TOKENS:
        if _TOKENS[token].get("persistido"):
            _eliminar_token_persistido(token)
        del _TOKENS[token]
    return jsonify({"ok": True})


def _log_request_error(endpoint: str, exc: Exception):
    """Registra un error de endpoint con traceback completo."""
    logger.error(
        "ENDPOINT=%s METHOD=%s ARGS=%s ERROR=%s\n%s",
        endpoint,
        request.method,
        dict(request.args),
        str(exc),
        traceback.format_exc(),
    )


# Registra cada petición recibida (INFO)
@app.before_request
def _log_incoming():
    logger.info(">>> %s %s", request.method, request.path)


# Registra respuestas con errores HTTP (WARNING/ERROR)
@app.after_request
def _log_response(response):
    if response.status_code >= 400:
        logger.warning(
            "<<< %s %s -> %s", request.method, request.path, response.status_code
        )
    return response


MARIADB = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "3307")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "123"),
    "database": os.environ.get("DB_NAME", "censo_animales"),
}
# Utilidades de base de datos


def get_conn():
    conn = mysql.connector.connect(**MARIADB)
    cur = conn.cursor(buffered=True)
    cur.execute("SET NAMES utf8mb4")
    cur.close()
    return conn


def cur(conn):
    return conn.cursor(buffered=True)


def serializar(val):
    return val.isoformat() if isinstance(val, (datetime, date)) else val


def fila_a_dict(cursor, fila):
    cols = [d[0] for d in cursor.description]
    return {c: serializar(v) for c, v in zip(cols, fila)}


def detectar_chip(c):
    return "N_CHIP"


def _siguiente_n_baja(conn, anio: int) -> str:
    """
    Genera el siguiente número de baja del año indicado
    con formato BAJA-AAAA-NNNN, leyendo el último registrado.
    """
    c = cur(conn)
    c.execute(
        "SELECT N_BAJA FROM BAJA_ANIMAL "
        "WHERE N_BAJA LIKE %s "
        "ORDER BY N_BAJA DESC LIMIT 1",
        (f"BAJA-{anio}-%",),
    )
    fila = c.fetchone()
    try:
        ultimo = int(fila[0].split("-")[-1]) if fila and fila[0] else 0
    except (ValueError, IndexError) as e:
        logger.debug("N_BAJA: no se pudo parsear %r: %s", fila, e)
        ultimo = 0
    return f"BAJA-{anio}-{ultimo + 1:04d}"


def _insertar_baja(
    conn, chip_col: str, chip: str, dni: str, motivo: str, obs: str, n_baja: str
):
    fecha_hoy = date.today().isoformat()

    cur(conn).execute(
        f"INSERT INTO BAJA_ANIMAL (`{chip_col}`, FECHA, N_BAJA, MOTIVO) "
        "VALUES (%s, %s, %s, %s)",
        (chip, fecha_hoy, n_baja, motivo),
    )
    cur(conn).execute(
        f"INSERT INTO HISTORICO_MASCOTAS "
        f"(`{chip_col}`, FECHA, ID_ESTADO, DNI_PROPIETARIO, OBSERVACIONES) "
        "VALUES (%s, %s, 2, %s, %s)",
        (chip, fecha_hoy, dni, obs or None),
    )


# Endpoints — Propietarios


@app.route("/api/propietarios", methods=["GET"])
def listar_propietarios():
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("SELECT * FROM PROPIETARIOS ORDER BY PRIMER_APELLIDO, NOMBRE")
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/propietarios/<dni>", methods=["GET"])
def obtener_propietario(dni):
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("SELECT * FROM PROPIETARIOS WHERE DNI = %s", (dni,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({"ok": False, "error": "No encontrado"})
        return jsonify({"ok": True, "datos": fila_a_dict(c, row)})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/propietarios", methods=["POST"])
def insertar_propietario():
    d = request.get_json()
    if not d.get("DNI"):
        return jsonify({"ok": False, "error": "Campo requerido: DNI"}), 400
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute(
            """INSERT INTO PROPIETARIOS
                 (DNI, PRIMER_APELLIDO, SEGUNDO_APELLIDO, NOMBRE,
                  TELEFONO1, TELEFONO2)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                d.get("DNI"),
                d.get("PRIMER_APELLIDO"),
                d.get("SEGUNDO_APELLIDO"),
                d.get("NOMBRE"),
                d.get("TELEFONO1"),
                d.get("TELEFONO2"),
            ),
        )
        direcciones = d.get("DIRECCIONES", [])
        for dr in direcciones:
            dom = dr.get("DOMICILIO", "").strip()
            if dom:
                c.execute(
                    """INSERT INTO PROPIETARIO_DIRECCION (DNI, DOMICILIO, CP, MUNICIPIO)
                       VALUES (%s, %s, %s, %s)""",
                    (d.get("DNI"), dom, dr.get("CP"), dr.get("MUNICIPIO") or dr.get("MINICIPIO")),
                )
        conn.commit()
        conn.close()
        _log_auditoria("crear_propietario", {
            "DNI": d.get("DNI"),
            "nombre": f"{d.get('NOMBRE','') or ''} {d.get('PRIMER_APELLIDO','') or ''} {d.get('SEGUNDO_APELLIDO','') or ''}".strip(),
            "direcciones": len(direcciones),
        })
        return jsonify({"ok": True, "mensaje": "Propietario registrado correctamente."})
    except mysql.connector.IntegrityError as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("crear_propietario", {"DNI": d.get("DNI"), "error": "DNI duplicado"}, exito=False)
        return (
            jsonify({"ok": False, "error": "El DNI ya existe en la base de datos."}),
            409,
        )
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("crear_propietario", {"DNI": d.get("DNI"), "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": str(e)}), 500


# Endpoints — Direcciones de propietarios


@app.route("/api/propietarios/<dni>/direcciones", methods=["GET"])
def listar_direcciones(dni):
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        # Devolver direcciones con conteo de animales activos asociados
        c.execute(
            f"""SELECT pd.*,
                       (SELECT COUNT(*)
                        FROM ANIMALES a
                        WHERE a.ID_DOMICILIO = pd.CODIGO
                          AND a.`{chip_col}` NOT IN (
                              SELECT b.`{chip_col}` FROM BAJA_ANIMAL b
                              WHERE b.`{chip_col}` IS NOT NULL
                          )
                       ) AS NUM_ANIMALES
                FROM PROPIETARIO_DIRECCION pd
                WHERE pd.DNI = %s
                ORDER BY pd.CODIGO""",
            (dni,),
        )
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "direcciones": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/propietarios/<dni>/direcciones", methods=["POST"])
def crear_direccion(dni):
    d = request.get_json()
    if not d.get("DOMICILIO", "").strip():
        return jsonify({"ok": False, "error": "El domicilio es obligatorio."}), 400
    try:
        conn = get_conn()
        c = cur(conn)
        # Verificar que el propietario existe
        c.execute("SELECT DNI FROM PROPIETARIOS WHERE DNI = %s", (dni,))
        if not c.fetchone():
            conn.close()
            return jsonify({"ok": False, "error": "Propietario no encontrado."}), 404
        c.execute(
            """INSERT INTO PROPIETARIO_DIRECCION (DNI, DOMICILIO, CP, MUNICIPIO)
               VALUES (%s, %s, %s, %s)""",
            (dni, d.get("DOMICILIO"), d.get("CP"), d.get("MUNICIPIO") or d.get("MINICIPIO")),
        )
        new_id = c.lastrowid
        conn.commit()
        conn.close()
        _log_auditoria("crear_direccion", {"DNI": dni, "CODIGO": new_id, "DOMICILIO": d.get("DOMICILIO")})
        return jsonify({"ok": True, "mensaje": "Domicilio añadido.", "CODIGO": new_id})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/propietarios/<dni>/direcciones/<int:codigo>", methods=["DELETE"])
def eliminar_direccion(dni, codigo):
    try:
        conn = get_conn()
        c = cur(conn)
        # Verificar que no hay animales asociados a este domicilio
        c.execute(
            "SELECT COUNT(*) AS n FROM ANIMALES WHERE ID_DOMICILIO = %s", (codigo,)
        )
        row = c.fetchone()
        n = row[0] if row else 0
        if n > 0:
            conn.close()
            return jsonify({
                "ok": False,
                "error": f"No se puede eliminar: hay {n} animal(es) censado(s) en este domicilio.",
            }), 409
        c.execute(
            "DELETE FROM PROPIETARIO_DIRECCION WHERE CODIGO = %s AND DNI = %s",
            (codigo, dni),
        )
        if c.rowcount == 0:
            conn.close()
            return jsonify({"ok": False, "error": "Domicilio no encontrado."}), 404
        conn.commit()
        conn.close()
        _log_auditoria("eliminar_direccion", {"DNI": dni, "CODIGO": codigo})
        return jsonify({"ok": True, "mensaje": "Domicilio eliminado."})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# Endpoints — Animales


@app.route("/api/animales", methods=["GET"])
def listar_animales():
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(f"SELECT * FROM ANIMALES ORDER BY `{chip_col}`")
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/animales/<chip>", methods=["GET"])
def obtener_animal(chip):
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(f"SELECT * FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({"ok": False, "error": "No encontrado"})
        return jsonify({"ok": True, "datos": fila_a_dict(c, row)})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/animales/<chip>", methods=["PUT"])
def actualizar_animal(chip):
    """
    Campos permitidos:
      - DNI_PROPIETARIO  (debe existir en PROPIETARIOS)
      - FECHA_ULTIMA_VACUNA_ANTIRRABICA
      - ESTERILIZADO
      - SEGURO_POLIZA    (actualiza SEGUROS; requiere que ya exista un seguro para el chip)
    """
    d = request.get_json()
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Snapshot ANTES para auditoría con diff
        estado_antes = _snapshot_animal(conn, chip)

        # Verificar que el animal existe
        c.execute(f"SELECT COUNT(*) FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        if c.fetchone()[0] == 0:
            conn.close()
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "No existe ningún animal con ese número de chip.",
                    }
                ),
                404,
            )

        # Columnas reales de la tabla
        c.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ANIMALES' "
            "ORDER BY ORDINAL_POSITION"
        )
        cols_tabla = [r[0] for r in c.fetchall()]
        col_vacuna = (
            "FECHA_ULTIMA_VACUNACION_ANTIRRABICA"
            if "FECHA_ULTIMA_VACUNACION_ANTIRRABICA" in cols_tabla
            else "FECHA_ULTIMA_VACUNA_ANTIRRABICA"
        )

        set_parts, set_vals = [], []

        # ── DNI/NIE del propietario ───────────────────────────────
        if "DNI_PROPIETARIO" in d:
            nuevo_dni = (d["DNI_PROPIETARIO"] or "").strip().upper()
            if nuevo_dni:
                c2 = cur(conn)
                c2.execute(
                    "SELECT COUNT(*) FROM PROPIETARIOS WHERE TRIM(UPPER(DNI)) = %s",
                    (nuevo_dni,),
                )
                if c2.fetchone()[0] == 0:
                    conn.close()
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": f"El DNI/NIE «{nuevo_dni}» no existe en el padrón de propietarios.",
                            }
                        ),
                        404,
                    )
                set_parts.append("`DNI_PROPIETARIO` = %s")
                set_vals.append(nuevo_dni)

        # ── Fecha última vacuna antirrábica ───────────────────────
        if "FECHA_ULTIMA_VACUNA_ANTIRRABICA" in d and col_vacuna in cols_tabla:
            val = d["FECHA_ULTIMA_VACUNA_ANTIRRABICA"]
            set_parts.append(f"`{col_vacuna}` = %s")
            set_vals.append(val if val and str(val).strip() else None)

        # ── Esterilizado ──────────────────────────────────────────
        if "ESTERILIZADO" in d and "ESTERILIZADO" in cols_tabla:
            val = (
                1
                if str(d["ESTERILIZADO"]).lower() in ("1", "true", "si", "sí", "yes")
                else 0
            )
            set_parts.append("`ESTERILIZADO` = %s")
            set_vals.append(val)

        # ── Actualizar ANIMALES ───────────────────────────────────
        if set_parts:
            set_vals.append(chip)
            c.execute(
                f"UPDATE ANIMALES SET {', '.join(set_parts)} WHERE `{chip_col}` = %s",
                set_vals,
            )

        # ── Póliza de seguro (tabla SEGUROS) ──────────────────────
        if "SEGURO_POLIZA" in d:
            nueva_poliza = (d["SEGURO_POLIZA"] or "").strip()
            c3 = cur(conn)
            c3.execute(
                f"UPDATE SEGUROS SET SEGURO_POLIZA = %s WHERE `{chip_col}` = %s",
                (nueva_poliza if nueva_poliza else None, chip),
            )

        if not set_parts and "SEGURO_POLIZA" not in d:
            conn.close()
            return (
                jsonify(
                    {"ok": False, "error": "No se proporcionaron campos a actualizar."}
                ),
                400,
            )

        conn.commit()
        # Snapshot DESPUÉS para calcular diff antes de cerrar conexión
        estado_despues = _snapshot_animal(conn, chip)
        conn.close()
        campos_mod = [k for k in ("DNI_PROPIETARIO", "FECHA_ULTIMA_VACUNA_ANTIRRABICA",
                                    "ESTERILIZADO", "SEGURO_POLIZA") if k in d]
        diff = _diff_dict(estado_antes, estado_despues)
        _log_auditoria("actualizar_animal", {
            "N_CHIP": chip,
            "campos_modificados": campos_mod,
            "diff": diff,
        })
        return jsonify({"ok": True, "mensaje": "Animal actualizado correctamente."})

    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("actualizar_animal", {"N_CHIP": chip, "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/animales", methods=["POST"])
def insertar_animal():
    d = request.get_json()
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Columnas reales de la tabla
        c.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ANIMALES' "
            "ORDER BY ORDINAL_POSITION"
        )
        cols_tabla = [r[0] for r in c.fetchall()]

        # ── Verificar límite de animales por propietario (5 máximo) ──
        dni_solicitado = (d.get("DNI_PROPIETARIO") or "").strip().upper()
        if dni_solicitado:
            c.execute(
                f"""SELECT COUNT(*)
                    FROM ANIMALES a
                    WHERE TRIM(UPPER(a.DNI_PROPIETARIO)) = %s
                      AND a.`{chip_col}` NOT IN (
                          SELECT b.`{chip_col}` FROM BAJA_ANIMAL b
                          WHERE b.`{chip_col}` IS NOT NULL
                      )""",
                (dni_solicitado,),
            )
            total_activos = c.fetchone()[0]
            if total_activos >= 5:
                conn.close()
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": f"Este propietario ya tiene {total_activos} animal(es) activo(s) registrado(s). "
                            f"El límite máximo es de 5 animales por propietario.",
                            "limite_alcanzado": True,
                            "total_activos": total_activos,
                        }
                    ),
                    409,
                )

        # ── Generar N_CENSO automático: CEN-XXX ──────────────────
        c.execute(
            "SELECT N_CENSO FROM CENSO "
            "WHERE N_CENSO LIKE 'CEN-%' "
            "ORDER BY CODIGO_CENSO DESC LIMIT 1"
        )
        fila_seq = c.fetchone()
        try:
            ultimo_censo = (
                int(fila_seq[0].split("-")[-1]) if fila_seq and fila_seq[0] else 0
            )
        except (ValueError, IndexError) as e:
            logger.debug("N_CENSO: no se pudo parsear %r: %s", fila_seq, e)
            ultimo_censo = 0
        n_censo_auto = f"CEN-{ultimo_censo + 1:03d}"

        # Mapa campo_formulario → columna_real
        col_nacimiento = (
            "FECHA_NACIMIENTO"
            if "FECHA_NACIMIENTO" in cols_tabla
            else "ANIO_NACIMIENTO"
        )
        mapa = {
            "N_CHIP": chip_col,
            "ESPECIE": "ESPECIE",
            "RAZA": "RAZA",
            "SEXO": "SEXO",
            "NOMBRE": "NOMBRE",
            "COLOR": "COLOR",
            "FECHA_NACIMIENTO": col_nacimiento,
            "FECHA_ULTIMA_VACUNA_ANTIRRABICA": "FECHA_ULTIMA_VACUNA_ANTIRRABICA",
            "ESTERILIZADO": "ESTERILIZADO",
            "DNI_PROPIETARIO": "DNI_PROPIETARIO",
            "PELIGROSO": "PELIGROSO",
            "ID_DOMICILIO": "ID_DOMICILIO",
        }

        # ── Verificar límite de 5 animales por domicilio ──
        id_dom = d.get("ID_DOMICILIO")
        if id_dom:
            try:
                id_dom = int(id_dom)
            except (ValueError, TypeError) as e:
                logger.debug("ID_DOMICILIO inválido %r: %s", id_dom, e)
                id_dom = None
        if id_dom:
            c.execute(
                f"""SELECT COUNT(*)
                    FROM ANIMALES a
                    WHERE a.ID_DOMICILIO = %s
                      AND a.`{chip_col}` NOT IN (
                          SELECT b.`{chip_col}` FROM BAJA_ANIMAL b
                          WHERE b.`{chip_col}` IS NOT NULL
                      )""",
                (id_dom,),
            )
            animales_en_dom = c.fetchone()[0]
            if animales_en_dom >= 5:
                conn.close()
                return (
                    jsonify({
                        "ok": False,
                        "error": f"El domicilio seleccionado ya tiene {animales_en_dom} animal(es) activo(s). "
                        "El límite máximo es de 5 animales por domicilio.",
                        "limite_alcanzado": True,
                    }),
                    409,
                )

        # Añadir N_CENSO al insert si la columna existe
        col_censo = next(
            (c_ for c_ in cols_tabla if c_ == "N_CENSO"), None
        )

        insert_cols, insert_vals = [], []

        for campo, col_real in mapa.items():
            if col_real not in cols_tabla:
                continue
            val = d.get(campo)
            if val is None or not str(val).strip():
                continue
            if campo in ("ESTERILIZADO", "PELIGROSO"):
                val = 1 if str(val).lower() in ("1", "true", "si", "sí", "yes") else 0
            insert_cols.append(f"`{col_real}`")
            insert_vals.append(val)

        if col_censo:
            insert_cols.append(f"`{col_censo}`")
            insert_vals.append(n_censo_auto)

        if not insert_cols:
            return jsonify({"ok": False, "error": "No se proporcionaron datos."}), 400

        # ── Verificar que el chip no existe ya ────────────────────
        chip_nuevo = d.get("N_CHIP", "").strip()
        if chip_nuevo:
            c.execute(
                f"SELECT COUNT(*) FROM ANIMALES WHERE `{chip_col}` = %s",
                (chip_nuevo,),
            )
            if c.fetchone()[0] > 0:
                conn.close()
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": f"El número de chip «{chip_nuevo}» ya está registrado en el censo. "
                            "Cada animal debe tener un chip único.",
                            "chip_duplicado": True,
                        }
                    ),
                    409,
                )

        c.execute(
            f"INSERT INTO ANIMALES ({', '.join(insert_cols)}) "
            f"VALUES ({', '.join(['%s'] * len(insert_vals))})",
            insert_vals,
        )

        # Insertar en tabla CENSO
        chip_val = d.get("N_CHIP", "")
        try:
            c2 = cur(conn)
            c2.execute(
                "INSERT INTO CENSO (N_CHIP, N_CENSO, FECHA_ALTA) "
                "VALUES (%s, %s, CURDATE())",
                (chip_val, n_censo_auto),
            )
        except Exception as e:
            # No bloquear el alta si falla el insert en CENSO
            logger.warning("INSERT en CENSO falló (chip=%s, n_censo=%s): %s", chip_val, n_censo_auto, e)

        conn.commit()

        conn.close()
        _log_auditoria("crear_animal", {
            "N_CHIP": d.get("N_CHIP"),
            "nombre": d.get("NOMBRE"),
            "especie": d.get("ESPECIE"),
            "DNI_propietario": d.get("DNI_PROPIETARIO"),
            "N_CENSO": n_censo_auto,
        })
        return jsonify(
            {
                "ok": True,
                "mensaje": "Animal registrado correctamente.",
                "n_censo": n_censo_auto,
            }
        )

    except mysql.connector.IntegrityError as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("crear_animal", {"N_CHIP": d.get("N_CHIP"), "error": f"integridad_{e.errno}"}, exito=False)
        msgs = {
            1062: f"El número de chip ya existe. Detalle: {e}",
            1452: f"El DNI del propietario no existe. Regístrelo primero. Detalle: {e}",
        }
        return (
            jsonify(
                {
                    "ok": False,
                    "error": msgs.get(e.errno, f"Error de integridad ({e.errno}): {e}"),
                }
            ),
            409,
        )
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("crear_animal", {"N_CHIP": d.get("N_CHIP"), "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": f"Error inesperado: {e}"}), 500


# Endpoints — Catálogos


@app.route("/api/sexos", methods=["GET"])
def listar_sexos():
    try:
        conn = get_conn()
        c = cur(conn)
        try:
            c.execute("SELECT CLAVE, SEXO FROM SEXO")
            rows = [fila_a_dict(c, r) for r in c.fetchall()]
        except Exception as e:
            logger.warning("SEXOS: falló consulta, usando valores por defecto: %s", e)
            rows = [
                {"CLAVE": "Macho", "SEXO": "Macho"},
                {"CLAVE": "Hembra", "SEXO": "Hembra"},
            ]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/estados", methods=["GET"])
def listar_estados():
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("SELECT ID_ESTADO, ESTADO FROM ESTADOS_HISTORICO ORDER BY ESTADO")
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/motivos_baja", methods=["GET"])
def listar_motivos_baja():
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("SELECT CLAVE, MOTIVO_BAJA FROM MOTIVO_BAJA ORDER BY CLAVE")
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# Endpoints — Seguros


@app.route("/api/seguros", methods=["GET"])
def listar_seguros():
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(
            f"""SELECT s.ID_SEGUROS,
                       s.`{chip_col}`        AS N_CHIP,
                       s.SEGURO_COMPANIA,
                       s.SEGURO_POLIZA,
                       a.NOMBRE              AS NOMBRE_ANIMAL,
                       a.ESPECIE,
                       a.DNI_PROPIETARIO
                FROM SEGUROS s
                LEFT JOIN ANIMALES a ON s.`{chip_col}` = a.`{chip_col}`
                ORDER BY s.ID_SEGUROS"""
        )
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/seguros/<int:id_seguro>", methods=["GET"])
def obtener_seguro(id_seguro):
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("SELECT * FROM SEGUROS WHERE ID_SEGUROS = %s", (id_seguro,))
        row = c.fetchone()
        conn.close()
        if not row:
            return jsonify({"ok": False, "error": "No encontrado"})
        return jsonify({"ok": True, "datos": fila_a_dict(c, row)})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/seguros", methods=["POST"])
def insertar_seguro():
    d = request.get_json()
    requeridos = {
        "N_CHIP": "N.º chip",
        "SEGURO_COMPANIA": "Compañía",
        "SEGURO_POLIZA": "N.º póliza",
    }
    for campo, label in requeridos.items():
        if not d.get(campo):
            return jsonify({"ok": False, "error": f"Campo requerido: {label}"}), 400
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(
            f"INSERT INTO SEGUROS (`{chip_col}`, SEGURO_COMPANIA, SEGURO_POLIZA) "
            "VALUES (%s, %s, %s)",
            (d["N_CHIP"], d["SEGURO_COMPANIA"], d["SEGURO_POLIZA"]),
        )
        conn.commit()
        nuevo_id = c.lastrowid
        conn.close()
        _log_auditoria("crear_seguro", {
            "id": nuevo_id,
            "N_CHIP": d.get("N_CHIP"),
            "compania": d.get("SEGURO_COMPANIA"),
            "poliza": d.get("SEGURO_POLIZA"),
        })
        return jsonify(
            {"ok": True, "mensaje": "Seguro registrado correctamente.", "id": nuevo_id}
        )
    except mysql.connector.IntegrityError as e:
        _log_auditoria("crear_seguro", {"N_CHIP": d.get("N_CHIP"), "error": f"integridad_{e.errno}"}, exito=False)
        msg = (
            "El número de chip no existe en el censo de animales."
            if e.errno == 1452
            else f"Error de integridad: {e}"
        )
        return jsonify({"ok": False, "error": msg}), 409
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("crear_seguro", {"N_CHIP": d.get("N_CHIP"), "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/seguros/<int:id_seguro>", methods=["DELETE"])
def eliminar_seguro(id_seguro):
    try:
        conn = get_conn()
        c = cur(conn)
        # Leer datos antes de borrar para poder auditarlo
        c.execute("SELECT * FROM SEGUROS WHERE ID_SEGUROS = %s", (id_seguro,))
        row = c.fetchone()
        detalle_prev = fila_a_dict(c, row) if row else None
        c.execute("DELETE FROM SEGUROS WHERE ID_SEGUROS = %s", (id_seguro,))
        conn.commit()
        conn.close()
        _log_auditoria("eliminar_seguro", {"id": id_seguro, "datos": detalle_prev})
        return jsonify({"ok": True, "mensaje": "Seguro eliminado."})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("eliminar_seguro", {"id": id_seguro, "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": str(e)}), 500


# Endpoints — Bajas


@app.route("/api/bajas", methods=["GET"])
def listar_bajas():
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(
            f"""SELECT b.`{chip_col}`      AS N_CHIP,
                       b.FECHA             AS FECHA_BAJA,
                       b.N_BAJA           AS N_BAJA,
                       b.MOTIVO,
                       mb.MOTIVO_BAJA      AS MOTIVO_DESC,
                       h.OBSERVACIONES     AS OBSERVACIONES,
                       a.NOMBRE            AS NOMBRE_ANIMAL,
                       a.ESPECIE,
                       a.RAZA,
                       a.SEXO,
                       a.DNI_PROPIETARIO,
                       p.NOMBRE            AS NOMBRE_PROP,
                       p.PRIMER_APELLIDO,
                       p.SEGUNDO_APELLIDO
                FROM BAJA_ANIMAL b
                LEFT JOIN ANIMALES a     ON b.`{chip_col}` = a.`{chip_col}`
                LEFT JOIN MOTIVO_BAJA mb ON b.MOTIVO = mb.CLAVE
                LEFT JOIN PROPIETARIOS p ON a.DNI_PROPIETARIO = p.DNI
                LEFT JOIN (
                    SELECT `{chip_col}` AS CHIP, OBSERVACIONES
                    FROM HISTORICO_MASCOTAS
                    WHERE ID_ESTADO = 2
                ) h ON h.CHIP = b.`{chip_col}`
                ORDER BY b.FECHA DESC, b.`{chip_col}`"""
        )
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "datos": rows})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/propietarios/<dni>/animales", methods=["GET"])
def animales_por_propietario(dni):
    try:
        conn = get_conn()

        # Verificar propietario con cursor independiente
        c_prop = cur(conn)
        c_prop.execute(
            "SELECT DNI, NOMBRE, PRIMER_APELLIDO, SEGUNDO_APELLIDO "
            "FROM PROPIETARIOS WHERE DNI = %s",
            (dni,),
        )
        prop = c_prop.fetchone()
        if not prop:
            conn.close()
            return jsonify(
                {
                    "ok": False,
                    "error": "No se encontró ningún propietario con ese DNI.",
                }
            )

        prop_dict = fila_a_dict(c_prop, prop)
        dni_bd = prop_dict.get("DNI") or prop[0]

        c = cur(conn)
        chip_col = detectar_chip(c)

        c.execute(
            f"""SELECT a.`{chip_col}` AS N_CHIP,
                       a.NOMBRE, a.ESPECIE, a.RAZA, a.SEXO, a.COLOR
                FROM ANIMALES a
                WHERE a.DNI_PROPIETARIO = %s
                  AND a.`{chip_col}` NOT IN (
                      SELECT b.`{chip_col}` FROM BAJA_ANIMAL b
                      WHERE b.`{chip_col}` IS NOT NULL
                  )
                ORDER BY a.NOMBRE""",
            (dni,),
        )
        animales = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()

        prop_dict["DNI"] = dni_bd
        return jsonify({"ok": True, "propietario": prop_dict, "animales": animales})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/bajas", methods=["POST"])
def registrar_baja():
    d = request.get_json()
    chip = (d.get("N_CHIP") or "").strip()
    dni = (d.get("DNI") or "").strip().upper()
    motivo = d.get("MOTIVO")
    obs = d.get("OBSERVACIONES", "")

    for campo, label in [
        ("N_CHIP", "N.º chip"),
        ("DNI", "DNI del propietario"),
        ("MOTIVO", "motivo de baja"),
    ]:
        if not d.get(campo, "").strip() if campo != "MOTIVO" else not motivo:
            return jsonify({"ok": False, "error": f"Campo requerido: {label}"}), 400

    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # ¿Existe el animal?
        c.execute(f"SELECT COUNT(*) FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        if c.fetchone()[0] == 0:
            conn.close()
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "No existe ningún animal con ese número de chip.",
                    }
                ),
                404,
            )

        # ¿Pertenece al propietario indicado? (comparación normalizada en SQL)
        c.execute(
            f"""SELECT COUNT(*)
                FROM ANIMALES a
                JOIN PROPIETARIOS p
                  ON TRIM(UPPER(a.DNI_PROPIETARIO)) = TRIM(UPPER(p.DNI))
                WHERE a.`{chip_col}` = %s
                  AND TRIM(UPPER(p.DNI)) = TRIM(UPPER(%s))""",
            (chip, dni),
        )
        if c.fetchone()[0] == 0:
            conn.close()
            return (
                jsonify(
                    {
                        "ok": False,
                        "error": "El DNI introducido no corresponde al propietario de ese animal.",
                    }
                ),
                403,
            )

        # ¿Ya tiene baja?
        c.execute(f"SELECT COUNT(*) FROM BAJA_ANIMAL WHERE `{chip_col}` = %s", (chip,))
        if c.fetchone()[0] > 0:
            conn.close()
            return (
                jsonify(
                    {"ok": False, "error": "Este animal ya tiene una baja registrada."}
                ),
                409,
            )

        n_baja_auto = _siguiente_n_baja(conn, date.today().year)
        _insertar_baja(conn, chip_col, chip, dni, motivo, obs, n_baja_auto)
        conn.commit()
        conn.close()
        _log_auditoria("baja_animal", {
            "N_CHIP": chip,
            "DNI_propietario": dni,
            "motivo": motivo,
            "observaciones": obs,
            "n_baja": n_baja_auto,
        })
        return jsonify(
            {
                "ok": True,
                "mensaje": "Baja registrada correctamente en el censo municipal.",
                "n_baja": n_baja_auto,
            }
        )

    except mysql.connector.IntegrityError as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("baja_animal", {"N_CHIP": chip, "error": f"integridad_{e.errno}"}, exito=False)
        return jsonify({"ok": False, "error": f"Error de integridad: {e}"}), 409
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("baja_animal", {"N_CHIP": chip, "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": str(e)}), 500


# Tarea programada — Baja automática por edad (>100 años)


def baja_automatica_por_edad():
    try:
        anio_corte = date.today().year - 100
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Detectar columna de nacimiento
        c.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ANIMALES' "
            "AND COLUMN_NAME IN ('ANIO_NACIMIENTO', 'FECHA_NACIMIENTO') LIMIT 1"
        )
        row_col = c.fetchone()
        if not row_col:
            conn.close()
            return
        nac_col = row_col[0]

        # Animales mayores de 100 años sin baja previa
        c.execute(
            f"""SELECT a.`{chip_col}`, a.DNI_PROPIETARIO
                FROM ANIMALES a
                WHERE a.`{nac_col}` IS NOT NULL
                  AND a.`{nac_col}` != ''
                  AND CAST(
                        CASE
                          WHEN a.`{nac_col}` REGEXP '^[0-9]{{4}}'
                          THEN LEFT(a.`{nac_col}`, 4)
                          ELSE '9999'
                        END
                      AS UNSIGNED) <= %s
                  AND a.`{chip_col}` NOT IN (
                      SELECT b.`{chip_col}` FROM BAJA_ANIMAL b
                      WHERE b.`{chip_col}` IS NOT NULL
                  )""",
            (anio_corte,),
        )
        candidatos = c.fetchall()

        if not candidatos:
            conn.close()
            return

        anio_hoy = date.today().year
        obs = "Baja automática por superación del límite de edad (100 años)"
        dados_baja = []

        # Obtener el último número de baja del año para continuar la secuencia
        c.execute(
            "SELECT N_BAJA FROM BAJA_ANIMAL "
            "WHERE N_BAJA LIKE %s ORDER BY N_BAJA DESC LIMIT 1",
            (f"BAJA-{anio_hoy}-%",),
        )
        fila_seq = c.fetchone()
        try:
            ultimo = int(fila_seq[0].split("-")[-1]) if fila_seq and fila_seq[0] else 0
        except (ValueError, IndexError) as e:
            logger.debug("N_BAJA auto: no se pudo parsear %r: %s", fila_seq, e)
            ultimo = 0

        for chip, dni_prop in candidatos:
            ultimo += 1
            n_baja = f"BAJA-{anio_hoy}-{ultimo:04d}"
            try:
                _insertar_baja(conn, chip_col, chip, dni_prop, "1001", obs, n_baja)
                dados_baja.append(chip)
                _log_auditoria("baja_animal_automatica", {
                    "N_CHIP": chip,
                    "DNI_propietario": dni_prop,
                    "motivo": "1001",
                    "n_baja": n_baja,
                    "observaciones": obs,
                })
            except Exception as e:
                logger.warning("baja_automatica: fallo con chip=%s dni=%s: %s", chip, dni_prop, e)
                # Un fallo individual no detiene el resto

        conn.commit()
        conn.close()

        if dados_baja:
            print(
                f"[AUTO-BAJA] {len(dados_baja)} animal(es) dado(s) de baja por edad: {dados_baja}"
            )

    except Exception as e:
        logger.exception("AUTO-BAJA: error en el proceso automático: %s", e)


# Mantenimiento de esquema


def aplicar_unique_chip():
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Comprobar si ya existe un índice UNIQUE sobre esa columna
        c.execute(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'ANIMALES' "
            "AND COLUMN_NAME = %s "
            "AND NON_UNIQUE = 0",
            (chip_col,),
        )
        if c.fetchone()[0] == 0:
            c.execute(f"ALTER TABLE ANIMALES ADD UNIQUE INDEX `uq_chip` (`{chip_col}`)")
            conn.commit()
            print(f"[SCHEMA] UNIQUE aplicado a ANIMALES.`{chip_col}`")
        else:
            print(f"[SCHEMA] UNIQUE ya existe en ANIMALES.`{chip_col}`")
        conn.close()
    except Exception as e:
        logger.warning("SCHEMA: no se pudo aplicar UNIQUE en chip: %s", e)


@app.route("/api/estadisticas", methods=["GET"])
def estadisticas():
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Filtros opcionales
        especie_filtro = (request.args.get("especie") or "").strip()
        try:
            anio_desde = int(request.args.get("anio_desde") or 0) or None
        except (ValueError, TypeError) as e:
            logger.debug("ESTADISTICAS: anio_desde inválido %r: %s", request.args.get("anio_desde"), e)
            anio_desde = None
        try:
            anio_hasta = int(request.args.get("anio_hasta") or 0) or None
        except (ValueError, TypeError) as e:
            logger.debug("ESTADISTICAS: anio_hasta inválido %r: %s", request.args.get("anio_hasta"), e)
            anio_hasta = None

        def filas(q, params=()):
            c.execute(q, params)
            return c.fetchall()

        # -- Todos los animales registrados (filtrados por especie si se indica) --
        where_especie = " WHERE LOWER(TRIM(a.ESPECIE)) = LOWER(%s)" if especie_filtro else ""
        params_main = [especie_filtro] if especie_filtro else []

        c.execute(
            f"""SELECT a.ESPECIE, a.SEXO, a.PELIGROSO, a.ESTERILIZADO,
                       a.`{chip_col}` AS N_CHIP,
                       a.ANIO_NACIMIENTO
                FROM ANIMALES a{where_especie}""",
            params_main,
        )
        animales = c.fetchall()
        cols_a = [d[0] for d in c.description]

        # Número de activos (sin baja), con filtro de especie si se indica
        if especie_filtro:
            c.execute(
                f"""SELECT COUNT(*) FROM ANIMALES a
                    WHERE LOWER(TRIM(a.ESPECIE)) = LOWER(%s)
                    AND NOT EXISTS (
                        SELECT 1 FROM BAJA_ANIMAL b
                        WHERE b.`{chip_col}` = a.`{chip_col}`
                    )""",
                [especie_filtro],
            )
        else:
            c.execute(
                f"""SELECT COUNT(*) FROM ANIMALES a
                    WHERE NOT EXISTS (
                        SELECT 1 FROM BAJA_ANIMAL b
                        WHERE b.`{chip_col}` = a.`{chip_col}`
                    )"""
            )
        total_activos = c.fetchone()[0]

        from collections import defaultdict, Counter
        import datetime

        especies = Counter()
        sexos = Counter()
        peligrosos = Counter({"Peligroso": 0, "No peligroso": 0})
        esterilizados = Counter({"Esterilizado": 0, "No esterilizado": 0})
        nacimientos = Counter()
        anio_actual = datetime.date.today().year

        def norm(v, fallback="Sin datos"):
            """Normaliza cadena: strip + title-case. Devuelve fallback si vacía."""
            if v is None:
                return fallback
            s = str(v).strip()
            return s.title() if s else fallback

        for row in animales:
            r = dict(zip(cols_a, row))
            especies[norm(r.get("ESPECIE"))] += 1
            sexos[norm(r.get("SEXO"))] += 1

            def es_activo(v):
                """Devuelve True solo si el valor text de la BD es '1'."""
                return str(v).strip() == "1" if v is not None else False

            peligrosos[
                "Peligroso" if es_activo(r.get("PELIGROSO")) else "No peligroso"
            ] += 1
            esterilizados[
                (
                    "Esterilizado"
                    if es_activo(r.get("ESTERILIZADO"))
                    else "No esterilizado"
                )
            ] += 1
            anio = r.get("ANIO_NACIMIENTO")
            if anio:
                try:
                    y = int(str(anio).strip()[:4])
                    if 1900 <= y <= anio_actual:
                        if (anio_desde is None or y >= anio_desde) and (
                            anio_hasta is None or y <= anio_hasta
                        ):
                            nacimientos[y] += 1
                except (ValueError, TypeError) as e:
                    logger.debug("Año nacimiento inválido ignorado: %r (%s)", anio, e)

        # -- Bajas por año y por motivo (con filtro de especie si se indica) --
        if especie_filtro:
            c.execute(
                f"""
                SELECT YEAR(b.FECHA) AS anio, COUNT(*) AS total,
                       mb.MOTIVO_BAJA AS motivo
                FROM BAJA_ANIMAL b
                INNER JOIN ANIMALES a ON b.`{chip_col}` = a.`{chip_col}`
                LEFT JOIN MOTIVO_BAJA mb ON b.MOTIVO = mb.CLAVE
                WHERE b.FECHA IS NOT NULL AND LOWER(TRIM(a.ESPECIE)) = LOWER(%s)
                GROUP BY YEAR(b.FECHA), b.MOTIVO
                ORDER BY anio
                """,
                [especie_filtro],
            )
        else:
            c.execute(
                """
                SELECT YEAR(b.FECHA) AS anio, COUNT(*) AS total,
                       mb.MOTIVO_BAJA AS motivo
                FROM BAJA_ANIMAL b
                LEFT JOIN MOTIVO_BAJA mb ON b.MOTIVO = mb.CLAVE
                WHERE b.FECHA IS NOT NULL
                GROUP BY YEAR(b.FECHA), b.MOTIVO
                ORDER BY anio
                """
            )
        bajas_raw = c.fetchall()
        bajas_por_anio = defaultdict(int)
        motivos_counter = Counter()
        for anio, total, motivo in bajas_raw:
            if anio:
                bajas_por_anio[int(anio)] += int(total)
            motivos_counter[motivo or "Sin motivo"] += int(total)

        # -- Altas por año (tabla CENSO) --
        try:
            if especie_filtro:
                c.execute(
                    f"""
                    SELECT YEAR(cs.FECHA_ALTA) AS anio, COUNT(*) AS total
                    FROM CENSO cs
                    INNER JOIN ANIMALES a ON cs.`{chip_col}` = a.`{chip_col}`
                    WHERE cs.FECHA_ALTA IS NOT NULL AND LOWER(TRIM(a.ESPECIE)) = LOWER(%s)
                    GROUP BY YEAR(cs.FECHA_ALTA)
                    ORDER BY anio
                    """,
                    [especie_filtro],
                )
            else:
                c.execute(
                    """
                    SELECT YEAR(FECHA_ALTA) AS anio, COUNT(*) AS total
                    FROM CENSO
                    WHERE FECHA_ALTA IS NOT NULL
                    GROUP BY YEAR(FECHA_ALTA)
                    ORDER BY anio
                    """
                )
            altas_raw = c.fetchall()
            altas_por_anio = {int(a): int(t) for a, t in altas_raw if a}
        except Exception as e:
            logger.warning("ESTADISTICAS: no se pudieron calcular altas por año: %s", e)
            altas_por_anio = {}

        # -- Distribución: nº de animales por propietario (0-5, con LEFT JOIN) --
        c.execute(
            """SELECT num_animales, COUNT(*) AS num_propietarios
               FROM (
                   SELECT p.DNI, COUNT(a.DNI_PROPIETARIO) AS num_animales
                   FROM PROPIETARIOS p
                   LEFT JOIN ANIMALES a ON p.DNI = a.DNI_PROPIETARIO
                   GROUP BY p.DNI
               ) sub
               WHERE num_animales <= 5
               GROUP BY num_animales
               ORDER BY num_animales"""
        )
        dist_raw = c.fetchall()
        dist_prop = {i: 0 for i in range(6)}
        for n_anim, n_prop in dist_raw:
            dist_prop[int(n_anim)] = int(n_prop)
        anim_por_prop = {
            (f"{k} animal{'es' if k != 1 else ''}"): dist_prop[k]
            for k in sorted(dist_prop)
        }

        conn.close()

        def _serie_counter(c):
            """Devuelve labels/values ordenados por frecuencia desc."""
            items = sorted(c.items(), key=lambda x: -x[1])
            return {"labels": [k for k, _ in items], "values": [v for _, v in items]}

        # Ordenar series temporales
        def serie(d):
            ks = sorted(d.keys())
            return {"labels": ks, "values": [d[k] for k in ks]}

        return jsonify(
            {
                "ok": True,
                "total_registrados": len(animales),
                "total_activos": total_activos,
                "especies": _serie_counter(especies),
                "sexos": _serie_counter(sexos),
                "peligrosos": _serie_counter(peligrosos),
                "esterilizados": _serie_counter(esterilizados),
                "nacimientos": serie(nacimientos),
                "bajas_por_anio": serie(bajas_por_anio),
                "altas_por_anio": serie(altas_por_anio),
                "motivos_baja": {
                    "labels": list(motivos_counter.keys()),
                    "values": list(motivos_counter.values()),
                },
                "anim_por_prop": {
                    "labels": list(anim_por_prop.keys()),
                    "values": list(anim_por_prop.values()),
                },
            }
        )
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/busqueda_global", methods=["GET"])
def busqueda_global():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify({"ok": True, "propietarios": [], "animales": []})
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        like = f"%{q}%"

        c.execute(
            """SELECT DNI, NOMBRE, PRIMER_APELLIDO, SEGUNDO_APELLIDO,
                      TELEFONO1, DOMICILIO
               FROM PROPIETARIOS
               WHERE DNI LIKE %s
                  OR PRIMER_APELLIDO LIKE %s
                  OR SEGUNDO_APELLIDO LIKE %s
                  OR NOMBRE LIKE %s
               LIMIT 10""",
            (like, like, like, like),
        )
        propietarios = [fila_a_dict(c, r) for r in c.fetchall()]

        c.execute(
            f"""SELECT a.`{chip_col}` AS N_CHIP, a.NOMBRE, a.ESPECIE,
                       a.RAZA, a.DNI_PROPIETARIO,
                       p.NOMBRE AS NOMBRE_PROP,
                       p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO
                FROM ANIMALES a
                LEFT JOIN PROPIETARIOS p ON a.DNI_PROPIETARIO = p.DNI
                WHERE a.`{chip_col}` LIKE %s OR a.NOMBRE LIKE %s
                LIMIT 10""",
            (like, like),
        )
        animales = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()
        return jsonify({"ok": True, "propietarios": propietarios, "animales": animales})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/alertas", methods=["GET"])
def alertas():
    try:
        import datetime

        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Columna de vacuna
        vacuna_col = None
        for nombre in (
            "FECHA_ULTIMA_VACUNA_ANTIRRABICA",
            "FECHA_ULTIMA_VACUNACION_ANTIRRABICA",
        ):
            c.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ANIMALES' "
                "AND COLUMN_NAME=%s",
                (nombre,),
            )
            if c.fetchone()[0]:
                vacuna_col = nombre
                break

        activos_where = (
            f"a.`{chip_col}` NOT IN "
            f"(SELECT b.`{chip_col}` FROM BAJA_ANIMAL b "
            f"WHERE b.`{chip_col}` IS NOT NULL)"
        )

        # Vacunas caducadas (> 1 año)
        vacunas = []
        if vacuna_col:
            hace_un_anio = (
                datetime.date.today() - datetime.timedelta(days=365)
            ).isoformat()
            c.execute(
                f"""SELECT a.`{chip_col}` AS N_CHIP, a.NOMBRE, a.ESPECIE,
                           a.`{vacuna_col}` AS FECHA_VACUNA,
                           a.DNI_PROPIETARIO,
                           p.NOMBRE AS NOMBRE_PROP,
                           p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO, p.TELEFONO1
                    FROM ANIMALES a
                    LEFT JOIN PROPIETARIOS p ON a.DNI_PROPIETARIO = p.DNI
                    WHERE {activos_where}
                      AND a.`{vacuna_col}` IS NOT NULL
                      AND a.`{vacuna_col}` < %s
                    ORDER BY a.`{vacuna_col}`
                    LIMIT 200""",
                (hace_un_anio,),
            )
            vacunas = [fila_a_dict(c, r) for r in c.fetchall()]

        # Animales próximos a baja por edad (>= 90 años)
        anio_actual = datetime.date.today().year
        anio_limite = anio_actual - 90
        c.execute(
            f"""SELECT a.`{chip_col}` AS N_CHIP, a.NOMBRE, a.ESPECIE,
                       a.ANIO_NACIMIENTO,
                       a.DNI_PROPIETARIO,
                       p.NOMBRE AS NOMBRE_PROP,
                       p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO, p.TELEFONO1
                FROM ANIMALES a
                LEFT JOIN PROPIETARIOS p ON a.DNI_PROPIETARIO = p.DNI
                WHERE {activos_where}
                  AND a.ANIO_NACIMIENTO IS NOT NULL
                  AND a.ANIO_NACIMIENTO <= %s
                  AND a.ANIO_NACIMIENTO > %s
                ORDER BY a.ANIO_NACIMIENTO
                LIMIT 100""",
            (anio_limite, anio_actual - 100),
        )
        proximos_baja = [fila_a_dict(c, r) for r in c.fetchall()]

        conn.close()
        return jsonify(
            {
                "ok": True,
                "vacunas_caducadas": vacunas,
                "proximos_baja": proximos_baja,
            }
        )
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ficha_animal/<chip>", methods=["GET"])
def ficha_animal(chip):
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Animal completo
        c.execute(f"SELECT * FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({"ok": False, "error": "Animal no encontrado"})
        animal = fila_a_dict(c, row)

        # Propietario
        dni = animal.get("DNI_PROPIETARIO")
        propietario = None
        if dni:
            c.execute("SELECT * FROM PROPIETARIOS WHERE DNI = %s", (dni,))
            p = c.fetchone()
            if p:
                propietario = fila_a_dict(c, p)

        # Seguros
        c.execute(f"SELECT * FROM SEGUROS WHERE `{chip_col}` = %s", (chip,))
        seguros = [fila_a_dict(c, r) for r in c.fetchall()]

        # Historial de baja (si existe)
        c.execute(
            f"""SELECT b.N_BAJA AS N_BAJA, b.FECHA AS FECHA_BAJA,
                       b.MOTIVO, h.OBSERVACIONES AS OBSERVACIONES,
                       mb.MOTIVO_BAJA AS MOTIVO_DESC
                FROM BAJA_ANIMAL b
                LEFT JOIN MOTIVO_BAJA mb ON b.MOTIVO = mb.CLAVE
                LEFT JOIN (
                    SELECT `{chip_col}` AS CHIP, OBSERVACIONES
                    FROM HISTORICO_MASCOTAS
                    WHERE ID_ESTADO = 2
                ) h ON h.CHIP = b.`{chip_col}`
                WHERE b.`{chip_col}` = %s""",
            (chip,),
        )
        bajas = [fila_a_dict(c, r) for r in c.fetchall()]

        conn.close()
        return jsonify(
            {
                "ok": True,
                "animal": animal,
                "propietario": propietario,
                "seguros": seguros,
                "bajas": bajas,
            }
        )
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/vencimientos", methods=["GET"])
def vencimientos():
    """Animales activos cuya vacuna antirrábica vence en los próximos N días."""
    try:
        import datetime

        dias = int(request.args.get("dias", 30))
        dias = max(1, min(dias, 365))

        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        # Detectar columna de vacuna
        vacuna_col = None
        for nombre in (
            "FECHA_ULTIMA_VACUNA_ANTIRRABICA",
            "FECHA_ULTIMA_VACUNACION_ANTIRRABICA",
        ):
            c.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='ANIMALES' "
                "AND COLUMN_NAME=%s",
                (nombre,),
            )
            if c.fetchone()[0]:
                vacuna_col = nombre
                break

        if not vacuna_col:
            conn.close()
            return jsonify(
                {"ok": True, "datos": [], "aviso": "Columna de vacuna no encontrada."}
            )

        hoy = datetime.date.today()
        vence_en = hoy + datetime.timedelta(days=dias)  # vencerán dentro de `dias` días

        # Animales activos cuya vacuna vence entre hoy-365 y hoy-365+dias
        c.execute(
            f"""SELECT a.`{chip_col}` AS N_CHIP,
                       a.NOMBRE, a.ESPECIE, a.RAZA,
                       a.`{vacuna_col}` AS FECHA_VACUNA,
                       a.DNI_PROPIETARIO,
                       p.NOMBRE       AS NOMBRE_PROP,
                       p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO,
                       p.TELEFONO1, pd.DOMICILIO AS DOMICILIO, pd.CP AS CP, pd.MUNICIPIO AS MUNICIPIO
                FROM ANIMALES a
                LEFT JOIN PROPIETARIOS p ON a.DNI_PROPIETARIO = p.DNI
                LEFT JOIN (SELECT DNI, MIN(CODIGO) AS codmin FROM PROPIETARIO_DIRECCION GROUP BY DNI) pdk ON pdk.DNI = p.DNI
                LEFT JOIN PROPIETARIO_DIRECCION pd ON pd.CODIGO = pdk.codmin
                WHERE a.`{chip_col}` NOT IN (
                    SELECT b.`{chip_col}` FROM BAJA_ANIMAL b
                    WHERE b.`{chip_col}` IS NOT NULL
                )
                  AND a.`{vacuna_col}` IS NOT NULL
                  AND DATE_ADD(a.`{vacuna_col}`, INTERVAL 1 YEAR) BETWEEN %s AND %s
                ORDER BY a.`{vacuna_col}`""",
            (hoy, vence_en),
        )
        rows = [fila_a_dict(c, r) for r in c.fetchall()]
        conn.close()

        # Calcular días restantes para cada animal
        for r in rows:
            fv = r.get("FECHA_VACUNA")
            if fv:
                try:
                    fv_date = datetime.date.fromisoformat(str(fv)[:10])
                    vence = fv_date.replace(year=fv_date.year + 1)
                    r["VENCE"] = str(vence)
                    r["DIAS_RESTANTES"] = (vence - hoy).days
                except Exception as e:
                    logger.debug("VENCIMIENTOS: fecha vacuna inválida %r: %s", fv, e)
                    r["VENCE"] = None
                    r["DIAS_RESTANTES"] = None

        return jsonify({"ok": True, "datos": rows, "dias": dias})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/ficha_propietario/<dni>", methods=["GET"])
def ficha_propietario(dni):
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)

        c.execute("SELECT * FROM PROPIETARIOS WHERE DNI = %s", (dni,))
        row = c.fetchone()
        if not row:
            conn.close()
            return jsonify({"ok": False, "error": "Propietario no encontrado"})
        prop = fila_a_dict(c, row)

        # Todos sus animales (activos e inactivos)
        c.execute(
            f"""SELECT a.`{chip_col}` AS N_CHIP, a.NOMBRE, a.ESPECIE, a.RAZA,
                       a.SEXO, a.COLOR, a.ANIO_NACIMIENTO, a.PELIGROSO, a.ESTERILIZADO,
                       CASE WHEN b.`{chip_col}` IS NOT NULL THEN 1 ELSE 0 END AS DADO_DE_BAJA
                FROM ANIMALES a
                LEFT JOIN BAJA_ANIMAL b ON a.`{chip_col}` = b.`{chip_col}`
                WHERE a.DNI_PROPIETARIO = %s
                ORDER BY DADO_DE_BAJA, a.NOMBRE""",
            (dni,),
        )
        animales = [fila_a_dict(c, r) for r in c.fetchall()]

        # Direcciones del propietario
        c.execute(
            "SELECT * FROM PROPIETARIO_DIRECCION WHERE DNI = %s ORDER BY CODIGO",
            (dni,),
        )
        direcciones = [fila_a_dict(c, r) for r in c.fetchall()]

        # Seguros
        c.execute(
            f"""SELECT s.*, a.NOMBRE AS NOMBRE_ANIMAL, a.ESPECIE
                FROM SEGUROS s
                LEFT JOIN ANIMALES a ON s.`{chip_col}` = a.`{chip_col}`
                WHERE a.DNI_PROPIETARIO = %s""",
            (dni,),
        )
        seguros = [fila_a_dict(c, r) for r in c.fetchall()]

        conn.close()
        return jsonify(
            {"ok": True, "propietario": prop, "animales": animales, "seguros": seguros, "direcciones": direcciones}
        )
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/logs", methods=["GET"])
def listar_logs():
    """Lista los ficheros de log disponibles (solo admin)."""
    try:
        ficheros = sorted(
            [f.name for f in LOG_DIR.glob("log_*.txt")],
            reverse=True,
        )
        # Incluir log.txt activo si existe
        activo = LOG_DIR / "log.txt"
        if activo.exists():
            ficheros.insert(0, "log.txt")
        return jsonify({"ok": True, "ficheros": ficheros})
    except Exception as e:
        _log_request_error("listar_logs", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auditoria", methods=["GET"])
def listar_auditoria():
    """Devuelve las entradas de auditoría. Solo administrador.
    Parámetros opcionales (query string):
      - desde, hasta  → rango de fechas 'YYYY-MM-DD'
      - rol           → admin | empleado | policia | sistema
      - usuario       → coincidencia parcial (case-insensitive)
      - accion        → coincidencia parcial (case-insensitive)
      - ip            → coincidencia parcial
      - limit         → máximo de entradas devueltas (por defecto 500, máx 5000)
    """
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    try:
        desde   = (request.args.get("desde")   or "").strip()
        hasta   = (request.args.get("hasta")   or "").strip()
        rol_f   = (request.args.get("rol")     or "").strip().lower()
        usr_f   = (request.args.get("usuario") or "").strip().lower()
        acc_f   = (request.args.get("accion")  or "").strip().lower()
        ip_f    = (request.args.get("ip")      or "").strip()
        try:
            limit = int(request.args.get("limit") or 500)
        except ValueError as e:
            logger.debug("AUDITORIA: limit inválido %r: %s", request.args.get("limit"), e)
            limit = 500
        limit = max(1, min(limit, 5000))

        if not _AUDIT_LOG_FILE.exists():
            return jsonify({"ok": True, "datos": [], "total": 0})

        entradas: list[dict] = []
        with open(_AUDIT_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    e = json.loads(linea)
                except Exception as _parse_err:
                    logger.debug("AUDITORIA: línea JSON inválida descartada: %s", _parse_err)
                    continue
                fecha = str(e.get("fecha", ""))[:10]  # YYYY-MM-DD
                if desde and fecha < desde:
                    continue
                if hasta and fecha > hasta:
                    continue
                if rol_f and rol_f not in str(e.get("rol", "")).lower():
                    continue
                if usr_f and usr_f not in str(e.get("usuario", "")).lower():
                    continue
                if acc_f and acc_f not in str(e.get("accion", "")).lower():
                    continue
                if ip_f and ip_f not in str(e.get("ip", "")):
                    continue
                entradas.append(e)

        total = len(entradas)
        # Últimas N entradas en orden cronológico inverso (más recientes primero)
        entradas = list(reversed(entradas[-limit:]))
        return jsonify({"ok": True, "datos": entradas, "total": total})
    except Exception as e:
        _log_request_error("listar_auditoria", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/auditoria/descargar", methods=["GET"])
def descargar_auditoria():
    """Descarga el fichero de auditoría completo (solo admin)."""
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    try:
        if not _AUDIT_LOG_FILE.exists():
            return jsonify({"ok": False, "error": "No hay registros de auditoría."}), 404
        return send_file(_AUDIT_LOG_FILE, as_attachment=True, download_name="auditoria.jsonl")
    except Exception as e:
        _log_request_error("descargar_auditoria", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/logs/<nombre>", methods=["GET"])
def descargar_log(nombre):
    """Descarga o muestra un fichero de log."""
    try:
        # Sanitizar: solo permitir nombres seguros
        if not nombre.replace("-", "").replace("_", "").replace(".", "").isalnum():
            return (
                jsonify({"ok": False, "error": "Nombre de fichero no permitido"}),
                400,
            )
        ruta = (LOG_DIR / nombre).resolve()
        if not str(ruta).startswith(str(LOG_DIR.resolve())):
            return jsonify({"ok": False, "error": "Acceso denegado"}), 403
        if not ruta.exists():
            return jsonify({"ok": False, "error": "Fichero no encontrado"}), 404
        modo = request.args.get("modo", "descargar")
        if modo == "ver":
            with open(ruta, "r", encoding="utf-8", errors="replace") as f:
                lineas = f.readlines()
            # Devolver las últimas 500 líneas
            return jsonify({"ok": True, "lineas": lineas[-500:], "total": len(lineas)})
        return send_file(ruta, as_attachment=True, download_name=nombre)
    except Exception as e:
        _log_request_error("descargar_log", e)
        return jsonify({"ok": False, "error": str(e)}), 500


# Endpoint — Logging desde frontend

@app.route("/api/log", methods=["POST"])
def recibir_log():
    """Endpoint para recibir y registrar errores desde el frontend."""
    try:
        d = request.get_json()
        if not d:
            return jsonify({"ok": False, "error": "JSON requerido"}), 400
        
        mensaje = d.get("mensaje", "Error sin mensaje")
        tipo = d.get("tipo", "ERROR")  # ERROR, WARNING, INFO
        contexto = d.get("contexto", "")
        stack = d.get("stack", "")
        
        # Registrar en el logger
        log_msg = f"FRONTEND | {tipo} | {mensaje}"
        if contexto:
            log_msg += f" | Contexto: {contexto}"
        if stack:
            log_msg += f"\n{stack}"
        
        if tipo == "ERROR":
            logger.error(log_msg)
        elif tipo == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
        
        return jsonify({"ok": True, "mensaje": "Log registrado"})
    except Exception as e:
        logger.error(f"Error al recibir log desde frontend: {e}\n{traceback.format_exc()}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Tabla INCIDENCIAS ─────────────────────────────────────────────────────────
def _init_incidencias():
    """Crea la tabla INCIDENCIAS si no existe."""
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("""
            CREATE TABLE IF NOT EXISTS INCIDENCIAS (
                ID         INT AUTO_INCREMENT PRIMARY KEY,
                N_CHIP     VARCHAR(50)  NOT NULL,
                TIPO       VARCHAR(100) NOT NULL,
                DESCRIPCION TEXT,
                FECHA      DATETIME     NOT NULL,
                ROL_AGENTE VARCHAR(20)  DEFAULT 'admin',
                AGENTE     VARCHAR(100) DEFAULT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        # Añadir columna AGENTE si la tabla ya existía sin ella
        try:
            c.execute("ALTER TABLE INCIDENCIAS ADD COLUMN AGENTE VARCHAR(100) DEFAULT NULL")
            conn.commit()
        except mysql.connector.Error as e:
            # Error 1060 = duplicate column (la columna ya existía); lo demás sí avisar.
            if getattr(e, "errno", None) != 1060:
                logger.warning("ALTER TABLE INCIDENCIAS AGENTE falló: %s", e)
        conn.commit()
        conn.close()
        logger.info("DB: tabla INCIDENCIAS lista")
    except Exception as e:
        logger.warning("DB: no se pudo crear INCIDENCIAS: %s", e)


# ── Endpoints policía ─────────────────────────────────────────────────────────

def _req_policia_o_admin():
    """Devuelve el payload si el token es de admin o policia, None en caso contrario."""
    token = request.headers.get("X-Token", "")
    payload = _validar_token(token)
    if payload and payload["rol"] in ("admin", "policia"):
        return payload
    return None


@app.route("/api/policia/chip/<chip>", methods=["GET"], strict_slashes=False)
def policia_buscar_chip(chip):
    """Devuelve el animal y su propietario por número de chip."""
    if not _req_policia_o_admin():
        return jsonify({"ok": False, "error": "Acceso no autorizado."}), 403
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(f"SELECT * FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        animal_row = c.fetchone()
        if not animal_row:
            conn.close()
            return jsonify({"ok": False, "error": "Animal no encontrado."})
        animal = fila_a_dict(c, animal_row)
        # Buscar propietario
        propietario = None
        dni = animal.get("DNI_PROPIETARIO")
        if dni:
            c.execute("SELECT * FROM PROPIETARIOS WHERE DNI = %s", (dni,))
            prop_row = c.fetchone()
            if prop_row:
                propietario = fila_a_dict(c, prop_row)
        conn.close()
        return jsonify({"ok": True, "animal": animal, "propietario": propietario})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/incidencias", methods=["POST"], strict_slashes=False)
def registrar_incidencia():
    """Registra una incidencia. Requiere rol admin o policia."""
    payload = _req_policia_o_admin()
    if not payload:
        return jsonify({"ok": False, "error": "Acceso no autorizado."}), 403
    data = request.get_json(silent=True) or {}
    chip = data.get("chip", "").strip()
    tipo = data.get("tipo", "").strip()
    descripcion = data.get("descripcion", "").strip()
    if not chip or not tipo:
        return jsonify({"ok": False, "error": "Chip y tipo de incidencia son obligatorios."})
    try:
        conn = get_conn()
        c = cur(conn)
        chip_col = detectar_chip(c)
        c.execute(f"SELECT COUNT(*) FROM ANIMALES WHERE `{chip_col}` = %s", (chip,))
        if c.fetchone()[0] == 0:
            conn.close()
            return jsonify({"ok": False, "error": "No existe ningún animal con ese chip."})
        # Determinar nombre del agente
        agente_nombre = None
        if payload["rol"] == "policia":
            username = payload.get("username", "")
            pol_user = _cargar_auth().get("policia_usuarios", {}).get(username, {})
            agente_nombre = pol_user.get("nombre", username)
        elif payload["rol"] == "admin":
            agente_nombre = "Administrador"
        c.execute(
            "INSERT INTO INCIDENCIAS (N_CHIP, TIPO, DESCRIPCION, FECHA, ROL_AGENTE, AGENTE) VALUES (%s,%s,%s,%s,%s,%s)",
            (chip, tipo, descripcion, datetime.now(), payload["rol"], agente_nombre)
        )
        conn.commit()
        inc_id = c.lastrowid
        conn.close()
        logger.info("POL: incidencia #%d registrada — chip=%s tipo=%s", inc_id, chip, tipo)
        _log_auditoria("crear_incidencia", {
            "id": inc_id,
            "N_CHIP": chip,
            "tipo": tipo,
            "descripcion": descripcion[:500] if descripcion else "",
        })
        return jsonify({"ok": True, "id": inc_id})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        _log_auditoria("crear_incidencia", {"N_CHIP": chip, "error": str(e)[:200]}, exito=False)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/incidencias", methods=["GET"], strict_slashes=False)
def listar_incidencias():
    """Lista las incidencias. Requiere rol admin o policia."""
    if not _req_policia_o_admin():
        return jsonify({"ok": False, "error": "Acceso no autorizado."}), 403
    try:
        conn = get_conn()
        c = cur(conn)
        c.execute("SELECT * FROM INCIDENCIAS ORDER BY FECHA DESC LIMIT 200")
        rows = c.fetchall()
        conn.close()
        return jsonify({"ok": True, "datos": [fila_a_dict(c, r) for r in rows]})
    except Exception as e:
        _log_request_error(request.endpoint or "unknown", e)
        return jsonify({"ok": False, "error": str(e)}), 500


def _bloquear_usuarios_inactivos():
    """Tarea programada: desactiva cuentas que lleven más de 6 meses sin acceder.
    Aplica a policía y empleados (dispositivos). No afecta al admin.
    """
    try:
        auth    = _cargar_auth()
        cambios = 0

        # Policía
        for username, user in auth.get("policia_usuarios", {}).items():
            if user.get("activo", False) and _check_inactividad(user.get("ultimo_acceso")):
                auth["policia_usuarios"][username]["activo"] = False
                cambios += 1
                logger.info("SCHEDULER: cuenta policía bloqueada por inactividad — %s", username)
                _log_auditoria("bloqueo_inactividad",
                               {"username": username, "motivo": "sin_acceso_6_meses"})
                # Revocar tokens activos en memoria
                to_revoke = [t for t, p in list(_TOKENS.items())
                             if p.get("rol") == "policia" and p.get("username") == username]
                for t in to_revoke:
                    if _TOKENS[t].get("persistido"):
                        _eliminar_token_persistido(t)
                    del _TOKENS[t]

        # Empleados (por dispositivo)
        for device_id, dev in auth.get("devices", {}).items():
            if dev.get("activo", True) and _check_inactividad(dev.get("ultimo_acceso")):
                auth["devices"][device_id]["activo"] = False
                cambios += 1
                logger.info("SCHEDULER: dispositivo empleado bloqueado por inactividad — %s", device_id[:12])
                _log_auditoria("bloqueo_inactividad",
                               {"device_id": device_id[:12], "motivo": "sin_acceso_6_meses"})

        if cambios:
            _guardar_auth(auth)
            logger.info("SCHEDULER: %d cuenta(s) bloqueadas por inactividad", cambios)
    except Exception as e:
        logger.error("SCHEDULER: error en _bloquear_usuarios_inactivos: %s", e)


# ── Backups automáticos ──────────────────────────────────────────────────────

BACKUP_DIR = Path(os.environ.get("BACKUP_DIR", "db/backups"))
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))


def _sql_escape(valor) -> str:
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, (bytes, bytearray)):
        return "0x" + bytes(valor).hex()
    if isinstance(valor, (datetime, date)):
        return "'" + valor.isoformat(sep=" ") + "'"
    s = str(valor).replace("\\", "\\\\").replace("'", "''").replace("\x00", "")
    return "'" + s + "'"


def _dump_database_a_sql(fh) -> dict:
    """Escribe un volcado SQL completo a `fh`. Devuelve estadísticas."""
    stats = {"tablas": 0, "filas": 0}
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        tablas = [r[0] for r in cur.fetchall()]
        fh.write(f"-- Backup censo_animales {datetime.now().isoformat()}\n")
        fh.write("SET FOREIGN_KEY_CHECKS=0;\n")
        fh.write("SET NAMES utf8mb4;\n\n")
        for tabla in tablas:
            cur.execute(f"SHOW CREATE TABLE `{tabla}`")
            create_sql = cur.fetchone()[1]
            fh.write(f"DROP TABLE IF EXISTS `{tabla}`;\n")
            fh.write(create_sql + ";\n\n")
            cur.execute(f"SELECT * FROM `{tabla}`")
            cols = [d[0] for d in cur.description]
            col_list = ", ".join(f"`{c}`" for c in cols)
            filas_tabla = 0
            for row in cur.fetchall():
                vals = ", ".join(_sql_escape(v) for v in row)
                fh.write(f"INSERT INTO `{tabla}` ({col_list}) VALUES ({vals});\n")
                filas_tabla += 1
            fh.write("\n")
            stats["tablas"] += 1
            stats["filas"] += filas_tabla
        fh.write("SET FOREIGN_KEY_CHECKS=1;\n")
    finally:
        cur.close()
        conn.close()
    return stats


def _ejecutar_backup() -> dict:
    """Crea un backup comprimido y verifica integridad. Devuelve metadatos."""
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"backup_{ts}.sql.gz"
    ruta = BACKUP_DIR / filename
    try:
        with gzip.open(ruta, "wt", encoding="utf-8") as fh:
            stats = _dump_database_a_sql(fh)
        # Verificación: abrir y leer cabecera
        with gzip.open(ruta, "rt", encoding="utf-8") as fh:
            cabecera = fh.read(200)
        if "SET NAMES utf8mb4" not in cabecera:
            raise RuntimeError("Verificación del backup fallida: cabecera inválida")
        tamano = ruta.stat().st_size
        logger.info("BACKUP: creado %s (%d tablas, %d filas, %d bytes)",
                    filename, stats["tablas"], stats["filas"], tamano)
        return {
            "ok": True,
            "archivo": filename,
            "tamano": tamano,
            "tablas": stats["tablas"],
            "filas": stats["filas"],
            "fecha": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("BACKUP: fallo creando %s: %s", filename, e)
        try:
            if ruta.exists():
                ruta.unlink()
        except OSError as unlink_err:
            logger.warning("BACKUP: no se pudo eliminar archivo parcial %s: %s", ruta, unlink_err)
        return {"ok": False, "error": str(e)}


def _limpiar_backups_antiguos() -> int:
    """Elimina backups con antigüedad superior a BACKUP_RETENTION_DAYS."""
    limite = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    eliminados = 0
    try:
        for archivo in BACKUP_DIR.glob("backup_*.sql.gz"):
            try:
                mtime = datetime.fromtimestamp(archivo.stat().st_mtime)
                if mtime < limite:
                    archivo.unlink()
                    eliminados += 1
            except Exception as e:
                logger.warning("BACKUP: no se pudo borrar %s: %s", archivo.name, e)
        if eliminados:
            logger.info("BACKUP: %d archivo(s) antiguos eliminados", eliminados)
    except Exception as e:
        logger.error("BACKUP: error en limpieza: %s", e)
    return eliminados


def _backup_diario():
    """Tarea programada: crea backup y limpia antiguos."""
    resultado = _ejecutar_backup()
    if resultado.get("ok"):
        _limpiar_backups_antiguos()
        try:
            _log_auditoria("backup_automatico", {
                "archivo": resultado["archivo"],
                "tamano": resultado["tamano"],
                "tablas": resultado["tablas"],
                "filas": resultado["filas"],
            })
        except Exception as e:
            logger.warning("BACKUP: no se pudo auditar backup_automatico: %s", e)


@app.route("/api/admin/backups", methods=["GET"])
def admin_backups_listar():
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    archivos = []
    for archivo in sorted(BACKUP_DIR.glob("backup_*.sql.gz"), reverse=True):
        try:
            st = archivo.stat()
            archivos.append({
                "nombre": archivo.name,
                "tamano": st.st_size,
                "fecha": datetime.fromtimestamp(st.st_mtime).isoformat(),
            })
        except OSError as e:
            logger.warning("BACKUP: no se pudo leer metadatos de %s: %s", archivo.name, e)
            continue
    return jsonify({"ok": True, "backups": archivos, "retencion_dias": BACKUP_RETENTION_DAYS})


@app.route("/api/admin/backups/crear", methods=["POST"])
def admin_backups_crear():
    payload = _req_admin()
    if not payload:
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    resultado = _ejecutar_backup()
    if resultado.get("ok"):
        try:
            _log_auditoria("backup_manual", {
                "archivo": resultado["archivo"],
                "tamano": resultado["tamano"],
                "tablas": resultado["tablas"],
                "filas": resultado["filas"],
            })
        except Exception as e:
            logger.warning("BACKUP: no se pudo auditar backup_manual: %s", e)
        _limpiar_backups_antiguos()
        return jsonify(resultado)
    return jsonify(resultado), 500


@app.route("/api/admin/backups/<nombre>", methods=["GET"])
def admin_backups_descargar(nombre):
    if not _req_admin():
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    # Evitar path traversal: el nombre debe coincidir con el patrón esperado
    if not nombre.startswith("backup_") or not nombre.endswith(".sql.gz") or "/" in nombre or "\\" in nombre or ".." in nombre:
        return jsonify({"ok": False, "error": "Nombre de archivo inválido."}), 400
    ruta = BACKUP_DIR / nombre
    if not ruta.exists() or not ruta.is_file():
        return jsonify({"ok": False, "error": "Archivo no encontrado."}), 404
    return send_file(str(ruta), as_attachment=True, download_name=nombre, mimetype="application/gzip")


def _ejecutar_restore(ruta) -> dict:
    """Restaura un backup .sql.gz en la base de datos actual.
    Antes de restaurar, crea un backup de seguridad pre-restore.
    """
    # 1) Backup de seguridad pre-restore
    pre = _ejecutar_backup()
    if not pre.get("ok"):
        return {"ok": False, "error": "No se pudo crear backup de seguridad previo: " + str(pre.get("error"))}
    sentencias_ejecutadas = 0
    errores = []
    try:
        with gzip.open(ruta, "rt", encoding="utf-8") as fh:
            contenido = fh.read()
    except Exception as e:
        logger.error("RESTORE: no se pudo leer el backup %s: %s", ruta, e)
        return {"ok": False, "error": f"No se pudo leer el backup: {e}"}

    # División ingenua por ';\n' — nuestros dumps son lo bastante simples
    sentencias = [s.strip() for s in contenido.split(";\n") if s.strip() and not s.strip().startswith("--")]
    conn = None
    try:
        conn = get_conn()
        c = conn.cursor()
        for sql in sentencias:
            try:
                c.execute(sql)
                sentencias_ejecutadas += 1
            except Exception as e:
                logger.warning("RESTORE: sentencia falló (%s...): %s", sql[:80], e)
                errores.append(f"{sql[:80]}… → {e}")
        conn.commit()
    except Exception as e:
        logger.exception("RESTORE: fallo al ejecutar: %s", e)
        return {"ok": False, "error": str(e), "pre_restore": pre.get("archivo")}
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.debug("RESTORE: error cerrando conexión: %s", e)

    return {
        "ok": True,
        "sentencias": sentencias_ejecutadas,
        "errores": errores[:10],
        "pre_restore": pre.get("archivo"),
    }


@app.route("/api/admin/backups/<nombre>/restaurar", methods=["POST"])
def admin_backups_restaurar(nombre):
    payload = _req_admin()
    if not payload:
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    if not nombre.startswith("backup_") or not nombre.endswith(".sql.gz") or "/" in nombre or "\\" in nombre or ".." in nombre:
        return jsonify({"ok": False, "error": "Nombre de archivo inválido."}), 400
    ruta = BACKUP_DIR / nombre
    if not ruta.exists() or not ruta.is_file():
        return jsonify({"ok": False, "error": "Archivo no encontrado."}), 404

    # Requerir confirmación explícita en el cuerpo
    data = request.get_json(silent=True) or {}
    if data.get("confirmacion") != "RESTAURAR":
        return jsonify({"ok": False, "error": "Se requiere confirmación explícita (confirmacion=RESTAURAR)."}), 400

    resultado = _ejecutar_restore(ruta)
    try:
        _log_auditoria("backup_restaurar", {
            "archivo": nombre,
            "ok": resultado.get("ok"),
            "sentencias": resultado.get("sentencias"),
            "errores_muestra": resultado.get("errores"),
            "pre_restore": resultado.get("pre_restore"),
        }, exito=bool(resultado.get("ok")))
    except Exception as e:
        logger.warning("BACKUP: no se pudo auditar backup_restaurar: %s", e)
    if resultado.get("ok"):
        return jsonify(resultado)
    return jsonify(resultado), 500


@app.route("/api/admin/backups/<nombre>", methods=["DELETE"])
def admin_backups_eliminar(nombre):
    payload = _req_admin()
    if not payload:
        return jsonify({"ok": False, "error": "Se requiere sesión de administrador."}), 403
    if not nombre.startswith("backup_") or not nombre.endswith(".sql.gz") or "/" in nombre or "\\" in nombre or ".." in nombre:
        return jsonify({"ok": False, "error": "Nombre de archivo inválido."}), 400
    ruta = BACKUP_DIR / nombre
    if not ruta.exists():
        return jsonify({"ok": False, "error": "Archivo no encontrado."}), 404
    try:
        ruta.unlink()
        try:
            _log_auditoria("backup_eliminar", {"archivo": nombre})
        except Exception as e:
            logger.warning("BACKUP: no se pudo auditar backup_eliminar: %s", e)
        return jsonify({"ok": True})
    except Exception as e:
        logger.error("BACKUP: no se pudo eliminar %s: %s", nombre, e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ── Arranque ──────────────────────────────────────────────────────────────────

# Inicializar scheduler (tanto para `python app.py` como para Docker)
try:
    if not hasattr(app, '_scheduler_initialized'):
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            baja_automatica_por_edad,
            trigger="cron",
            hour=1,
            minute=0,
            id="baja_por_edad",
            replace_existing=True,
        )
        scheduler.add_job(
            _cleanup_old_logs,
            trigger="cron",
            hour=2,
            minute=0,
            id="cleanup_logs",
            replace_existing=True,
        )
        scheduler.add_job(
            _bloquear_usuarios_inactivos,
            trigger="cron",
            hour=3,
            minute=0,
            id="bloqueo_inactividad",
            replace_existing=True,
        )
        scheduler.add_job(
            _backup_diario,
            trigger="cron",
            hour=4,
            minute=0,
            id="backup_diario",
            replace_existing=True,
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
        app._scheduler_initialized = True
except Exception as e:
    logger.error(f"Error initializing scheduler: {e}")

try:
    aplicar_unique_chip()
except Exception as e:
    logger.error(f"Error applying unique chip constraint: {e}")

try:
    baja_automatica_por_edad()
except Exception as e:
    logger.error(f"Error processing age-based withdrawals: {e}")

try:
    _cargar_tokens_persistidos()
except Exception as e:
    logger.error(f"Error loading persisted tokens: {e}")

try:
    _init_incidencias()
except Exception as e:
    logger.error(f"Error initializing INCIDENCIAS table: {e}")

if __name__ == "__main__":
    print(f"API conectando a {MARIADB['host']}:{MARIADB['port']}/{MARIADB['database']}")
    app.run(debug=False, host="0.0.0.0", port=5000)