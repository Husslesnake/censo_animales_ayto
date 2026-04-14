      // ── Panel de Policía ───────────────────────────────────────────────────────
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
        try {
          var res = await apiFetch("/api/incidencias", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chip: chip, tipo: tipo, descripcion: desc })
          });
          var data = await res.json();
          if (data.ok) {
            altEl.textContent = "Incidencia #" + data.id + " registrada correctamente.";
            altEl.style.background = "rgba(30,107,60,0.08)";
            altEl.style.color = "var(--verde)";
            altEl.style.display = "block";
            document.getElementById("inc-tipo").value = "";
            document.getElementById("inc-descripcion").value = "";
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
          var tbody = document.getElementById("tbody-incidencias");
          if (!data.ok || !data.datos || data.datos.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No hay incidencias registradas.</td></tr>';
            return;
          }
          tbody.innerHTML = data.datos.map(function(inc) {
            var fecha = inc.FECHA ? inc.FECHA.replace("T", " ").slice(0,16) : "—";
            return "<tr><td>" + (inc.ID||"") + "</td><td>" + (inc.N_CHIP||"") +
              "</td><td>" + (inc.TIPO||"") + "</td><td style='max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>" +
              (inc.DESCRIPCION||"—") + "</td><td>" + fecha + "</td></tr>";
          }).join("");
        } catch(e) { logError(e.message, "cargarIncidencias", e.stack); }
      }
      // ── Fin panel policía ──────────────────────────────────────────────────────
