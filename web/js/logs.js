      let _logFicheroActivo = null;

      async function cargarListaLogs() {
        const lista = document.getElementById("logs-lista");
        if (lista) lista.innerHTML = "Cargando…";
        try {
          const json = await (await fetch(API + "/logs")).json();
          if (!json.ok) {
            if (lista) lista.innerHTML = "Error al cargar logs.";
            return;
          }
          if (!json.ficheros.length) {
            if (lista)
              lista.innerHTML =
                '<span style="color:var(--gris3);font-size:.82rem;">Sin ficheros de log.</span>';
            return;
          }
          lista.innerHTML = json.ficheros
            .map(
              (f) =>
                `<div onclick="verLog('${f}')" style="padding:.45rem 1rem;cursor:pointer;font-family:'IBM Plex Mono',monospace;` +
                `font-size:.75rem;border-bottom:1px solid var(--borde2);transition:background .1s;"
       onmouseover="this.style.background='var(--gris0)'" onmouseout="this.style.background=''"
       id="log-item-${f.replace(".", "_")}">${f}</div>`,
            )
            .join("");
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          if (lista)
            lista.innerHTML = `<span style="color:var(--rojo);font-size:.82rem;">Error: ${err.message}</span>`;
        }
      }

      async function verLog(nombre) {
        _logFicheroActivo = nombre;
        const viewer = document.getElementById("logs-viewer");
        const titulo = document.getElementById("logs-fichero-titulo");
        const totalEl = document.getElementById("logs-total-lineas");
        const btnDesc = document.getElementById("btn-descargar-log");

        if (titulo) titulo.textContent = nombre;
        if (viewer) viewer.textContent = "Cargando…";
        if (btnDesc) btnDesc.style.display = "";

        document.querySelectorAll('[id^="log-item-"]').forEach((el) => {
          el.style.fontWeight =
            el.id === "log-item-" + nombre.replace(".", "_") ? "700" : "";
          el.style.color =
            el.id === "log-item-" + nombre.replace(".", "_")
              ? "var(--rojo)"
              : "";
        });

        try {
          const json = await (
            await fetch(
              API + "/logs/" + encodeURIComponent(nombre) + "?modo=ver",
            )
          ).json();
          if (!json.ok) {
            if (viewer) viewer.textContent = "Error: " + json.error;
            return;
          }
          if (totalEl)
            totalEl.textContent = `${json.total} líneas · mostrando últimas ${json.lineas.length}`;

          if (viewer) {
            viewer.innerHTML = json.lineas
              .map((l) => {
                const escaped = l
                  .replace(/&/g, "&amp;")
                  .replace(/</g, "&lt;")
                  .replace(/>/g, "&gt;");
                if (l.includes(" ERROR   "))
                  return `<span style="color:var(--rojo);">${escaped}</span>`;
                if (l.includes(" WARNING "))
                  return `<span style="color:var(--dorado2);">${escaped}</span>`;
                if (l.includes(" INFO    "))
                  return `<span style="color:var(--gris3);">${escaped}</span>`;
                return escaped;
              })
              .join("");

            viewer.scrollTop = viewer.scrollHeight;
          }
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          if (viewer) viewer.textContent = `Error: ${err.message}`;
        }
      }

      function descargarLog() {
        if (!_logFicheroActivo) return;
        window.location.href =
          API + "/logs/" + encodeURIComponent(_logFicheroActivo);
      }

      // ── Gestión de agentes de policía (admin) ─────────────────────────────

      var _polResetUsername = null;

      async function cargarAgentesPolicia() {
        var tbody = document.getElementById("tbody-agentes");
        if (!tbody) return;
        tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Cargando…</td></tr>';
        try {
          var res  = await apiFetch(API + "/auth/policia_usuarios");
          var data = await res.json();
          if (!data.ok) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Error al cargar agentes.</td></tr>';
            return;
          }
          if (!data.datos.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No hay agentes registrados.</td></tr>';
            return;
          }
          tbody.innerHTML = data.datos.map(function(a) {
            var estadoTag = a.activo
              ? '<span class="tag" style="background:rgba(30,107,60,0.1);color:var(--verde);border:1px solid rgba(30,107,60,0.3);">Activo</span>'
              : '<span class="tag" style="background:rgba(123,45,64,0.1);color:var(--rojo);border:1px solid rgba(123,45,64,0.3);">Desactivado</span>';
            // Último acceso + aviso de inactividad próxima (>150 días = 5 meses)
            var ultimoAccesoStr = "—";
            var ultimoAccesoStyle = "";
            if (a.ultimo_acceso) {
              var diasInactivo = Math.floor((Date.now() - new Date(a.ultimo_acceso)) / 86400000);
              ultimoAccesoStr = a.ultimo_acceso.replace("T", " ").slice(0, 16);
              if (diasInactivo > 150) {
                ultimoAccesoStyle = "color:var(--rojo);font-weight:600;";
                ultimoAccesoStr += ' <span title="Próximo a bloqueo por inactividad">⚠</span>';
              }
            } else if (a.activo) {
              ultimoAccesoStr = '<span style="color:var(--gris3);font-size:0.76rem;">Sin accesos aún</span>';
            }
            var toggleLabel = a.activo ? "Desactivar" : "Activar";
            var toggleColor = a.activo ? "color:var(--rojo);" : "color:var(--verde);";
            return '<tr>' +
              '<td><span class="tag tag-id">' + a.username + '</span></td>' +
              '<td>' + a.nombre + '</td>' +
              '<td>' + estadoTag + '</td>' +
              '<td style="font-size:0.78rem;' + ultimoAccesoStyle + '">' + ultimoAccesoStr + '</td>' +
              '<td style="white-space:nowrap;display:flex;gap:0.4rem;flex-wrap:wrap;">' +
                '<button class="btn btn-secondary" style="font-size:0.75rem;padding:0.15rem 0.5rem;" ' +
                  'onclick="abrirModalResetPolicia(\'' + a.username + '\',\'' + a.nombre.replace(/'/g,"\\'" ) + '\')">' +
                  'Contraseña</button>' +
                '<button class="btn btn-secondary" style="font-size:0.75rem;padding:0.15rem 0.5rem;' + toggleColor + '" ' +
                  'onclick="toggleActivoPolicia(\'' + a.username + '\',' + !a.activo + ')">' +
                  toggleLabel + '</button>' +
                '<button class="btn btn-secondary" style="font-size:0.75rem;padding:0.15rem 0.5rem;color:var(--rojo);" ' +
                  'onclick="eliminarCuentaPolicia(\'' + a.username + '\',\'' + a.nombre.replace(/'/g,"\\'") + '\')">' +
                  'Eliminar</button>' +
              '</td></tr>';
          }).join("");
        } catch(e) {
          tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Error de conexión.</td></tr>';
          logError(e.message, "cargarAgentesPolicia", e.stack);
        }
      }

      async function crearCuentaPolicia() {
        var username = document.getElementById("pol-admin-username").value.trim().toLowerCase();
        var nombre   = document.getElementById("pol-admin-nombre").value.trim();
        var password = document.getElementById("pol-admin-pass").value;
        var alertEl  = document.getElementById("pol-admin-alert");
        alertEl.classList.remove("show");
        if (!username || !nombre || !password) {
          alertEl.querySelector(".alert-msg").textContent = "Todos los campos son obligatorios.";
          alertEl.classList.add("show", "error");
          return;
        }
        try {
          var res  = await apiFetch(API + "/auth/policia_usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, nombre: nombre, password: password })
          });
          var data = await res.json();
          if (data.ok) {
            alertEl.querySelector(".alert-msg").textContent = "Cuenta creada correctamente.";
            alertEl.classList.add("show", "ok");
            document.getElementById("pol-admin-username").value = "";
            document.getElementById("pol-admin-nombre").value   = "";
            document.getElementById("pol-admin-pass").value     = "";
            cargarAgentesPolicia();
          } else {
            alertEl.querySelector(".alert-msg").textContent = data.error || "Error al crear la cuenta.";
            alertEl.classList.add("show", "error");
          }
        } catch(e) {
          alertEl.querySelector(".alert-msg").textContent = "Error de conexión.";
          alertEl.classList.add("show", "error");
          logError(e.message, "crearCuentaPolicia", e.stack);
        }
      }

      async function toggleActivoPolicia(username, nuevoEstado) {
        try {
          var res  = await apiFetch(API + "/auth/policia_usuarios/" + encodeURIComponent(username), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ activo: nuevoEstado })
          });
          var data = await res.json();
          if (data.ok) cargarAgentesPolicia();
          else alert(data.error || "Error al actualizar.");
        } catch(e) { logError(e.message, "toggleActivoPolicia", e.stack); }
      }

      async function eliminarCuentaPolicia(username, nombre) {
        if (!confirm('¿Eliminar la cuenta de "' + nombre + '" (' + username + ')?\nEsta acción no se puede deshacer.')) return;
        try {
          var res  = await apiFetch(API + "/auth/policia_usuarios/" + encodeURIComponent(username), {
            method: "DELETE"
          });
          var data = await res.json();
          if (data.ok) cargarAgentesPolicia();
          else alert(data.error || "Error al eliminar.");
        } catch(e) { logError(e.message, "eliminarCuentaPolicia", e.stack); }
      }

      function abrirModalResetPolicia(username, nombre) {
        _polResetUsername = username;
        document.getElementById("modal-reset-pol-desc").textContent = "Agente: " + nombre + " (" + username + ")";
        document.getElementById("modal-reset-pol-pass").value = "";
        document.getElementById("modal-reset-pol-error").style.display = "none";
        document.getElementById("modal-reset-pol").style.display = "flex";
        setTimeout(function(){ document.getElementById("modal-reset-pol-pass").focus(); }, 50);
      }

      function cerrarModalResetPolicia() {
        document.getElementById("modal-reset-pol").style.display = "none";
        _polResetUsername = null;
      }

      async function confirmarResetPolicia() {
        var pass  = document.getElementById("modal-reset-pol-pass").value;
        var errEl = document.getElementById("modal-reset-pol-error");
        errEl.style.display = "none";
        if (pass.length < 6) {
          errEl.textContent = "La contraseña debe tener al menos 6 caracteres.";
          errEl.style.display = "block"; return;
        }
        try {
          var res  = await apiFetch(API + "/auth/policia_usuarios/" + encodeURIComponent(_polResetUsername), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: pass })
          });
          var data = await res.json();
          if (data.ok) {
            cerrarModalResetPolicia();
          } else {
            errEl.textContent = data.error || "Error al cambiar contraseña.";
            errEl.style.display = "block";
          }
        } catch(e) {
          errEl.textContent = "Error de conexión.";
          errEl.style.display = "block";
          logError(e.message, "confirmarResetPolicia", e.stack);
        }
      }

      // ── Gestión de empleados (admin) ──────────────────────────────────────

      var _empResetUsername = null;

      async function cargarEmpleados() {
        var tbody = document.getElementById("tbody-empleados");
        if (!tbody) return;
        tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Cargando…</td></tr>';
        try {
          var res  = await apiFetch(API + "/auth/empleado_usuarios");
          var data = await res.json();
          if (!data.ok) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Error al cargar empleados.</td></tr>';
            return;
          }
          if (!data.datos.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No hay empleados registrados.</td></tr>';
            return;
          }
          tbody.innerHTML = data.datos.map(function(a) {
            var estadoTag = a.activo
              ? '<span class="tag" style="background:rgba(30,107,60,0.1);color:var(--verde);border:1px solid rgba(30,107,60,0.3);">Activo</span>'
              : '<span class="tag" style="background:rgba(123,45,64,0.1);color:var(--rojo);border:1px solid rgba(123,45,64,0.3);">Desactivado</span>';
            var ultimoAccesoStr = "—";
            var ultimoAccesoStyle = "";
            if (a.ultimo_acceso) {
              var diasInactivo = Math.floor((Date.now() - new Date(a.ultimo_acceso)) / 86400000);
              ultimoAccesoStr = a.ultimo_acceso.replace("T", " ").slice(0, 16);
              if (diasInactivo > 150) {
                ultimoAccesoStyle = "color:var(--rojo);font-weight:600;";
                ultimoAccesoStr += ' <span title="Próximo a bloqueo por inactividad">⚠</span>';
              }
            } else if (a.activo) {
              ultimoAccesoStr = '<span style="color:var(--gris3);font-size:0.76rem;">Sin accesos aún</span>';
            }
            var toggleLabel = a.activo ? "Desactivar" : "Activar";
            var toggleColor = a.activo ? "color:var(--rojo);" : "color:var(--verde);";
            return '<tr>' +
              '<td><span class="tag tag-id">' + a.username + '</span></td>' +
              '<td>' + a.nombre + '</td>' +
              '<td>' + estadoTag + '</td>' +
              '<td style="font-size:0.78rem;' + ultimoAccesoStyle + '">' + ultimoAccesoStr + '</td>' +
              '<td style="white-space:nowrap;display:flex;gap:0.4rem;flex-wrap:wrap;">' +
                '<button class="btn btn-secondary" style="font-size:0.75rem;padding:0.15rem 0.5rem;" ' +
                  'onclick="abrirModalResetEmpleado(\'' + a.username + '\',\'' + a.nombre.replace(/'/g,"\\'" ) + '\')">' +
                  'Contraseña</button>' +
                '<button class="btn btn-secondary" style="font-size:0.75rem;padding:0.15rem 0.5rem;' + toggleColor + '" ' +
                  'onclick="toggleActivoEmpleado(\'' + a.username + '\',' + !a.activo + ')">' +
                  toggleLabel + '</button>' +
                '<button class="btn btn-secondary" style="font-size:0.75rem;padding:0.15rem 0.5rem;color:var(--rojo);" ' +
                  'onclick="eliminarCuentaEmpleado(\'' + a.username + '\',\'' + a.nombre.replace(/'/g,"\\'") + '\')">' +
                  'Eliminar</button>' +
              '</td></tr>';
          }).join("");
        } catch(e) {
          tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Error de conexión.</td></tr>';
          logError(e.message, "cargarEmpleados", e.stack);
        }
      }

      async function crearCuentaEmpleado() {
        var username = document.getElementById("emp-admin-username").value.trim().toLowerCase();
        var nombre   = document.getElementById("emp-admin-nombre").value.trim();
        var password = document.getElementById("emp-admin-pass").value;
        var alertEl  = document.getElementById("emp-admin-alert");
        alertEl.classList.remove("show");
        if (!username || !nombre || !password) {
          alertEl.querySelector(".alert-msg").textContent = "Todos los campos son obligatorios.";
          alertEl.classList.add("show", "error");
          return;
        }
        try {
          var res  = await apiFetch(API + "/auth/empleado_usuarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, nombre: nombre, password: password })
          });
          var data = await res.json();
          if (data.ok) {
            alertEl.querySelector(".alert-msg").textContent = "Cuenta creada correctamente.";
            alertEl.classList.add("show", "ok");
            document.getElementById("emp-admin-username").value = "";
            document.getElementById("emp-admin-nombre").value   = "";
            document.getElementById("emp-admin-pass").value     = "";
            cargarEmpleados();
          } else {
            alertEl.querySelector(".alert-msg").textContent = data.error || "Error al crear la cuenta.";
            alertEl.classList.add("show", "error");
          }
        } catch(e) {
          alertEl.querySelector(".alert-msg").textContent = "Error de conexión.";
          alertEl.classList.add("show", "error");
          logError(e.message, "crearCuentaEmpleado", e.stack);
        }
      }

      async function toggleActivoEmpleado(username, nuevoEstado) {
        try {
          var res  = await apiFetch(API + "/auth/empleado_usuarios/" + encodeURIComponent(username), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ activo: nuevoEstado })
          });
          var data = await res.json();
          if (data.ok) cargarEmpleados();
          else alert(data.error || "Error al actualizar.");
        } catch(e) { logError(e.message, "toggleActivoEmpleado", e.stack); }
      }

      async function eliminarCuentaEmpleado(username, nombre) {
        if (!confirm('¿Eliminar la cuenta de "' + nombre + '" (' + username + ')?\nEsta acción no se puede deshacer.')) return;
        try {
          var res  = await apiFetch(API + "/auth/empleado_usuarios/" + encodeURIComponent(username), {
            method: "DELETE"
          });
          var data = await res.json();
          if (data.ok) cargarEmpleados();
          else alert(data.error || "Error al eliminar.");
        } catch(e) { logError(e.message, "eliminarCuentaEmpleado", e.stack); }
      }

      function abrirModalResetEmpleado(username, nombre) {
        _empResetUsername = username;
        document.getElementById("modal-reset-emp-desc").textContent = "Empleado: " + nombre + " (" + username + ")";
        document.getElementById("modal-reset-emp-pass").value = "";
        document.getElementById("modal-reset-emp-error").style.display = "none";
        document.getElementById("modal-reset-emp").style.display = "flex";
        setTimeout(function(){ document.getElementById("modal-reset-emp-pass").focus(); }, 50);
      }

      function cerrarModalResetEmpleado() {
        document.getElementById("modal-reset-emp").style.display = "none";
        _empResetUsername = null;
      }

      async function confirmarResetEmpleado() {
        var pass  = document.getElementById("modal-reset-emp-pass").value;
        var errEl = document.getElementById("modal-reset-emp-error");
        errEl.style.display = "none";
        if (pass.length < 4) {
          errEl.textContent = "La contraseña debe tener al menos 4 caracteres.";
          errEl.style.display = "block"; return;
        }
        try {
          var res  = await apiFetch(API + "/auth/empleado_usuarios/" + encodeURIComponent(_empResetUsername), {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password: pass })
          });
          var data = await res.json();
          if (data.ok) {
            cerrarModalResetEmpleado();
          } else {
            errEl.textContent = data.error || "Error al cambiar contraseña.";
            errEl.style.display = "block";
          }
        } catch(e) {
          errEl.textContent = "Error de conexión.";
          errEl.style.display = "block";
          logError(e.message, "confirmarResetEmpleado", e.stack);
        }
      }
