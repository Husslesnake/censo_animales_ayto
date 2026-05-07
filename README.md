# Censo Municipal de Animales

Aplicación web para la gestión del padrón municipal de animales del Ayuntamiento de Navalcarnero.

## Estructura

```
├── docker-compose.yml        Orquestación de todos los servicios
├── nginx.conf                Servidor web (puertos 80 empleado / 8181 admin)
├── api/
│   ├── Dockerfile            Imagen del backend Flask
│   ├── requirements.txt      Dependencias de producción
│   ├── requirements-dev.txt  Dependencias de tests
│   └── app.py                API REST (autenticación, censo, auditoría, backups)
├── web/
│   ├── index.html            SPA con includes SSI
│   ├── manifest.json         Manifest PWA
│   ├── sw.js                 Service worker
│   ├── pages/                Vistas (propietarios, animales, logs, etc.)
│   ├── partials/             Cabecera, login, modales
│   ├── css/                  Estilos
│   └── js/                   auth, ui, auditoria, backups, policia, …
├── db/
│   ├── censo_animales.sql    Esquema inicial
│   └── backups/              Copias automáticas (mounted)
├── logs/                     Rotación diaria (log.txt, auditoria.jsonl)
├── tests/                    Pytest (conftest + test_*.py)
├── Manual_Administrador.md   Guía del administrador
└── Manual_Empleado.md        Guía del empleado y policía
```

## Arrancar

```bash
docker compose up -d --build
```

Disponible en:

- `http://<IP-servidor>` (puerto 80) — empleados y policía.
- `http://localhost:8181` — panel de administrador (solo desde el propio equipo).

## Parar

```bash
docker compose down
```

## Variables de entorno (api)

| Variable                 | Por defecto          | Descripción                                     |
|--------------------------|----------------------|-------------------------------------------------|
| `DB_HOST`                | `mariadb`            | Host de la base de datos                        |
| `DB_PORT`                | `3306`               | Puerto                                          |
| `DB_USER`                | `root`               | Usuario                                         |
| `DB_PASSWORD`            | `123`                | Contraseña                                      |
| `DB_NAME`                | `censo_animales`     | Base de datos                                   |
| `LOG_DIR`                | `logs`               | Directorio de logs y auditoría                  |
| `AUTH_FILE`              | `auth.json`          | Fichero de credenciales y tokens                |
| `BACKUP_DIR`             | `db/backups`         | Directorio donde se guardan los backups         |
| `BACKUP_RETENTION_DAYS`  | `30`                 | Retención de backups en días                    |

## Tests

```bash
pip install -r api/requirements-dev.txt
python -m pytest
```

## Documentación

Toda la documentación está en PDF. Para regenerarla tras editar las fuentes:

```bash
python scripts/generar_manuales.py        # Manual_Administrador / _Empleado
python scripts/generar_docs_tecnicos.py   # docs/*.pdf, CHANGELOG, CONTRIBUTING, Manual_Policia
```

### Manuales de usuario
- [Manual del administrador](Manual_Administrador.pdf)
- [Manual del empleado](Manual_Empleado.pdf)
- [Manual del agente de policía](Manual_Policia.pdf)

### Técnica
- [Arquitectura](docs/ARQUITECTURA.pdf)
- [Referencia de la API](docs/API.pdf)
- [Base de datos y migraciones](docs/BASE_DE_DATOS.pdf)
- [Despliegue](docs/DESPLIEGUE.pdf)
- [Guía de desarrollo](docs/DESARROLLO.pdf)
- [Seguridad y privacidad](docs/SEGURIDAD.pdf)

### Proyecto
- [Changelog](CHANGELOG.pdf)
- [Cómo contribuir](CONTRIBUTING.pdf)
- [README sin Docker](README_SIN_DOCKER.md)
