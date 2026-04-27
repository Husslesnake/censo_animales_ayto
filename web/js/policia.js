      // ── Panel de Policía ───────────────────────────────────────────────────────
      var _incidencias = { datos: [], pagina: 1, porPagina: 2 };

      async function buscarChipPolicia() {
        var chip = document.getElementById("pol-chip-input").value.trim();
        var errEl = document.getElementById("pol-chip-error");
        var resEl = document.getElementById("pol-resultado");
        errEl.style.display = "none";
        resEl.style.display = "none";
        if (!chip) { errEl.textContent = "Introduzca un número de chip."; errEl.style.display = "block"; return; }
        try {
          var res = await apiFetch("/api/policia/chip/" + encodeURIComponent(chip));
          var data = await res.json();
          if (!data.ok) { errEl.textContent = data.error || "Animal no encontrado."; errEl.style.display = "block"; return; }
          // Rellenar animal
          var a = data.animal || {};
          var aDl = document.getElementById("pol-animal-dl");
          aDl.innerHTML = [
            ["Chip",    a["Nº_CHIP"] || a["N_CHIP"] || chip],
            ["Nombre",  a["NOMBRE"] || "—"],
            ["Especie", a["ESPECIE"] || "—"],
            ["Raza",    a["RAZA"] || "—"],
            ["Sexo",    a["SEXO"] || "—"],
            ["Color",   a["COLOR"] || "—"],
            ["Peligroso", a["PELIGROSO"] ? "Sí" : "No"],
          ].map(function(p){ return "<dt>"+p[0]+"</dt><dd>"+p[1]+"</dd>"; }).join("");
          // Rellenar propietario
          var p = data.propietario || {};
          var pDl = document.getElementById("pol-prop-dl");
          if (data.propietario) {
            pDl.innerHTML = [
              ["DNI",       p["DNI"] || "—"],
              ["Nombre",    (p["NOMBRE"]||"") + " " + (p["PRIMER_APELLIDO"]||"") + " " + (p["SEGUNDO_APELLIDO"]||"")],
              ["Teléfono",  p["TELEFONO1"] || "—"],
              ["Domicilio", p["DOMICILIO"] || "—"],
              ["Municipio", p["MINICIPIO"] || "—"],
            ].map(function(r){ return "<dt>"+r[0]+"</dt><dd>"+r[1].trim()+"</dd>"; }).join("");
          } else {
            pDl.innerHTML = "<dt style='grid-column:1/-1;color:var(--gris4);'>Sin propietario registrado</dt>";
          }
          resEl.style.display = "grid";
          // Pre-rellenar chip en el formulario
          document.getElementById("inc-chip").value = chip;
        } catch(e) {
          errEl.textContent = "Error de conexión."; errEl.style.display = "block";
          logError(e.message, "buscarChipPolicia", e.stack);
        }
      }

      async function registrarIncidencia() {
        var chip  = document.getElementById("inc-chip").value.trim();
        var tipo  = document.getElementById("inc-tipo").value;
        var desc  = document.getElementById("inc-descripcion").value.trim();
        var altEl = document.getElementById("inc-alert");
        altEl.style.display = "none";
        if (!chip || !tipo) {
          altEl.textContent = "Chip y tipo de incidencia son obligatorios.";
          altEl.style.background = "rgba(123,45,64,0.08)";
          altEl.style.color = "var(--rojo)";
          altEl.style.display = "block"; return;
        }
        var fotoInput = document.getElementById("inc-foto");
        var tieneFoto = fotoInput && fotoInput.files && fotoInput.files.length > 0;
        try {
          var opciones;
          if (tieneFoto) {
            var fd = new FormData();
            fd.append("chip", chip);
            fd.append("tipo", tipo);
            fd.append("descripcion", desc);
            fd.append("N_CHIP", chip);
            fd.append("TIPO", tipo);
            fd.append("DESCRIPCION", desc);
            fd.append("FECHA", new Date().toISOString());
            fd.append("FOTO", fotoInput.files[0]);
            opciones = { method: "POST", body: fd };
          } else {
            opciones = {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ chip: chip, tipo: tipo, descripcion: desc })
            };
          }
          var res = await apiFetch("/api/incidencias", opciones);
          var data = await res.json();
          if (data.ok) {
            altEl.textContent = "Incidencia #" + data.id + " registrada correctamente.";
            altEl.style.background = "rgba(30,107,60,0.08)";
            altEl.style.color = "var(--verde)";
            altEl.style.display = "block";
            document.getElementById("inc-tipo").value = "";
            document.getElementById("inc-descripcion").value = "";
            if (fotoInput) fotoInput.value = "";
            cargarIncidencias();
          } else {
            altEl.textContent = data.error || "Error al registrar.";
            altEl.style.background = "rgba(123,45,64,0.08)";
            altEl.style.color = "var(--rojo)";
            altEl.style.display = "block";
          }
        } catch(e) {
          altEl.textContent = "Error de conexión."; altEl.style.display = "block";
          logError(e.message, "registrarIncidencia", e.stack);
        }
      }

      async function cargarIncidencias() {
        try {
          var res = await apiFetch("/api/incidencias");
          var data = await res.json();
          if (!data.ok || !data.datos || data.datos.length === 0) {
            _incidencias.datos = [];
            _incidencias.pagina = 1;
            var tbody = document.getElementById("tbody-incidencias");
            tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No hay incidencias registradas.</td></tr>';
            var pagEl = document.getElementById("pag-incidencias");
            if (pagEl) pagEl.innerHTML = "";
            return;
          }
          _incidencias.datos = data.datos;
          _incidencias.pagina = 1;
          renderIncidenciasPagina(1);
        } catch(e) { logError(e.message, "cargarIncidencias", e.stack); }
      }

      function renderIncidenciasPagina(pagina) {
        var d = _incidencias;
        var total = d.datos.length;
        var npags = Math.ceil(total / d.porPagina);
        pagina = Math.max(1, Math.min(pagina, npags));
        d.pagina = pagina;

        var inicio = (pagina - 1) * d.porPagina;
        var trozo = d.datos.slice(inicio, inicio + d.porPagina);
        var tbody = document.getElementById("tbody-incidencias");

        tbody.innerHTML = trozo.map(function(inc) {
          var fecha = inc.FECHA ? inc.FECHA.replace("T", " ").slice(0,16) : "—";
          return '<tr>' +
            '<td data-label="ID">' + (inc.ID||"") + '</td>' +
            '<td data-label="Chip">' + (inc.N_CHIP||"") + '</td>' +
            '<td data-label="Tipo">' + (inc.TIPO||"") + '</td>' +
            '<td data-label="Descripción">' + (inc.DESCRIPCION||"—") + '</td>' +
            '<td data-label="Fecha">' + fecha + '</td>' +
            '<td data-label="Agente">' + (inc.AGENTE||"—") + '</td>' +
            '</tr>';
        }).join("");

        // Render pagination controls
        var pagEl = document.getElementById("pag-incidencias");
        if (!pagEl) return;
        if (npags <= 1) { pagEl.innerHTML = ""; return; }

        var html = '<button onclick="renderIncidenciasPagina(' + (pagina - 1) + ')" ' +
          (pagina === 1 ? 'disabled' : '') + '>‹</button>';
        // Windowed page buttons (max 5 visible)
        var ventana = [];
        if (npags <= 7) {
          for (var i = 1; i <= npags; i++) ventana.push(i);
        } else {
          ventana.push(1);
          if (pagina > 3) ventana.push("…");
          for (var i = Math.max(2, pagina - 1); i <= Math.min(npags - 1, pagina + 1); i++) ventana.push(i);
          if (pagina < npags - 2) ventana.push("…");
          ventana.push(npags);
        }
        ventana.forEach(function(p) {
          if (p === "…") {
            html += '<button disabled>…</button>';
          } else {
            html += '<button class="' + (p === pagina ? 'activa' : '') +
              '" onclick="renderIncidenciasPagina(' + p + ')">' + p + '</button>';
          }
        });
        html += '<button onclick="renderIncidenciasPagina(' + (pagina + 1) + ')" ' +
          (pagina === npags ? 'disabled' : '') + '>›</button>';
        html += '<span class="pag-info">pág. ' + pagina + ' / ' + npags + ' · ' + total + ' incidencias</span>';
        pagEl.innerHTML = html;
      }
      // ── Fin panel policía ──────────────────────────────────────────────────────
