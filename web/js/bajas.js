      const estadoBajas = { datos: [], todosDatos: [], pagina: 1 };
      const bajaEstado = {
        paso: 1,
        propietario: null,
        animales: [],
        chipSeleccionado: null,
        nombreAnimal: null,
      };
      async function _poblarSelectMotivos() {
        const sel = document.getElementById("busq-baja-motivo");
        if (!sel) return;
        try {
          const json = await (await fetch(API + "/motivos_baja")).json();
          if (!json.ok || !json.datos.length) return;
          const actual = sel.value;
          sel.innerHTML = '<option value="">— Todos —</option>';
          json.datos.forEach((r) => {
            const opt = document.createElement("option");
            opt.value = r.CLAVE;
            opt.textContent = r.MOTIVO_BAJA;
            sel.appendChild(opt);
          });
          if (actual) sel.value = actual;
        } catch (e) {
          logError(
            e?.message || "Error al poblar motivos de baja",
            "_poblarSelectMotivos",
            e?.stack,
          );
        }
      }
      async function cargarBajas() {
        const tbody = document.getElementById("tbody-bajas");
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="10">Cargando…</td></tr>';
        try {
          const json = await (await fetch(API + "/bajas")).json();
          if (!json.ok) throw new Error(json.error);
          estadoBajas.todosDatos = json.datos;
          estadoBajas.datos = json.datos;
          estadoBajas.pagina = 1;
          setDatosBajas(json.datos, "encontrados");
          mostrarTabla("bajas");
        } catch (err) {
          logError(
            err?.message || "Error al cargar bajas",
            "cargarBajas",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="10">Error: ${err.message}</td></tr>`;
        }
      }
      function buscarBajas() {
        const chip = document
          .getElementById("busq-baja-chip")
          .value.trim()
          .toUpperCase();
        const dni = document
          .getElementById("busq-baja-dni")
          .value.trim()
          .toUpperCase();
        const motivo = document.getElementById("busq-baja-motivo").value;
        const filtrados = (
          estadoBajas.todosDatos.length
            ? estadoBajas.todosDatos
            : estadoBajas.datos
        ).filter((r) => {
          const okChip = !chip || (r.N_CHIP || "").toUpperCase().includes(chip);
          const okDni =
            !dni || (r.DNI_PROPIETARIO || "").toUpperCase().includes(dni);
          const okMotivo = !motivo || String(r.MOTIVO) === String(motivo);
          return okChip && okDni && okMotivo;
        });
        if (!filtrados.length && estadoBajas.datos.length === 0) {
          cargarBajas().then(() => buscarBajas());
          return;
        }
        estadoBajas.pagina = 1;
        setDatosBajas(filtrados, "encontrados");
        mostrarTabla("bajas");
      }
      function setDatosBajas(datos, tipo) {
        estadoBajas.datos = datos;
        if (!estadoBajas.todosDatos.length) estadoBajas.todosDatos = datos;
        renderPaginaBajas();
        const cont = document.getElementById("baja-contador");
        cont.textContent = datos.length
          ? `${datos.length} registro${datos.length > 1 ? "s" : ""} ${tipo}`
          : "Sin resultados";
        document.getElementById("btn-ocultar-bajas").style.display =
          datos.length ? "" : "none";
      }
      function renderPaginaBajas() {
        const tbody = document.getElementById("tbody-bajas");
        const total = estadoBajas.datos.length;
        if (!total) {
          tbody.innerHTML =
            '<tr class="empty-row"><td colspan="10">Sin resultados.</td></tr>';
          document.getElementById("pag-bajas").innerHTML = "";
          return;
        }
        const inicio = (estadoBajas.pagina - 1) * POR_PAGINA;
        const pagina = estadoBajas.datos.slice(inicio, inicio + POR_PAGINA);
        tbody.innerHTML = pagina
          .map((r) => {
            const nombreProp =
              [r.NOMBRE_PROP, r.PRIMER_APELLIDO, r.SEGUNDO_APELLIDO]
                .filter(Boolean)
                .join(" ") || "—";
            const fecha = r.FECHA_BAJA ? r.FECHA_BAJA.substring(0, 10) : "—";
            return `<tr style="cursor:pointer;" title="Ver ficha del animal" data-chip="${r.N_CHIP || ""}" onclick="abrirFicha(this.dataset.chip)"> <td data-label="Chip"><code class="u-mono">${r.N_CHIP || "—"}</code></td> <td data-label="Animal">${r.NOMBRE_ANIMAL || "—"}</td> <td data-label="Especie">${r.ESPECIE || "—"}</td> <td data-label="Raza">${r.RAZA || "—"}</td> <td data-label="Propietario">${nombreProp}</td> <td data-label="DNI"><code class="u-mono">${r.DNI_PROPIETARIO || "—"}</code></td> <td><span style="background:var(--rojo);color:#fff;padding:.15rem .5rem;border-radius:0;font-size:.75rem;font-weight:600;">
 ${r.MOTIVO_DESC || r.MOTIVO || "—"}
 </span></td> <td>${fecha}</td> <td>${r.N_BAJA || "—"}</td> <td style="max-width:180px;white-space:normal;">${r.OBSERVACIONES || "—"}</td> </tr>`;
          })
          .join("");
        const totalPags = Math.max(1, Math.ceil(total / POR_PAGINA));
        const pag = document.getElementById("pag-bajas");
        let html = "";
        if (estadoBajas.pagina > 1)
          html += `<button class="pag-btn" onclick="irPaginaBajas(${estadoBajas.pagina - 1})">‹ Anterior</button>`;
        html += `<span class="pag-info">Página ${estadoBajas.pagina} de ${totalPags}</span>`;
        if (estadoBajas.pagina < totalPags)
          html += `<button class="pag-btn" onclick="irPaginaBajas(${estadoBajas.pagina + 1})">Siguiente ›</button>`;
        pag.innerHTML = html;
      }
      function irPaginaBajas(n) {
        estadoBajas.pagina = n;
        renderPaginaBajas();
        document
          .getElementById("tabla-wrap-bajas")
          .scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
      function bajaActualizarStepper() {
        const p = bajaEstado.paso;
        [1, 2, 3].forEach((n) => {
          const el = document.getElementById("step-ind-" + n);
          el.classList.remove("active", "done");
          if (n < p) el.classList.add("done");
          else if (n === p) el.classList.add("active");
        });
      }
      function bajaMostrarPaso(n) {
        [1, 2, 3, "ok"].forEach((id) => {
          const el = document.getElementById("baja-paso-" + id);
          if (el) el.style.display = "none";
        });
        document.getElementById("baja-paso-" + n).style.display = "";
        bajaEstado.paso = n === "ok" ? 4 : n;
        bajaActualizarStepper();
      }
      function validarDniBaja(input) {
        const v = input.value.trim();
        const hint = document.getElementById("baja-dni-hint");
        if (!v) {
          hint.textContent = "";
          hint.className = "campo-hint";
          return;
        }
        const res = validarFormatoDNI(v);
        if (res.ok === true) {
          hint.textContent = "Formato correcto";
          hint.className = "campo-hint hint-ok";
        } else if (v.length >= 9) {
          hint.textContent =
            res.msg || "Formato o letra de control incorrectos";
          hint.className = "campo-hint hint-error";
        } else {
          hint.textContent = "";
          hint.className = "campo-hint";
        }
      }
      async function verificarPropietarioBaja() {
        const dniInputBaja = document.getElementById("baja-dni");
        const dni = dniInputBaja.value.trim().toUpperCase();
        if (!dni) {
          mostrarAlerta("alert-baja", "error", "Introduzca su DNI o NIE.");
          return;
        }
        const fmtBaja = validarFormatoDNI(dni);
        if (fmtBaja.ok !== true) {
          dniInputBaja.classList.add("dni-error");
          const hintBaja = document.getElementById("baja-dni-hint");
          if (hintBaja) {
            hintBaja.textContent = fmtBaja.msg || "Formato incorrecto";
            hintBaja.className = "campo-hint hint-error";
          }
          mostrarAlerta(
            "alert-baja",
            "error",
            "El DNI o NIE introducido no es válido.",
          );
          return;
        }
        const btn = document.getElementById("btn-verificar-baja");
        btn.disabled = true;
        btn.textContent = "Verificando...";
        try {
          const resp = await fetch(
            API + "/propietarios/" + encodeURIComponent(dni) + "/animales",
          );
          const json = await resp.json().catch(() => ({
            ok: false,
            error:
              "El servidor devolvió una respuesta inesperada (HTTP " +
              resp.status +
              ").",
          }));
          if (!json.ok) {
            mostrarAlerta("alert-baja", "error", json.error);
            return;
          }
          const prop = json.propietario;
          bajaEstado.propietario = prop;
          bajaEstado.animales = json.animales;
          const nombre = [
            prop.NOMBRE,
            prop.PRIMER_APELLIDO,
            prop.SEGUNDO_APELLIDO,
          ]
            .filter(Boolean)
            .join(" ");
          document.getElementById("baja-info-propietario").innerHTML =
            `<strong>${nombre}</strong> <span>DNI: ${prop.DNI}</span>`;
          const grid = document.getElementById("baja-lista-animales");
          if (!json.animales.length) {
            grid.innerHTML = `<div class="baja-animal-vacio">
 No hay animales activos registrados a su nombre.
 </div>`;
          } else {
            grid.innerHTML = json.animales
              .map(
                (a) => `
 <div class="baja-animal-item" data-chip="${a.N_CHIP}"
 onclick="bajaSeleccionarAnimal('${a.N_CHIP}', '${(a.NOMBRE || "Sin nombre").replace(/'/g, "\\'")}', '${(a.ESPECIE || "").replace(/'/g, "\\'")}', '${(a.RAZA || "").replace(/'/g, "\\'")}', '${a.N_CHIP}')"> <div class="anim-chip">Chip: ${a.N_CHIP}</div> <div class="anim-nombre">${a.NOMBRE || "(sin nombre)"}</div> <div class="anim-especie">${[a.ESPECIE, a.RAZA].filter(Boolean).join(" · ")}</div> </div>
 `,
              )
              .join("");
          }
          bajaMostrarPaso(2);
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          mostrarAlerta(
            "alert-baja",
            "error",
            "Error: " + (err.message || "No se pudo conectar con el servidor."),
          );
        } finally {
          btn.disabled = false;
          btn.textContent = "Verificar";
        }
      }
      function bajaSeleccionarAnimal(chip, nombre, especie, raza, chipDisplay) {
        bajaEstado.chipSeleccionado = chip;
        bajaEstado.nombreAnimal = nombre;
        document.querySelectorAll(".baja-animal-item").forEach((el) => {
          el.classList.toggle("seleccionado", el.dataset.chip === chip);
        });
        const prop = bajaEstado.propietario;
        const nombreProp = [
          prop.NOMBRE,
          prop.PRIMER_APELLIDO,
          prop.SEGUNDO_APELLIDO,
        ]
          .filter(Boolean)
          .join(" ");
        document.getElementById("baja-info-animal-seleccionado").innerHTML =
          `<strong>${nombre || "(sin nombre)"}</strong>
 N.º chip: <code style="font-family:'IBM Plex Mono',monospace;">${chipDisplay}</code>
 &nbsp;·&nbsp; Especie: ${especie || "—"}&nbsp;·&nbsp;Raza: ${raza || "—"}<br>
 Propietario: ${nombreProp} (${prop.DNI})`;
        const sel = document.getElementById("baja-motivo");
        if (sel.options.length <= 1) cargarMotivosBaja();
        bajaMostrarPaso(3);
      }
      async function cargarMotivosBaja() {
        const sel = document.getElementById("baja-motivo");
        try {
          const json = await (await fetch(API + "/motivos_baja")).json();
          if (!json.ok || !json.datos.length) throw new Error();
          sel.innerHTML =
            '<option value="">— Seleccionar —</option>' +
            json.datos
              .map(
                (r) => `<option value="${r.CLAVE}">${r.MOTIVO_BAJA}</option>`,
              )
              .join("");
        } catch (e) {
          logError(
            e?.message || "Error cargando motivos baja",
            "cargarMotivosBaja",
            e?.stack,
          );
          sel.innerHTML = `<option value="">— Seleccionar —</option><option value="1001">FALLECIMIENTO</option><option value="1002">CESIÓN</option>`;
        }
      }
      function bajaPaso2Cancelar() {
        document.getElementById("baja-dni").value = "";
        document.getElementById("baja-dni-hint").textContent = "";
        document.getElementById("alert-baja").classList.remove("show");
        bajaMostrarPaso(1);
      }
      function bajaPaso3Cancelar() {
        bajaEstado.chipSeleccionado = null;
        bajaMostrarPaso(2);
      }
      async function confirmarBaja() {
        const motivo = document.getElementById("baja-motivo").value;
        if (!motivo) {
          mostrarAlerta("alert-baja", "error", "Seleccione el motivo de baja.");
          return;
        }
        const btn = document.getElementById("btn-confirmar-baja");
        btn.disabled = true;
        btn.textContent = "Registrando...";
        const payload = {
          N_CHIP: bajaEstado.chipSeleccionado,
          DNI: bajaEstado.propietario.DNI,
          MOTIVO: motivo,
          N_BAJA: document.getElementById("baja-num").value.trim(),
          OBSERVACIONES: document.getElementById("baja-obs").value.trim(),
        };
        try {
          const json = await (
            await fetch(API + "/bajas", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            })
          ).json();
          if (!json.ok) {
            mostrarAlerta("alert-baja", "error", json.error);
            return;
          }
          document.getElementById("baja-ok-detalle").textContent =
            `N.º baja: ${json.n_baja || "—"} · ` +
            `Animal: ${bajaEstado.nombreAnimal || bajaEstado.chipSeleccionado} · ` +
            `DNI: ${bajaEstado.propietario.DNI}`;
          bajaMostrarPaso("ok");
        } catch (e) {
          logError(
            e?.message || "Error al confirmar baja",
            "confirmarBaja",
            e?.stack,
          );
          mostrarAlerta(
            "alert-baja",
            "error",
            "No se pudo conectar con el servidor.",
          );
        } finally {
          btn.disabled = false;
          btn.textContent = "Registrar baja";
        }
      }
      function bajaReiniciar() {
        Object.assign(bajaEstado, {
          paso: 1,
          propietario: null,
          animales: [],
          chipSeleccionado: null,
          nombreAnimal: null,
        });
        document.getElementById("baja-dni").value = "";
        document.getElementById("baja-num").value = "";
        document.getElementById("baja-obs").value = "";
        document.getElementById("baja-motivo").selectedIndex = 0;
        document.getElementById("baja-dni-hint").textContent = "";
        document.getElementById("alert-baja").classList.remove("show");
        bajaMostrarPaso(1);
      }
      _poblarSelectMotivos();
