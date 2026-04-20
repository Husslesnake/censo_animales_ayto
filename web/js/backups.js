// ── Backups admin ─────────────────────────────────────────────────────────

function _fmtTamano(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}

function _fmtFechaBackup(iso) {
  if (!iso) return "—";
  var d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString("es-ES");
}

async function cargarBackups() {
  var tbody = document.getElementById("tbody-backups");
  var info = document.getElementById("backups-info");
  if (!tbody) return;
  tbody.innerHTML = '<tr class="empty-row"><td colspan="4">Cargando…</td></tr>';
  try {
    var res = await apiFetch("/api/admin/backups");
    var data = await res.json();
    if (!data.ok) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="4">' + (data.error || "Error al cargar.") + '</td></tr>';
      return;
    }
    if (info) {
      info.textContent = "Retención: " + (data.retencion_dias || 30) + " días · "
        + (data.backups || []).length + " archivo(s) · copia automática diaria a las 04:00";
    }
    if (!data.backups || !data.backups.length) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="4">No hay copias disponibles todavía.</td></tr>';
      return;
    }
    tbody.innerHTML = data.backups.map(function (b) {
      return '<tr>'
        + '<td style="font-family:monospace;font-size:0.82rem;">' + b.nombre + '</td>'
        + '<td>' + _fmtFechaBackup(b.fecha) + '</td>'
        + '<td style="text-align:right;font-family:monospace;">' + _fmtTamano(b.tamano) + '</td>'
        + '<td style="text-align:right;">'
        + '<button class="btn btn-secondary" style="padding:0.2rem 0.55rem;font-size:0.75rem;" onclick="descargarBackup(\'' + b.nombre + '\')">Descargar</button> '
        + '<button class="btn btn-primary" style="padding:0.2rem 0.55rem;font-size:0.75rem;" onclick="restaurarBackup(\'' + b.nombre + '\')">Restaurar</button> '
        + '<button class="btn btn-danger" style="padding:0.2rem 0.55rem;font-size:0.75rem;" onclick="eliminarBackup(\'' + b.nombre + '\')">Eliminar</button>'
        + '</td>'
        + '</tr>';
    }).join("");
  } catch (e) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="4">Error de conexión.</td></tr>';
    if (typeof logError === "function") logError(e.message, "cargarBackups", e.stack);
  }
}

async function crearBackupManual() {
  var alertEl = document.getElementById("alert-backups");
  try {
    var res = await apiFetch("/api/admin/backups/crear", { method: "POST" });
    var data = await res.json();
    if (data.ok) {
      if (alertEl) {
        alertEl.className = "alert alert-ok show";
        alertEl.querySelector(".alert-msg").textContent =
          "Backup creado: " + data.archivo + " (" + _fmtTamano(data.tamano) + ")";
        setTimeout(function () { alertEl.classList.remove("show"); }, 4000);
      }
      cargarBackups();
    } else if (alertEl) {
      alertEl.className = "alert alert-err show";
      alertEl.querySelector(".alert-msg").textContent = data.error || "Error al crear backup.";
    }
  } catch (e) {
    if (alertEl) {
      alertEl.className = "alert alert-err show";
      alertEl.querySelector(".alert-msg").textContent = "Error de conexión.";
    }
    if (typeof logError === "function") logError(e.message, "crearBackupManual", e.stack);
  }
}

async function descargarBackup(nombre) {
  try {
    var t = _getToken();
    var res = await fetch("/api/admin/backups/" + encodeURIComponent(nombre), {
      headers: { "X-Token": (t && t.token) || "", "X-Device-Id": _getDeviceId() }
    });
    if (!res.ok) {
      var alertEl = document.getElementById("alert-backups");
      if (alertEl) {
        alertEl.className = "alert alert-err show";
        alertEl.querySelector(".alert-msg").textContent = "No se pudo descargar el backup.";
      }
      return;
    }
    var blob = await res.blob();
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1500);
  } catch (e) {
    if (typeof logError === "function") logError(e.message, "descargarBackup", e.stack);
  }
}

async function restaurarBackup(nombre) {
  var msg = "¿Restaurar el backup " + nombre + "?\n\n"
    + "Esta acción SOBRESCRIBE todos los datos actuales de la base de datos con los del backup.\n"
    + "Antes de restaurar se creará automáticamente un backup de seguridad.\n\n"
    + "Escribe RESTAURAR para confirmar:";
  var txt = prompt(msg, "");
  if (txt !== "RESTAURAR") return;
  var alertEl = document.getElementById("alert-backups");
  if (alertEl) {
    alertEl.className = "alert alert-ok show";
    alertEl.querySelector(".alert-msg").textContent = "Restaurando… puede tardar varios segundos.";
  }
  try {
    var res = await apiFetch("/api/admin/backups/" + encodeURIComponent(nombre) + "/restaurar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ confirmacion: "RESTAURAR" }),
    });
    var data = await res.json();
    if (alertEl) {
      if (data.ok) {
        alertEl.className = "alert alert-ok show";
        var extra = (data.errores && data.errores.length)
          ? " (" + data.errores.length + " sentencia(s) con aviso)"
          : "";
        alertEl.querySelector(".alert-msg").textContent =
          "Restauración completada: " + data.sentencias + " sentencias" + extra
          + ". Backup previo: " + (data.pre_restore || "—");
      } else {
        alertEl.className = "alert alert-err show";
        alertEl.querySelector(".alert-msg").textContent =
          "Error en la restauración: " + (data.error || "desconocido")
          + (data.pre_restore ? " · Backup previo seguro en: " + data.pre_restore : "");
      }
    }
    cargarBackups();
  } catch (e) {
    if (alertEl) {
      alertEl.className = "alert alert-err show";
      alertEl.querySelector(".alert-msg").textContent = "Error de conexión durante la restauración.";
    }
    if (typeof logError === "function") logError(e.message, "restaurarBackup", e.stack);
  }
}

async function eliminarBackup(nombre) {
  if (!confirm("¿Eliminar el backup " + nombre + "? Esta acción no se puede deshacer.")) return;
  try {
    var res = await apiFetch("/api/admin/backups/" + encodeURIComponent(nombre), { method: "DELETE" });
    var data = await res.json();
    var alertEl = document.getElementById("alert-backups");
    if (data.ok) {
      if (alertEl) {
        alertEl.className = "alert alert-ok show";
        alertEl.querySelector(".alert-msg").textContent = "Backup eliminado.";
        setTimeout(function () { alertEl.classList.remove("show"); }, 3000);
      }
      cargarBackups();
    } else if (alertEl) {
      alertEl.className = "alert alert-err show";
      alertEl.querySelector(".alert-msg").textContent = data.error || "Error al eliminar.";
    }
  } catch (e) {
    if (typeof logError === "function") logError(e.message, "eliminarBackup", e.stack);
  }
}
