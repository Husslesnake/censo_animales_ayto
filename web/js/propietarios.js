      // ── Gestión dinámica de domicilios ──────────────────────
      let _domIdx = 1;
      function addDomicilioRow() {
        const container = document.getElementById("domicilios-container");
        const idx = _domIdx++;
        const row = document.createElement("div");
        row.className = "domicilio-row";
        row.dataset.idx = idx;
        row.innerHTML =
          `<div class="form-grid" style="align-items:end;">` +
          `<div class="form-group span2"><label>Domicilio</label>` +
          `<input type="text" class="dom-domicilio" placeholder="Calle Mayor, 1" /></div>` +
          `<div class="form-group"><label>C.P.</label>` +
          `<input type="text" class="dom-cp" placeholder="28001" maxlength="10" inputmode="numeric" /></div>` +
          `<div class="form-group" style="display:flex;gap:.4rem;align-items:end;">` +
          `<div style="flex:1"><label>Municipio</label>` +
          `<input type="text" class="dom-municipio" placeholder="Madrid" /></div>` +
          `<button type="button" class="btn btn-secondary" ` +
          `style="padding:.35rem .6rem;font-size:.75rem;color:var(--rojo);border-color:var(--rojo);margin-bottom:0;" ` +
          `onclick="removeDomicilioRow(${idx})" title="Quitar domicilio">✕</button>` +
          `</div></div>`;
        container.appendChild(row);
      }
      function removeDomicilioRow(idx) {
        const row = document.querySelector(`.domicilio-row[data-idx='${idx}']`);
        if (row) row.remove();
      }
      function recogerDomicilios() {
        const rows = document.querySelectorAll("#domicilios-container .domicilio-row");
        const dirs = [];
        rows.forEach((r) => {
          const dom = (r.querySelector(".dom-domicilio")?.value || "").trim();
          const cp = (r.querySelector(".dom-cp")?.value || "").trim();
          const mun = (r.querySelector(".dom-municipio")?.value || "").trim();
          if (dom) dirs.push({ DOMICILIO: dom, CP: cp, MINICIPIO: mun });
        });
        return dirs;
      }

      async function submitPropietario(e) {
        e.preventDefault();
        const dniInput = document.getElementById("input-prop-dni");
        const resultado = validarFormatoDNI(dniInput.value);
        if (resultado.ok !== true) {
          validarDNI(dniInput, true);
          dniInput.focus();
          mostrarAlerta(
            "alert-prop",
            "error",
            "El DNI o NIE introducido no es válido. Corrígalo antes de continuar.",
          );
          return;
        }
        const btn = document.getElementById("btn-prop");
        const sp = document.getElementById("sp-prop");
        btn.disabled = true;
        sp.style.display = "block";
        const data = Object.fromEntries(new FormData(e.target).entries());
        Object.keys(data).forEach((k) => {
          if (!data[k]) delete data[k];
        });
        // Recoger domicilios dinámicos
        const direcciones = recogerDomicilios();
        if (direcciones.length) {
          data.DIRECCIONES = direcciones;
          // Guardar primer domicilio también en campos legacy
          if (!data.DOMICILIO) data.DOMICILIO = direcciones[0].DOMICILIO;
          if (!data.CP) data.CP = direcciones[0].CP;
          if (!data.MINICIPIO) data.MINICIPIO = direcciones[0].MINICIPIO;
        }
        try {
          const res = await fetch(API + "/propietarios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          });
          const json = await res.json();
          if (json.ok) {
            mostrarAlerta("alert-prop", "ok", json.mensaje);
            e.target.reset();
            // Limpiar domicilios extra
            const cont = document.getElementById("domicilios-container");
            if (cont) {
              const rows = cont.querySelectorAll(".domicilio-row");
              rows.forEach((r, i) => { if (i > 0) r.remove(); });
            }
          } else if (json.error && json.error.includes("ya existe")) {
            try {
              const dni2 = data.DNI || "";
              const j2 = await (
                await fetch(API + "/propietarios/" + encodeURIComponent(dni2))
              ).json();
              if (j2.ok && j2.datos) {
                const p = j2.datos;
                const nombre = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO]
                  .filter(Boolean)
                  .join(" ");
                mostrarAlerta(
                  "alert-prop",
                  "error",
                  "Ya está registrad@: " + nombre,
                );
              } else {
                mostrarAlerta("alert-prop", "error", json.error);
              }
            } catch (e) {
              logError(
                e?.message || "Error al procesar respuesta de propietario",
                "submitPropietario",
                e?.stack,
              );
              mostrarAlerta("alert-prop", "error", json.error);
            }
          } else {
            mostrarAlerta("alert-prop", "error", json.error);
          }
        } catch (e) {
          logError(
            e?.message || "No se pudo conectar con el servidor",
            "submitPropietario",
            e?.stack,
          );
          mostrarAlerta(
            "alert-prop",
            "error",
            "No se pudo conectar con el servidor.",
          );
        }
        btn.disabled = false;
        sp.style.display = "none";
      }
      async function cargarPropietarios() {
        const tbody = document.getElementById("tbody-prop");
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="6">Cargando…</td></tr>';
        setContador("prop-contador", null);
        document.getElementById("alert-busq-prop").classList.remove("show");
        try {
          const json = await (await fetch(API + "/propietarios")).json();
          if (!json.ok) throw new Error(json.error);
          if (!json.datos.length) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="6">Sin registros.</td></tr>';
            return;
          }
          setDatos("prop", json.datos, "encontrados");
        } catch (err) {
          logError(
            err?.message || "Error al cargar propietarios",
            "cargarPropietarios",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="6">Error: ${err.message}</td></tr>`;
        }
      }
      async function buscarPropietario() {
        const dni = document
          .getElementById("busq-prop-dni")
          .value.trim()
          .toUpperCase();
        const tbody = document.getElementById("tbody-prop");
        const alrt = "alert-busq-prop";
        if (!dni) {
          mostrarAlerta(alrt, "error", "Introduzca un DNI para buscar.");
          return;
        }
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="6">Buscando…</td></tr>';
        setContador("prop-contador", null);
        document.getElementById(alrt).classList.remove("show");
        try {
          const json = await (
            await fetch(API + "/propietarios/" + encodeURIComponent(dni))
          ).json();
          if (!json.ok) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="6">No se encontró ningún propietario con ese DNI.</td></tr>';
            mostrarAlerta(
              alrt,
              "error",
              `DNI «${dni}» no encontrado en el censo.`,
            );
            return;
          }
          setDatos("prop", [json.datos], "encontrado");
        } catch (err) {
          logError(
            err?.message || "Error al buscar propietario",
            "buscarPropietario",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="6">Error: ${err.message}</td></tr>`;
        }
      }
      async function buscarPorApellidos() {
        const ap1 = document
          .getElementById("busq-prop-apellido1")
          .value.trim()
          .toLowerCase();
        const ap2 = document
          .getElementById("busq-prop-apellido2")
          .value.trim()
          .toLowerCase();
        const tbody = document.getElementById("tbody-prop");
        const alrt = "alert-busq-prop";
        if (!ap1 && !ap2) {
          mostrarAlerta(
            alrt,
            "error",
            "Introduzca al menos un apellido para buscar.",
          );
          return;
        }
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="6">Buscando…</td></tr>';
        setContador("prop-contador", null);
        document.getElementById(alrt).classList.remove("show");
        try {
          const json = await (await fetch(API + "/propietarios")).json();
          if (!json.ok) throw new Error(json.error);
          const filtrados = json.datos.filter((r) => {
            const p1 = (r.PRIMER_APELLIDO || "").toLowerCase();
            const p2 = (r.SEGUNDO_APELLIDO || "").toLowerCase();
            return (!ap1 || p1.includes(ap1)) && (!ap2 || p2.includes(ap2));
          });
          if (!filtrados.length) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="6">Sin resultados para ese criterio.</td></tr>';
            const criterio = [ap1 && `«${ap1}»`, ap2 && `«${ap2}»`]
              .filter(Boolean)
              .join(" + ");
            mostrarAlerta(
              alrt,
              "error",
              `No se encontró ningún propietario con los apellidos ${criterio}.`,
            );
            return;
          }
          setDatos("prop", filtrados, "encontrados");
        } catch (err) {
          logError(
            err?.message || "Error al buscar por apellidos",
            "buscarPorApellidos",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="6">Error: ${err.message}</td></tr>`;
        }
      }
      async function abrirFichaProp(dni) {
        if (!dni) return;
        const modal = document.getElementById("modal-ficha");
        const body = document.getElementById("ficha-body");
        const titulo = document.getElementById("ficha-titulo");
        titulo.textContent = "Cargando…";
        body.innerHTML =
          '<div style="padding:2rem;text-align:center;color:var(--gris3);">Cargando ficha…</div>';
        modal.style.display = "flex";
        try {
          const json = await (
            await fetch(API + "/ficha_propietario/" + encodeURIComponent(dni))
          ).json();
          if (!json.ok) {
            body.innerHTML = `<div style="padding:1.5rem;color:var(--rojo);">${json.error}</div>`;
            return;
          }
          const p = json.propietario;
          const nom = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO]
            .filter(Boolean)
            .join(" ");
          titulo.textContent = nom + " · " + dni;

          const camposProp = [
            ["DNI", p.DNI || "—"],
            ["Nombre", nom || "—"],
            ["Teléfono 1", p.TELEFONO1 || "—"],
            ["Teléfono 2", p.TELEFONO2 || "—"],
          ];
          const filasDatos = camposProp
            .map(
              ([k, v]) =>
                `<tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;` +
                `color:var(--gris3);padding:.35rem .75rem;white-space:nowrap;width:35%;">${k}</td>` +
                `<td style="font-size:.85rem;padding:.35rem .75rem;font-family:'IBM Plex Mono',monospace;">${v}</td></tr>`,
            )
            .join("");

          // Direcciones del propietario
          const dirs = json.direcciones || [];
          let htmlDirs = '';
          if (dirs.length) {
            htmlDirs = `<table style="width:100%;border-collapse:collapse;font-size:.82rem;">
              <thead><tr>
                <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Domicilio</th>
                <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">C.P.</th>
                <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Municipio</th>
                <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:center;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;width:60px;"></th>
              </tr></thead>
              <tbody>${dirs.map(d =>
                `<tr style="border-bottom:1px solid var(--borde2);" id="dir-row-${d.CODIGO}">` +
                `<td style="padding:.3rem .6rem;">${d.DOMICILIO || '—'}</td>` +
                `<td style="padding:.3rem .6rem;font-family:'IBM Plex Mono',monospace;">${d.CP || '—'}</td>` +
                `<td style="padding:.3rem .6rem;">${d.MINICIPIO || '—'}</td>` +
                `<td style="padding:.3rem .6rem;text-align:center;">` +
                `<button onclick="eliminarDireccionFicha('${dni}',${d.CODIGO})" ` +
                `style="background:none;border:1px solid var(--rojo);color:var(--rojo);padding:.15rem .4rem;` +
                `font-size:.7rem;cursor:pointer;border-radius:2px;" title="Quitar domicilio">✕</button></td></tr>`
              ).join('')}</tbody></table>`;
          } else {
            htmlDirs = '<p style="font-size:.82rem;color:var(--gris3);font-style:italic;">Sin domicilios registrados.</p>';
          }
          // Formulario para añadir nuevo domicilio
          const htmlAddDir = `<div style="margin-top:.6rem;display:flex;gap:.4rem;align-items:end;flex-wrap:wrap;" id="ficha-add-dir">
            <input type="text" id="ficha-new-dom" placeholder="Domicilio" style="flex:2;min-width:140px;padding:.3rem .5rem;font-size:.8rem;border:1px solid var(--borde);font-family:inherit;" />
            <input type="text" id="ficha-new-cp" placeholder="C.P." maxlength="10" style="width:70px;padding:.3rem .5rem;font-size:.8rem;border:1px solid var(--borde);font-family:inherit;" />
            <input type="text" id="ficha-new-mun" placeholder="Municipio" style="flex:1;min-width:100px;padding:.3rem .5rem;font-size:.8rem;border:1px solid var(--borde);font-family:inherit;" />
            <button onclick="addDireccionFicha('${dni}')" style="background:var(--azul);color:#fff;border:none;padding:.35rem .7rem;font-size:.75rem;cursor:pointer;white-space:nowrap;">+ Añadir</button>
          </div>`;

          const activos = json.animales.filter((a) => !a.DADO_DE_BAJA);
          const inactivos = json.animales.filter((a) => a.DADO_DE_BAJA);
          function tablaAnimales(lista, baja) {
            if (!lista.length)
              return `<p style="font-size:.82rem;color:var(--gris3);font-style:italic;">Ninguno.</p>`;
            return (
              `<table style="width:100%;border-collapse:collapse;font-size:.82rem;">
        <thead><tr>
          <th style="background:${baja ? "var(--gris2)" : "var(--azul)"};color:${baja ? "var(--gris4)" : "#fff"};` +
              `padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Chip</th>
          <th style="background:${baja ? "var(--gris2)" : "var(--azul)"};color:${baja ? "var(--gris4)" : "#fff"};` +
              `padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Nombre</th>
          <th style="background:${baja ? "var(--gris2)" : "var(--azul)"};color:${baja ? "var(--gris4)" : "#fff"};` +
              `padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Especie</th>
          <th style="background:${baja ? "var(--gris2)" : "var(--azul)"};color:${baja ? "var(--gris4)" : "#fff"};` +
              `padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Raza</th>
        </tr></thead>
        <tbody>${lista
          .map((a) => {
            const chip = a.N_CHIP || "—";
            return (
              `<tr style="cursor:pointer;border-bottom:1px solid var(--borde2);" ` +
              `onclick="cerrarFicha();setTimeout(()=>abrirFicha('${chip.replace(/'/g, "\\'")}'),120)">` +
              `<td style="padding:.3rem .6rem;font-family:'IBM Plex Mono',monospace;font-size:.75rem;">` +
              `<span class="tag tag-id">${chip}</span></td>` +
              `<td style="padding:.3rem .6rem;">${a.NOMBRE || "(sin nombre)"}</td>` +
              `<td style="padding:.3rem .6rem;">${a.ESPECIE || "—"}</td>` +
              `<td style="padding:.3rem .6rem;">${a.RAZA || "—"}</td></tr>`
            );
          })
          .join("")}</tbody>
      </table>`
            );
          }

          let htmlSeg =
            '<p style="font-size:.82rem;color:var(--gris3);font-style:italic;">Sin pólizas.</p>';
          if (json.seguros.length) {
            htmlSeg = `<table style="width:100%;border-collapse:collapse;font-size:.82rem;">
        <thead><tr>
          <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Chip</th>
          <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Animal</th>
          <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Compañía</th>
          <th style="background:var(--azul);color:#fff;padding:.3rem .6rem;text-align:left;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;">Póliza</th>
        </tr></thead>
        <tbody>${json.seguros
          .map(
            (s) =>
              `<tr style="border-bottom:1px solid var(--borde2);">
            <td style="padding:.3rem .6rem;font-family:'IBM Plex Mono',monospace;font-size:.75rem;">${s.N_CHIP || "—"}</td>
            <td style="padding:.3rem .6rem;">${s.NOMBRE_ANIMAL || "—"}</td>
            <td style="padding:.3rem .6rem;">${s.SEGURO_COMPANIA || "—"}</td>
            <td style="padding:.3rem .6rem;font-family:'IBM Plex Mono',monospace;">${s.SEGURO_POLIZA || "—"}</td>
          </tr>`,
          )
          .join("")}</tbody>
      </table>`;
          }

          const sec = (titulo, html) =>
            `<div style="margin-bottom:1.25rem;">
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;` +
            `color:var(--azul);border-bottom:2px solid var(--azul);padding-bottom:.3rem;margin-bottom:.5rem;">${titulo}</div>
        ${html}
      </div>`;

          body.innerHTML =
            sec(
              "Datos del propietario",
              `<table style="width:100%;border-collapse:collapse;">${filasDatos}</table>`,
            ) +
            sec(
              `Domicilios (${dirs.length})`,
              htmlDirs + htmlAddDir,
            ) +
            sec(
              `Animales activos (${activos.length})`,
              tablaAnimales(activos, false),
            ) +
            (inactivos.length
              ? sec(
                  `Animales dados de baja (${inactivos.length})`,
                  tablaAnimales(inactivos, true),
                )
              : "") +
            sec("Seguros", htmlSeg);
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          body.innerHTML = `<div style="padding:1.5rem;color:var(--rojo);">Error: ${err.message}</div>`;
        }
      }

      // ── CRUD de direcciones desde la ficha ──────────────────
      async function addDireccionFicha(dni) {
        const dom = document.getElementById("ficha-new-dom")?.value.trim();
        const cp = document.getElementById("ficha-new-cp")?.value.trim();
        const mun = document.getElementById("ficha-new-mun")?.value.trim();
        if (!dom) return;
        try {
          const res = await fetch(API + "/propietarios/" + encodeURIComponent(dni) + "/direcciones", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ DOMICILIO: dom, CP: cp, MINICIPIO: mun }),
          });
          const json = await res.json();
          if (json.ok) {
            abrirFichaProp(dni); // recargar ficha
          } else {
            alert(json.error || "Error al añadir domicilio.");
          }
        } catch (err) {
          logError(err?.message || "Error al añadir dirección", "addDireccionFicha", err?.stack);
          alert("No se pudo conectar con el servidor.");
        }
      }
      async function eliminarDireccionFicha(dni, codigo) {
        if (!confirm("¿Eliminar este domicilio del registro?")) return;
        try {
          const res = await fetch(
            API + "/propietarios/" + encodeURIComponent(dni) + "/direcciones/" + codigo,
            { method: "DELETE" },
          );
          const json = await res.json();
          if (json.ok) {
            abrirFichaProp(dni); // recargar ficha
          } else {
            alert(json.error || "Error al eliminar domicilio.");
          }
        } catch (err) {
          logError(err?.message || "Error al eliminar dirección", "eliminarDireccionFicha", err?.stack);
          alert("No se pudo conectar con el servidor.");
        }
      }
