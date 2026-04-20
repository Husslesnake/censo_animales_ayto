      // ── Auditoría del censo (solo administrador) ───────────────────────────
      // Carga las entradas del fichero logs/auditoria.jsonl desde el backend,
      // permite filtrarlas y mostrar el detalle completo de cada evento.

      var _auditoriaDatos = [];
      var _auditoriaPagina = 1;
      var _AUDITORIA_POR_PAG = 20;

      var ACCION_LABELS = {
        crear_propietario:         "Crear propietario",
        crear_animal:              "Alta de animal",
        actualizar_animal:         "Modificar animal",
        baja_animal:               "Dar de baja",
        baja_animal_automatica:    "Baja automática (edad)",
        crear_seguro:              "Crear seguro",
        eliminar_seguro:           "Eliminar seguro",
        crear_incidencia:          "Crear incidencia",
        crear_cuenta_policia:      "Crear agente",
        actualizar_cuenta_policia: "Modificar agente",
        eliminar_cuenta_policia:   "Eliminar agente",
        backup_automatico:         "Backup automático",
        backup_manual:             "Backup manual",
        backup_eliminar:           "Eliminar backup",
        solicitud_recuperacion:    "Solicitud de recuperación",
        bloqueo_inactividad:       "Bloqueo por inactividad",
        bloqueo_intentos:          "Bloqueo por intentos",
      };

      var ROL_LABELS = {
        admin:    "Administrador",
        empleado: "Empleado",
        policia:  "Policía",
        sistema:  "Sistema",
      };

      function _escapeHTML(s) {
        if (s === null || s === undefined) return "";
        return String(s)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }

      function _etiquetaAccion(accion) {
        return ACCION_LABELS[accion] || accion || "—";
      }

      function _etiquetaRol(rol) {
        return ROL_LABELS[rol] || rol || "—";
      }

      function _resumenDetalle(detalle) {
        if (!detalle || typeof detalle !== "object") return "—";
        var campos = [];
        // Si hay diff, resumirlo de forma legible
        if (detalle.diff && typeof detalle.diff === "object") {
          var keys = Object.keys(detalle.diff);
          if (keys.length) {
            var resumen = keys.slice(0, 2).map(function (k) {
              var v = detalle.diff[k] || {};
              var a = v.antes == null ? "∅" : String(v.antes);
              var d = v.despues == null ? "∅" : String(v.despues);
              return _escapeHTML(k) + ": " + _escapeHTML(a.slice(0, 20)) + " → " + _escapeHTML(d.slice(0, 20));
            }).join(" · ");
            if (keys.length > 2) resumen += " · +" + (keys.length - 2) + " más";
            campos.push(resumen);
          }
        }
        var prioridad = ["DNI", "N_CHIP", "nombre", "DNI_propietario",
                         "motivo", "n_baja", "N_CENSO", "id", "username",
                         "compania", "poliza", "tipo", "archivo", "error"];
        for (var i = 0; i < prioridad.length && campos.length < 3; i++) {
          var k = prioridad[i];
          if (detalle[k] !== undefined && detalle[k] !== null && detalle[k] !== "") {
            var v = detalle[k];
            if (Array.isArray(v)) v = v.join(", ");
            else if (typeof v === "object") v = JSON.stringify(v);
            campos.push(k + "=" + _escapeHTML(String(v).slice(0, 60)));
          }
        }
        return campos.length ? campos.join(" · ") : "—";
      }

      async function cargarAuditoria() {
        var tbody = document.getElementById("tbody-auditoria");
        if (tbody) tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Cargando…</td></tr>';

        var params = new URLSearchParams();
        var d  = document.getElementById("aud-desde").value;
        var h  = document.getElementById("aud-hasta").value;
        var r  = document.getElementById("aud-rol").value;
        var a  = document.getElementById("aud-accion").value;
        var u  = document.getElementById("aud-usuario").value.trim();
        var ip = document.getElementById("aud-ip").value.trim();
        if (d)  params.set("desde",   d);
        if (h)  params.set("hasta",   h);
        if (r)  params.set("rol",     r);
        if (a)  params.set("accion",  a);
        if (u)  params.set("usuario", u);
        if (ip) params.set("ip",      ip);
        params.set("limit", "2000");

        try {
          var res = await apiFetch(API + "/auditoria?" + params.toString());
          var data = await res.json();
          if (!data.ok) {
            if (tbody) tbody.innerHTML =
              '<tr class="empty-row"><td colspan="7">' +
              _escapeHTML(data.error || "Error al cargar la auditoría.") + '</td></tr>';
            return;
          }
          _auditoriaDatos = data.datos || [];
          _auditoriaPagina = 1;
          renderAuditoria();
        } catch (e) {
          if (tbody) tbody.innerHTML =
            '<tr class="empty-row"><td colspan="7">Error de conexión.</td></tr>';
          logError(e.message || "Error cargarAuditoria", "cargarAuditoria", e.stack);
        }
      }

      function renderAuditoria() {
        var tbody  = document.getElementById("tbody-auditoria");
        var cont   = document.getElementById("aud-contador");
        var pagWrap = document.getElementById("pag-auditoria");
        if (!tbody) return;

        var total = _auditoriaDatos.length;
        if (cont) cont.textContent = total
          ? total + " registro" + (total !== 1 ? "s" : "")
          : "";

        if (!total) {
          tbody.innerHTML =
            '<tr class="empty-row"><td colspan="7">Sin registros que coincidan con los filtros.</td></tr>';
          if (pagWrap) pagWrap.innerHTML = "";
          return;
        }

        var npags = Math.ceil(total / _AUDITORIA_POR_PAG);
        _auditoriaPagina = Math.max(1, Math.min(_auditoriaPagina, npags));
        var inicio = (_auditoriaPagina - 1) * _AUDITORIA_POR_PAG;
        var trozo  = _auditoriaDatos.slice(inicio, inicio + _AUDITORIA_POR_PAG);

        tbody.innerHTML = trozo.map(function (e, idx) {
          var rol   = _escapeHTML(_etiquetaRol(e.rol));
          var acc   = _escapeHTML(_etiquetaAccion(e.accion));
          var exito = e.exito
            ? '<span class="tag" style="background:rgba(30,107,60,0.1);color:var(--verde);border:1px solid rgba(30,107,60,0.3);">OK</span>'
            : '<span class="tag" style="background:rgba(123,45,64,0.1);color:var(--rojo);border:1px solid rgba(123,45,64,0.3);">Error</span>';
          var resumen = _resumenDetalle(e.detalle);
          var indiceReal = inicio + idx;
          return '<tr>' +
            '<td data-label="Fecha" style="white-space:nowrap;font-family:\'IBM Plex Mono\',monospace;font-size:0.78rem;">' + _escapeHTML(e.fecha || "—") + '</td>' +
            '<td data-label="Rol">' + rol + '</td>' +
            '<td data-label="Usuario" style="font-family:\'IBM Plex Mono\',monospace;font-size:0.78rem;">' + _escapeHTML(e.usuario || "—") + '</td>' +
            '<td data-label="IP" style="font-family:\'IBM Plex Mono\',monospace;font-size:0.78rem;">' + _escapeHTML(e.ip || "—") + '</td>' +
            '<td data-label="Acción">' + acc + '</td>' +
            '<td data-label="Estado">' + exito + '</td>' +
            '<td data-label="Detalle" style="font-size:0.78rem;">' +
              '<span style="color:var(--gris3);">' + resumen + '</span> ' +
              '<button class="btn btn-secondary" style="padding:0.1rem 0.45rem;font-size:0.72rem;margin-left:0.4rem;" ' +
                'onclick="verDetalleAuditoria(' + indiceReal + ')">Ver</button>' +
            '</td>' +
          '</tr>';
        }).join("");

        if (!pagWrap) return;
        if (npags <= 1) { pagWrap.innerHTML = ""; return; }

        var html = '<button onclick="irPaginaAuditoria(' + (_auditoriaPagina - 1) + ')"' +
                   (_auditoriaPagina === 1 ? ' disabled' : '') + '>‹</button>';
        var ventana = [];
        if (npags <= 7) {
          for (var i = 1; i <= npags; i++) ventana.push(i);
        } else {
          ventana.push(1);
          if (_auditoriaPagina > 3) ventana.push("…");
          for (var j = Math.max(2, _auditoriaPagina - 1);
               j <= Math.min(npags - 1, _auditoriaPagina + 1); j++) ventana.push(j);
          if (_auditoriaPagina < npags - 2) ventana.push("…");
          ventana.push(npags);
        }
        ventana.forEach(function (p) {
          if (p === "…") html += '<button disabled>…</button>';
          else html += '<button class="' + (p === _auditoriaPagina ? "activa" : "") +
                       '" onclick="irPaginaAuditoria(' + p + ')">' + p + '</button>';
        });
        html += '<button onclick="irPaginaAuditoria(' + (_auditoriaPagina + 1) + ')"' +
                (_auditoriaPagina === npags ? ' disabled' : '') + '>›</button>';
        html += '<span class="pag-info">pág. ' + _auditoriaPagina + ' / ' + npags +
                ' · ' + total + ' registros</span>';
        pagWrap.innerHTML = html;
      }

      function irPaginaAuditoria(p) {
        _auditoriaPagina = p;
        renderAuditoria();
      }

      function aplicarFiltrosAuditoria() {
        // Debounce para que no bombardee al servidor mientras se escribe
        if (aplicarFiltrosAuditoria._t) clearTimeout(aplicarFiltrosAuditoria._t);
        aplicarFiltrosAuditoria._t = setTimeout(cargarAuditoria, 300);
      }

      function resetFiltrosAuditoria() {
        ["aud-desde","aud-hasta","aud-rol","aud-accion","aud-usuario","aud-ip"]
          .forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.value = "";
          });
        cargarAuditoria();
      }

      function verDetalleAuditoria(indice) {
        var e = _auditoriaDatos[indice];
        if (!e) return;
        var pre = document.getElementById("aud-detalle-json");
        if (pre) pre.textContent = JSON.stringify(e, null, 2);
        document.getElementById("modal-aud-detalle").style.display = "flex";
      }

      function cerrarDetalleAuditoria() {
        document.getElementById("modal-aud-detalle").style.display = "none";
      }

      function descargarAuditoria() {
        var t = _getToken();
        // send_file no respeta cabeceras en descarga directa → usamos fetch + blob
        apiFetch(API + "/auditoria/descargar")
          .then(function (res) {
            if (!res.ok) throw new Error("No se pudo descargar (" + res.status + ").");
            return res.blob();
          })
          .then(function (blob) {
            var url = URL.createObjectURL(blob);
            var a = document.createElement("a");
            a.href = url;
            a.download = "auditoria.jsonl";
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
          })
          .catch(function (e) {
            alert("Error al descargar la auditoría: " + (e.message || ""));
            logError(e.message, "descargarAuditoria", e.stack);
          });
      }
