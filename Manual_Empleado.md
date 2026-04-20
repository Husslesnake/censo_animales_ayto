# Manual del empleado y policía

Guía de uso del Censo Municipal de Animales para los roles **empleado** y **policía**.

---

## 1. Acceso

Desde cualquier equipo conectado a la red municipal:

```
http://<IP-del-servidor>
```

En la pantalla de login hay dos formas de entrar:

- **Acceso de empleado** (por defecto): usuario + contraseña.
- **Acceso de Policía Municipal**: pulsar el enlace inferior; usa usuario + contraseña de agente.

### 1.1 Recordar sesión

Marcando **"Recordar sesión"** la sesión dura hasta un año en ese dispositivo. Sin marcar, se cierra al cerrar el navegador.

### 1.2 Primer inicio de sesión

La primera vez que accedas, el sistema te obligará a **cambiar la contraseña temporal** que te dio el administrador. No podrás usar la app hasta establecer una contraseña propia que cumpla:

- Mínimo 8 caracteres.
- Al menos una mayúscula, una minúscula, un número y un carácter especial.
- Distinta de la anterior.

La contraseña **caduca a los 365 días**; cuando expire, se te pedirá cambiarla de nuevo al iniciar sesión.

### 1.3 Olvidé mi contraseña

Pulsa **"¿Olvidaste tu contraseña?"** en la pantalla de login. Escribe tu usuario y un breve motivo. La solicitud se registra y el administrador te restablecerá la contraseña.

### 1.4 Bloqueos automáticos

- Tras **5 intentos fallidos** en 5 minutos, tu cuenta queda temporalmente bloqueada.
- Tras **6 meses sin iniciar sesión**, la cuenta se bloquea por inactividad. En ambos casos contacta con el administrador.

---

## 2. Rol empleado

### 2.1 Propietarios

- **Alta**: DNI/NIE, apellidos, nombre, teléfonos, direcciones.
- **Consulta**: el empleado debe introducir un criterio (DNI, chip o nombre). No se listan datos completos sin búsqueda previa.
- **Direcciones**: un propietario puede tener varias direcciones asociadas.

### 2.2 Animales

- **Alta**: chip, especie, raza, sexo, año de nacimiento, esterilizado, vacuna antirrábica, propietario (DNI existente), número de censo, póliza de seguro opcional.
- **Modificación**: propietario, fecha de última vacuna, esterilizado y póliza. Cada cambio queda registrado en auditoría con el valor anterior y el nuevo.
- **Consulta**: por chip o desde la ficha del propietario.

### 2.3 Seguros

Alta y consulta de pólizas (compañía, número de póliza, vigencia).

### 2.4 Baja de animal

- Motivos: fallecimiento, traslado, pérdida, etc.
- Se numera automáticamente (`BAJA-AAAA-####`) y queda en auditoría.
- Las bajas **por edad avanzada** se ejecutan automáticamente cada noche.

### 2.5 Consulta global

Buscador de la cabecera: escribe un chip, DNI o nombre y selecciona el resultado.

### 2.6 Estadísticas

Gráficos agregados con filtros opcionales.

---

## 3. Rol policía

### 3.1 Panel de policía

Al iniciar sesión se accede directamente al panel. Funciones disponibles:

- **Consulta rápida por chip**: introduce un chip y muestra propietario, vacunas y estado.
- **Registro de incidencias**: tipo, descripción, fecha, agente. Queda asociado al chip y al animal.

### 3.2 Uso en el móvil (PWA)

La aplicación es instalable como app nativa:

1. Abre la URL en Chrome/Edge (Android) o Safari (iOS).
2. Menú del navegador → **"Instalar aplicación"** o **"Añadir a pantalla de inicio"**.
3. Aparece un icono en el móvil con acceso directo al panel de policía.

Con la app instalada:

- Las **consultas** recientes (chips, propietarios, incidencias) funcionan **sin conexión**.
- El registro de incidencias **requiere conexión** al servidor.

---

## 4. Seguridad y buenas prácticas

- No compartas tu usuario ni tu contraseña. Todas las acciones quedan registradas a nombre del usuario que inicia la sesión.
- **Cierra sesión** (botón **"Salir"**) al terminar, especialmente en equipos compartidos.
- Si sospechas un acceso indebido, avisa al administrador para restablecer tu contraseña y revisar la auditoría.
- La aplicación muestra un aviso cuando no puede conectar con el servidor (**"API sin conexión"** en la cabecera).

---

## 5. Preguntas frecuentes

**¿Puedo cambiar mi contraseña cuando quiera?**
Sí, desde el menú desplegable de tu usuario (arriba a la derecha) → **"Cambiar contraseña"**.

**¿Por qué me pide cambiar la contraseña otra vez?**
Porque han pasado más de 365 días desde el último cambio, o el administrador la ha restablecido.

**¿Por qué no veo listados completos sin buscar?**
Los empleados y la policía solo pueden acceder a datos tras un criterio de búsqueda específico, por razones de protección de datos.

**¿Qué pasa si pierdo la conexión en el móvil?**
La PWA mantiene disponibles las consultas que hiciste recientemente. Las altas, bajas y modificaciones se tienen que hacer con conexión.
