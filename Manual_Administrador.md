# Manual del administrador

Guía de uso y operación del Censo Municipal de Animales para el rol **administrador**.

---

## 1. Acceso

El administrador se conecta desde el propio equipo servidor a:

```
http://localhost:8181
```

Este puerto solo es accesible localmente (nginx lo escucha en `127.0.0.1`).

### 1.1 Primer arranque

Si aún no se ha configurado contraseña, al entrar aparece el modal **"Crear contraseña de administrador"**. Mínimo 6 caracteres.

### 1.2 Inicio de sesión

- La casilla **"Recordar sesión"** mantiene la sesión abierta un año (almacenada en `localStorage`). Sin ella, la sesión dura hasta cerrar el navegador.
- Tras **5 intentos fallidos** en 5 minutos se bloquea temporalmente el acceso. Tras **20 intentos fallidos por IP** se bloquea esa IP.

### 1.3 Cambio y caducidad de contraseña

- Menú lateral → **"Cambiar contraseña"**.
- Requisitos para cuentas nominales (empleado/policía): 8 caracteres, mayúscula, minúscula, número y carácter especial.
- Las contraseñas caducan cada **365 días**; al expirar se fuerza el cambio en el próximo inicio de sesión.

---

## 2. Pestañas del panel

| Pestaña          | Uso                                                        |
|------------------|------------------------------------------------------------|
| Inicio           | Resumen y alertas del sistema                              |
| Propietarios     | Alta, consulta y gestión de direcciones                    |
| Animales         | Alta, modificación, vacunas, esterilizado, seguro          |
| Seguros          | Pólizas asociadas a chip                                   |
| Baja de Animal   | Bajas por motivo, muerte o traslado                        |
| Estadísticas     | Gráficos agregados                                         |
| Logs             | Ficheros de log del servidor                               |
| Auditoría        | Eventos con diff antes/después                             |
| Agentes          | Cuentas de policía                                         |
| Empleados        | Cuentas nominales de empleado                              |
| Backups          | Copias de seguridad de la base de datos                    |
| Consulta         | Buscador transversal por DNI, chip o nombre                |

---

## 3. Gestión de usuarios

### 3.1 Empleados (pestaña "Empleados")

- **Crear cuenta**: usuario, nombre, contraseña inicial.
- La cuenta se marca como **temporal**: el empleado *debe* cambiar su contraseña la primera vez que inicie sesión.
- **Restablecer contraseña**: genera una nueva temporal; el empleado volverá a pasar por cambio forzado.
- **Activar/desactivar**: una cuenta desactivada no puede iniciar sesión.
- Tras **6 meses sin iniciar sesión** una cuenta se bloquea automáticamente por inactividad.

### 3.2 Agentes de policía (pestaña "Agentes")

Misma gestión que empleados (crear, restablecer, activar/desactivar). Los agentes acceden desde el puerto público (80) pulsando **"Acceso de Policía Municipal"** en la pantalla de login.

### 3.3 Recuperación de contraseña

Si un usuario pulsa **"¿Olvidaste tu contraseña?"**, la solicitud se registra en `logs/auditoria.jsonl` (acción `solicitud_recuperacion`). El administrador debe **restablecer manualmente** la contraseña desde la pestaña correspondiente.

---

## 4. Auditoría (pestaña "Auditoría")

Registra todas las acciones que alteran datos o cuentas:

- **Creación, modificación y baja** de propietarios y animales.
- **Diff antes/después** en modificaciones de animal (campo por campo).
- Gestión de cuentas (crear, modificar, eliminar, bloquear).
- Backups (manual, automático, restauración, eliminación).
- Solicitudes de recuperación de contraseña.
- Bloqueos por inactividad o intentos fallidos.

**Filtros**: fecha, rol, acción, usuario, IP. Botón **"Ver"** muestra el JSON completo. **"Descargar"** exporta `auditoria.jsonl`.

---

## 5. Backups (pestaña "Backups")

### 5.1 Copia automática diaria

- Se ejecuta cada día a las **04:00**.
- Formato: `backup_YYYY-MM-DD_HHMMSS.sql.gz` (dump SQL completo comprimido con gzip, verificado).
- Retención: **30 días**; los más antiguos se borran automáticamente.
- Ubicación: `db/backups/` (montado como volumen desde `./db/backups` del host).

### 5.2 Acciones manuales

| Botón          | Efecto                                                                  |
|----------------|-------------------------------------------------------------------------|
| Crear ahora    | Ejecuta un backup inmediato.                                            |
| Actualizar     | Refresca el listado.                                                    |
| Descargar      | Descarga el `.sql.gz` al equipo.                                        |
| Restaurar      | Sobrescribe la BD actual con el backup elegido (pide confirmación).     |
| Eliminar       | Borra el archivo del servidor.                                          |

### 5.3 Restauración

Antes de restaurar, **se crea automáticamente un backup de seguridad pre-restore** del estado actual. Si algo sale mal, ese backup queda disponible para revertir.

Confirmación: hay que escribir la palabra `RESTAURAR` cuando el sistema lo pida.

---

## 6. Logs (pestaña "Logs")

- Un fichero por día: `log_YYYY-MM-DD.txt` (rotación diaria, 90 días de retención).
- Contienen errores, accesos y avisos del servidor.
- Auditoría se guarda aparte en `auditoria.jsonl`.

---

## 7. Estadísticas

Gráficos agregados: razas, edad, estado (vivo/baja), esterilizado, cobertura de seguro, nacimientos por año. Los datos se calculan al vuelo con filtros.

---

## 8. PWA — instalación en móvil/tablet

La aplicación es instalable como app:

1. Abrir la URL pública en Chrome/Edge (Android) o Safari (iOS).
2. Menú del navegador → **"Instalar aplicación"** / **"Añadir a pantalla de inicio"**.
3. Se crea un icono que abre la app en modo pantalla completa, con atajo directo al panel de **Policía**.

Funciona sin conexión para consultas ya cacheadas (chips, propietarios, incidencias). Las mutaciones requieren conectividad.

---

## 9. Mantenimiento

### 9.1 Arranque y parada

```bash
docker compose up -d --build      # arrancar (reconstruye si hay cambios)
docker compose down               # parar
docker compose logs -f api        # seguir logs del backend
docker compose restart api        # reiniciar solo el backend
```

### 9.2 Actualización tras modificar el backend

```bash
docker compose up -d --build api
```

### 9.3 Tests

```bash
pip install -r api/requirements-dev.txt
python -m pytest
```

35 tests cubren: fortaleza de contraseña, bcrypt y migración SHA-256→bcrypt, rate-limit y bloqueo, diff de auditoría, endpoints de backups con validaciones de seguridad.

### 9.4 Variables de entorno

Se configuran en `docker-compose.yml` (servicio `api`). Ver la tabla en el [README](README.md).

---

## 10. Seguridad

- **Hashing**: bcrypt (rounds=12). Las contraseñas SHA-256 antiguas se migran automáticamente a bcrypt en el primer inicio de sesión exitoso.
- **Rate limiting**: 5 fallos por usuario y 20 por IP en ventana de 5 minutos.
- **Bloqueo automático** por intentos consecutivos e inactividad (6 meses).
- **Tokens**: expiración 8 horas sin "recordar", 1 año con "recordar". Se pueden revocar reiniciando la API.
- **Path traversal** y nombres inválidos rechazados en todos los endpoints de archivos.
- **Separación por puertos**: admin solo desde localhost:8181; resto por el puerto público 80.
