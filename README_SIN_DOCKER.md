# Censo Municipal de Animales — Modo local sin Docker

Esta variante arranca toda la aplicación en un solo proceso Python, sin
Docker, sin nginx y sin phpMyAdmin. Solo necesitas Python 3.10+ y un
servidor MariaDB/MySQL accesible localmente.

## 1. Requisitos

- **Python 3.10 o superior**
- **MariaDB 10.5+ o MySQL 8+** corriendo en `127.0.0.1:3306`
  (cualquier instalador oficial sirve: MariaDB para Windows, XAMPP,
  Laragon, MySQL Community, etc.)
- Usuario `root` con contraseña `123` por defecto. Para cambiarlo, edita
  las variables al final de este README.

## 2. Instalación

```bash
# Windows
start.bat initdb     # crea la BD, carga el dump y aplica migraciones
start.bat            # arranca la aplicación

# Linux / macOS
chmod +x start.sh
./start.sh initdb
./start.sh
```

El primer arranque crea un entorno virtual `.venv/` e instala las
dependencias de `requirements.txt`.

## 3. Acceso

| Rol         | URL                       | Notas                            |
|-------------|---------------------------|----------------------------------|
| Empleados   | http://localhost:8000     | Acceso público                   |
| Admin       | http://localhost:8181     | Recibe `X-Admin-Access: true`    |
| API interna | http://127.0.0.1:5000/api | Solo para depuración             |

Por defecto se carga el `auth.json` del proyecto. Si no existe, la web
te guiará para crear el usuario admin inicial.

## 4. Variables de entorno (opcionales)

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123
DB_NAME=censo_animales
LOG_DIR=./logs
AUTH_FILE=./auth.json
```

En Windows: `set DB_PASSWORD=otra` antes de `start.bat`.
En Linux/macOS: `DB_PASSWORD=otra ./start.sh`.

## 5. Estructura

- `run_local.py` — lanzador (API + web empleados + web admin)
- `init_db_local.py` — crea BD, carga dump y migraciones
- `api/` — backend Flask
- `web/` — frontend (HTML/CSS/JS)
- `db/censo_animales.sql` — dump base
- `db/migrations/*.sql` — migraciones aplicadas en orden alfabético
- `scripts/` — utilidades (datos de prueba, etc.)

## 6. Detener

`Ctrl+C` en la consola. Los hilos están marcados como daemon, por lo
que el proceso termina limpiamente.

## 7. Volver a Docker

Los archivos `docker-compose.yml`, `nginx.conf` y los `Dockerfile`
siguen en su sitio. El modo local **no** los toca.
