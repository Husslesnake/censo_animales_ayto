      var _ultimoDniAnimal = "";
      async function submitAnimal(e) {
        e.preventDefault();
        const dniAnimInput = document.getElementById("anim-dni-prop");
        if (dniAnimInput && !validarCampoDni(dniAnimInput, "hint-anim-dni")) {
          dniAnimInput.focus();
          mostrarAlerta(
            "alert-anim",
            "error",
            "El DNI o NIE del propietario no es válido.",
          );
          return;
        }
        const btn = document.getElementById("btn-anim");
        const sp = document.getElementById("sp-anim");
        btn.disabled = true;
        sp.style.display = "block";
        const fd = new FormData(e.target);
        const data = {};
        for (const [k, v] of fd.entries()) {
          if (v instanceof File) continue;
          if (v) data[k] = v;
        }
        ["ESTERILIZADO", "PELIGROSO"].forEach((k) => {
          if (!(k in data)) data[k] = 0;
          fd.set(k, String(data[k]));
        });
        const fotoInput = document.getElementById("inp-foto-anim");
        const tieneFoto = fotoInput && fotoInput.files && fotoInput.files.length > 0;
        try {
          const res = await fetch(API + "/animales", {
            method: "POST",
            ...(tieneFoto
              ? { body: fd }
              : {
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(data),
                }),
          });
          const json = await res.json();
          if (json.ok) {
            _ultimoDniAnimal = data.DNI_PROPIETARIO || "";
            const ncenso = json.n_censo || "";
            if (ncenso) {
              var el = document.getElementById("anim-ncenso-display");
              if (el) {
                el.textContent = ncenso;
                el.style.color = "var(--verde)";
                el.style.fontWeight = "700";
              }
            }
            mostrarAlerta(
              "alert-anim",
              "ok",
              json.mensaje + (ncenso ? " · N.º censo: " + ncenso : ""),
            );
            const dni = data.DNI_PROPIETARIO || "";
            e.target.reset();
            if (typeof quitarFotoAnimal === "function") quitarFotoAnimal();
            if (dni) {
              const inp = document.getElementById("anim-dni-prop");
              if (inp) {
                inp.value = dni;
                buscarPropietarioAnim(dni);
              }
            }
            document.getElementById("btn-otro-animal-wrap").style.display = "";
          } else if (json.limite_alcanzado) {
            mostrarAlerta("alert-anim", "error", `⚠️ ${json.error}`);
            document.getElementById("btn-otro-animal-wrap").style.display =
              "none";
          } else if (json.chip_duplicado) {
            const chipInput = document.querySelector(
              "#form-anim [name='N_CHIP']",
            );
            if (chipInput) {
              chipInput.classList.add("dni-error");
              chipInput.focus();
            }
            mostrarAlerta("alert-anim", "error", `⚠️ ${json.error}`);
          } else {
            mostrarAlerta("alert-anim", "error", json.error);
          }
        } catch (e) {
          logError(
            e?.message || "No se pudo conectar con el servidor",
            "submitAnimal",
            e?.stack,
          );
          mostrarAlerta(
            "alert-anim",
            "error",
            "No se pudo conectar con el servidor.",
          );
        }
        btn.disabled = false;
        sp.style.display = "none";
      }
      async function buscarPropietarioAnim(dni) {
        if (!dni || dni.length < 8) return;
        const card = document.getElementById("anim-prop-card");
        const sel = document.getElementById("sel-domicilio-anim");
        try {
          const dniNorm = encodeURIComponent(dni.trim().toUpperCase());
          const [jsonProp, jsonDirs] = await Promise.all([
            fetch(API + "/propietarios/" + dniNorm).then(r => r.json()),
            fetch(API + "/propietarios/" + dniNorm + "/direcciones").then(r => r.json()),
          ]);
          if (jsonProp.ok && jsonProp.datos) {
            const p = jsonProp.datos;
            const nombre = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO]
              .filter(Boolean)
              .join(" ");
            card.innerHTML = `<div style="background:var(--azul);color:#fff;border-radius:0;padding:.65rem 1rem;font-size:.85rem;display:flex;align-items:center;gap:.75rem;"><span style="font-size:1.2rem;">&#10003;</span><span><strong>${nombre}</strong> &nbsp;·&nbsp; DNI: ${p.DNI}</span></div>`;
            card.style.display = "";
          } else {
            card.style.display = "none";
          }
          // Poblar select de domicilios (excluir los que ya tienen 5 animales)
          if (sel) {
            sel.innerHTML = '<option value="">— Seleccionar domicilio —</option>';
            if (jsonDirs.ok && jsonDirs.direcciones) {
              const disponibles = jsonDirs.direcciones.filter(d => (d.NUM_ANIMALES || 0) < 5);
              if (disponibles.length === 0) {
                sel.innerHTML = '<option value="">— Sin domicilios disponibles —</option>';
              } else {
                disponibles.forEach(d => {
                  const txt = [d.DOMICILIO, d.CP, d.MINICIPIO].filter(Boolean).join(", ");
                  const n = d.NUM_ANIMALES || 0;
                  const opt = document.createElement("option");
                  opt.value = d.CODIGO;
                  opt.textContent = txt + ` (${n}/5 animales)`;
                  sel.appendChild(opt);
                });
              }
            } else {
              sel.innerHTML = '<option value="">— Sin domicilios registrados —</option>';
            }
          }
        } catch (e) {
          logError(
            e?.message || "Error al buscar propietario",
            "buscarPropietarioAnim",
            e?.stack,
          );
          card.style.display = "none";
          if (sel) sel.innerHTML = '<option value="">— Error al cargar domicilios —</option>';
        }
      }
      function otroAnimalMismoPropietario() {
        const dni = _ultimoDniAnimal;
        document.getElementById("form-anim").reset();
        document.getElementById("alert-anim").classList.remove("show");
        var el = document.getElementById("anim-ncenso-display");
        if (el) {
          el.textContent = "Se asignará automáticamente";
          el.style.color = "";
          el.style.fontWeight = "";
        }
        document.getElementById("btn-otro-animal-wrap").style.display = "";
        if (dni) {
          const inp = document.getElementById("anim-dni-prop");
          if (inp) {
            inp.value = dni;
            buscarPropietarioAnim(dni);
          }
        }
        document.querySelector("#form-anim [name=N_CHIP]").focus();
      }
      function limpiarChipHint() {
        const inp = document.getElementById("anim-chip-input");
        const hint = document.getElementById("hint-anim-chip");
        if (inp) {
          inp.classList.remove("dni-ok", "dni-error");
        }
        if (hint) {
          hint.textContent = "";
          hint.className = "dni-hint";
        }
      }
      function limpiarPropCard() {
        _ultimoDniAnimal = "";
        document.getElementById("anim-prop-card").style.display = "none";
        document.getElementById("btn-otro-animal-wrap").style.display = "none";
        var el = document.getElementById("anim-ncenso-display");
        if (el) {
          el.textContent = "Se asignará automáticamente";
          el.style.color = "";
          el.style.fontWeight = "";
        }
        var sel = document.getElementById("sel-domicilio-anim");
        if (sel) sel.innerHTML = '<option value="">— Introduzca DNI del propietario —</option>';
      }
      async function cargarAnimales() {
        const tbody = document.getElementById("tbody-anim");
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="7">Cargando…</td></tr>';
        setContador("anim-contador", null);
        document.getElementById("alert-busq-anim").classList.remove("show");
        try {
          const json = await (await fetch(API + "/animales")).json();
          if (!json.ok) throw new Error(json.error);
          if (!json.datos.length) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="7">Sin registros.</td></tr>';
            return;
          }
          setDatos("anim", json.datos, "encontrados");
        } catch (err) {
          logError(
            err?.message || "Error al cargar animales",
            "cargarAnimales",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Error: ${err.message}</td></tr>`;
        }
      }
      async function buscarAnimal() {
        const chip = document
          .getElementById("busq-anim-chip")
          .value.trim()
          .toUpperCase();
        const tbody = document.getElementById("tbody-anim");
        const alrt = "alert-busq-anim";
        if (!chip) {
          mostrarAlerta(
            alrt,
            "error",
            "Introduzca un número de chip para buscar.",
          );
          return;
        }
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="7">Buscando…</td></tr>';
        setContador("anim-contador", null);
        document.getElementById(alrt).classList.remove("show");
        try {
          const json = await (
            await fetch(API + "/animales/" + encodeURIComponent(chip))
          ).json();
          if (!json.ok) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="7">No se encontró ningún animal con ese chip.</td></tr>';
            mostrarAlerta(
              alrt,
              "error",
              `Chip «${chip}» no encontrado en el censo.`,
            );
            return;
          }
          setDatos("anim", [json.datos], "encontrado");
        } catch (err) {
          logError(
            err?.message || "Error al buscar animal",
            "buscarAnimal",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Error: ${err.message}</td></tr>`;
        }
      }
      async function buscarAnimalesPorDni() {
        const dni = document
          .getElementById("busq-anim-dni")
          .value.trim()
          .toUpperCase();
        const tbody = document.getElementById("tbody-anim");
        const alrt = "alert-busq-anim";
        if (!dni) {
          mostrarAlerta(
            alrt,
            "error",
            "Introduzca un DNI de propietario para buscar.",
          );
          return;
        }
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="7">Buscando…</td></tr>';
        setContador("anim-contador", null);
        document.getElementById(alrt).classList.remove("show");
        try {
          const json = await (await fetch(API + "/animales")).json();
          if (!json.ok) throw new Error(json.error);
          const filtrados = json.datos.filter(
            (r) => (r.DNI_PROPIETARIO || "").toUpperCase() === dni,
          );
          if (!filtrados.length) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="7">No se encontraron animales para ese DNI.</td></tr>';
            mostrarAlerta(
              alrt,
              "error",
              `No hay animales registrados para el DNI «${dni}».`,
            );
            return;
          }
          setDatos("anim", filtrados, "encontrados");
        } catch (err) {
          logError(
            err?.message || "Error al buscar animales por DNI",
            "buscarAnimalesPorDni",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Error: ${err.message}</td></tr>`;
        }
      }
      let _chipEditando = null;
      async function abrirEditorAnimal() {
        const chip = document
          .getElementById("editar-busq-chip")
          .value.trim()
          .toUpperCase();
        const alrt = "alert-editar-busq";
        if (!chip) {
          mostrarAlerta(alrt, "error", "Introduzca un número de chip.");
          return;
        }
        try {
          const json = await (
            await fetch(API + "/animales/" + encodeURIComponent(chip))
          ).json();
          if (!json.ok) {
            mostrarAlerta(
              alrt,
              "error",
              `No se encontró ningún animal con el chip «${chip}».`,
            );
            return;
          }
          document.getElementById("alert-editar-busq").classList.remove("show");
          _rellenarModalEditar(json.datos);
        } catch (e) {
          logError(
            e?.message || "Error al buscar animal para editar",
            "abrirEditorAnimal",
            e?.stack,
          );
          mostrarAlerta(alrt, "error", "No se pudo conectar con el servidor.");
        }
      }
      function _rellenarModalEditar(r) {
        _chipEditando = r["N_CHIP"] || r["Nº_CHIP"] || "";
        document.getElementById("modal-editar-titulo").textContent =
          "Editar: " + (r.NOMBRE || r.ESPECIE || _chipEditando);
        document.getElementById("edit-chip-display").textContent =
          _chipEditando;
        document.getElementById("edit-prop-display").textContent =
          r.DNI_PROPIETARIO || "—";

        const dniInp = document.getElementById("edit-dni-prop");
        dniInp.value = r.DNI_PROPIETARIO || "";
        dniInp.classList.remove("dni-ok", "dni-error");
        const hintDni = document.getElementById("hint-edit-dni");
        if (hintDni) {
          hintDni.textContent = "";
          hintDni.className = "dni-hint";
        }

        document.getElementById("edit-vacuna").value = (
          r.FECHA_ULTIMA_VACUNA_ANTIRRABICA ||
          r.FECHA_ULTIMA_VACUNACION_ANTIRRABICA ||
          ""
        ).substring(0, 10);

        document.getElementById("edit-esterilizado").value =
          r.ESTERILIZADO == 1 ? "1" : "0";

        document.getElementById("edit-poliza").value = "";
        fetch(API + "/seguros")
          .then((r) => r.json())
          .then((json) => {
            if (!json.ok) return;
            const seg = json.datos.find((s) => s.N_CHIP === _chipEditando);
            if (seg)
              document.getElementById("edit-poliza").value =
                seg.SEGURO_POLIZA || "";
          })
          .catch((e) => {
            logError(
              e?.message || "Error al cargar seguros en editor",
              "_rellenarModalEditar",
              e?.stack,
            );
          });
        document.getElementById("alert-editar-modal").classList.remove("show");
        document.getElementById("modal-editar").style.display = "flex";
      }
      function cerrarEditorAnimal() {
        document.getElementById("modal-editar").style.display = "none";
        _chipEditando = null;
      }
      async function guardarEdicionAnimal() {
        if (!_chipEditando) return;

        const dniInp = document.getElementById("edit-dni-prop");
        const dniVal = dniInp.value.trim().toUpperCase();
        if (dniVal) {
          const fmt = validarFormatoDNI(dniVal);
          if (fmt.ok !== true) {
            dniInp.classList.add("dni-error");
            const h = document.getElementById("hint-edit-dni");
            if (h) {
              h.textContent = fmt.msg || "Formato incorrecto";
              h.className = "dni-hint error";
            }
            mostrarAlerta(
              "alert-editar-modal",
              "error",
              "El DNI o NIE introducido no es válido.",
            );
            return;
          }
        }
        const btn = document.getElementById("btn-guardar-editar");
        const sp = document.getElementById("sp-editar");
        btn.disabled = true;
        sp.style.display = "block";
        const payload = {
          DNI_PROPIETARIO: dniVal || undefined,
          FECHA_ULTIMA_VACUNA_ANTIRRABICA:
            document.getElementById("edit-vacuna").value || undefined,
          ESTERILIZADO: document.getElementById("edit-esterilizado").value,
          SEGURO_POLIZA:
            document.getElementById("edit-poliza").value.trim() || undefined,
        };

        Object.keys(payload).forEach((k) => {
          if (payload[k] === undefined) delete payload[k];
        });
        try {
          const res = await fetch(
            API + "/animales/" + encodeURIComponent(_chipEditando),
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            },
          );
          const json = await res.json();
          if (json.ok) {
            mostrarAlerta("alert-editar-modal", "ok", "✔ " + json.mensaje);
            if (estado.anim && estado.anim.datos.length) {
              const idx = estado.anim.datos.findIndex(
                (r) => (r["N_CHIP"] || r["Nº_CHIP"]) === _chipEditando,
              );
              if (idx >= 0) Object.assign(estado.anim.datos[idx], payload);
              renderPagina("anim", estado.anim.pagina);
            }
            setTimeout(cerrarEditorAnimal, 1400);
          } else {
            mostrarAlerta("alert-editar-modal", "error", json.error);
          }
        } catch (err) {
          logError(
            err?.message || "Error al guardar edición",
            "guardarEdicionAnimal",
            err?.stack,
          );
          mostrarAlerta(
            "alert-editar-modal",
            "error",
            "Error: " + (err.message || "No se pudo conectar."),
          );
        } finally {
          btn.disabled = false;
          sp.style.display = "none";
        }
      }
      async function abrirFicha(chip) {
        const modal = document.getElementById("modal-ficha");
        const body = document.getElementById("ficha-body");
        const titulo = document.getElementById("ficha-titulo");
        if (!modal) return;
        titulo.textContent = "Cargando…";
        body.innerHTML =
          '<div style="padding:2rem;text-align:center;color:var(--gris3);">Cargando ficha…</div>';
        modal.style.display = "flex";
        try {
          const json = await (
            await fetch(API + "/ficha_animal/" + encodeURIComponent(chip))
          ).json();
          if (!json.ok) {
            body.innerHTML = `<div style="padding:1.5rem;color:var(--rojo);">${json.error}</div>`;
            return;
          }
          const a = json.animal;
          const p = json.propietario;
          const nombre = a.NOMBRE || "(sin nombre)";
          titulo.textContent = nombre + " · " + chip;

          const chipReal = a["Nº_CHIP"] || a["N_CHIP"] || chip;

          const camposAnimal = [
            ["Chip", chipReal],
            ["N.º censo", a.N_CENSO || a["Nº_CENSO"] || "—"],
            ["Especie", a.ESPECIE || "—"],
            ["Raza", a.RAZA || "—"],
            ["Sexo", a.SEXO || "—"],
            ["Color", a.COLOR || "—"],
            ["Año nacimiento", a.AÑO_DE_NACIMIENTO || "—"],
            [
              "Peligroso",
              String(a.PELIGROSO) === "1"
                ? '<span style="color:var(--rojo);font-weight:700;">Sí</span>'
                : "No",
            ],
            ["Esterilizado", String(a.ESTERILIZADO) === "1" ? "Sí" : "No"],
            [
              "Última vacuna antirrábica",
              (a.FECHA_ULTIMA_VACUNA_ANTIRRABICA ||
                a.FECHA_ULTIMA_VACUNACION_ANTIRRABICA ||
                "—") + "".substring(0, 10),
            ],
          ];

          const filasCampos = camposAnimal
            .map(
              ([k, v]) =>
                `<tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gris3);padding:.35rem .75rem;white-space:nowrap;">${k}</td>` +
                `<td style="font-size:.85rem;padding:.35rem .75rem;font-family:'IBM Plex Mono',monospace;">${v}</td></tr>`,
            )
            .join("");

          let htmlProp =
            '<p style="font-size:.85rem;color:var(--gris3);font-style:italic;">Sin propietario registrado.</p>';
          if (p) {
            const nomP = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO]
              .filter(Boolean)
              .join(" ");
            htmlProp = `<table style="width:100%;border-collapse:collapse;">
        <tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gris3);padding:.3rem .75rem;width:40%;">DNI</td><td style="font-family:'IBM Plex Mono',monospace;font-size:.85rem;padding:.3rem .75rem;">${p.DNI || "—"}</td></tr>
        <tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gris3);padding:.3rem .75rem;">Nombre</td><td style="font-family:'IBM Plex Mono',monospace;font-size:.85rem;padding:.3rem .75rem;">${nomP || "—"}</td></tr>
        <tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gris3);padding:.3rem .75rem;">Teléfono</td><td style="font-family:'IBM Plex Mono',monospace;font-size:.85rem;padding:.3rem .75rem;">${[p.TELEFONO1, p.TELEFONO2].filter(Boolean).join(" / ") || "—"}</td></tr>
        <tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gris3);padding:.3rem .75rem;">Domicilio</td><td style="font-family:'IBM Plex Mono',monospace;font-size:.85rem;padding:.3rem .75rem;">${p.DOMICILIO || "—"}</td></tr>
        <tr><td style="font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--gris3);padding:.3rem .75rem;">CP / Municipio</td><td style="font-family:'IBM Plex Mono',monospace;font-size:.85rem;padding:.3rem .75rem;">${[p.CP, p.MINICIPIO].filter(Boolean).join(" ") || "—"}</td></tr>
      </table>`;
          }

          let htmlSeg =
            '<p style="font-size:.85rem;color:var(--gris3);font-style:italic;">Sin pólizas registradas.</p>';
          if (json.seguros.length) {
            htmlSeg = json.seguros
              .map(
                (s) =>
                  `<div style="font-size:.82rem;padding:.3rem 0;font-family:'IBM Plex Mono',monospace;">
          ${s.SEGURO_COMPANIA || "—"} · Póliza: <strong>${s.SEGURO_POLIZA || "—"}</strong>
        </div>`,
              )
              .join("");
          }

          let htmlBaja = "";
          if (json.bajas.length) {
            htmlBaja =
              `<div style="margin-top:1rem;">
        <div style="font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--rojo);margin-bottom:.4rem;">Historial de bajas</div>` +
              json.bajas
                .map(
                  (b) =>
                    `<div style="font-size:.82rem;padding:.3rem;background:#f8f1f3;border-left:3px solid var(--rojo);margin-bottom:.35rem;font-family:'IBM Plex Mono',monospace;">
            N.º ${b.N_BAJA || "—"} · ${(b.FECHA_BAJA || "").substring(0, 10)} · ${b.MOTIVO_DESC || b.MOTIVO || "—"}
            ${b.OBSERVACIONES ? `<div style="color:var(--gris3);font-size:.75rem;margin-top:.15rem;">${b.OBSERVACIONES}</div>` : ""}
          </div>`,
                )
                .join("") +
              "</div>";
          }

          body.innerHTML = `
      <div style="margin-bottom:1.25rem;">
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--azul);border-bottom:2px solid var(--azul);padding-bottom:.3rem;margin-bottom:.5rem;">Datos del animal</div>
        <table style="width:100%;border-collapse:collapse;">${filasCampos}</table>
      </div>
      <div style="margin-bottom:1.25rem;">
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--azul);border-bottom:2px solid var(--azul);padding-bottom:.3rem;margin-bottom:.5rem;">Propietario</div>
        ${htmlProp}
      </div>
      <div>
        <div style="font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--azul);border-bottom:2px solid var(--azul);padding-bottom:.3rem;margin-bottom:.5rem;">Seguros</div>
        ${htmlSeg}
      </div>
      ${htmlBaja}
    `;
          var btnExp = document.getElementById("btn-export-ficha");
          if (btnExp) {
            btnExp.style.display = "";
            btnExp.onclick = function() { exportarFichaAnimalPDF(chip); };
          }
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          body.innerHTML = `<div style="padding:1.5rem;color:var(--rojo);">Error: ${err.message}</div>`;
        }
      }
      function cerrarFicha() {
        document.getElementById("modal-ficha").style.display = "none";
        var btnExp = document.getElementById("btn-export-ficha");
        if (btnExp) { btnExp.style.display = "none"; btnExp.onclick = null; }
      }
      function previewFotoAnimal(inp) {
        var wrap = document.getElementById("preview-foto-anim");
        var img = document.getElementById("preview-foto-anim-img");
        if (!inp.files || !inp.files.length) { wrap.style.display = "none"; img.src = ""; return; }
        var f = inp.files[0];
        if (!/^image\//.test(f.type)) {
          wrap.style.display = "none";
          mostrarAlerta("alert-anim", "error", "El archivo seleccionado no es una imagen.");
          inp.value = "";
          return;
        }
        var reader = new FileReader();
        reader.onload = function(e) { img.src = e.target.result; wrap.style.display = ""; };
        reader.readAsDataURL(f);
      }
      function quitarFotoAnimal() {
        var inp = document.getElementById("inp-foto-anim");
        if (inp) inp.value = "";
        var wrap = document.getElementById("preview-foto-anim");
        var img = document.getElementById("preview-foto-anim-img");
        if (wrap) wrap.style.display = "none";
        if (img) img.src = "";
      }
      // ── Exportación de informe PDF ────────────────────────────────────────
      function _abrirVentanaInforme(titulo, htmlContenido) {
        var w = window.open("", "_blank", "width=820,height=900");
        if (!w) {
          alert("El navegador ha bloqueado la ventana del informe. Permita las ventanas emergentes para esta página.");
          return;
        }
        var hoy = new Date().toLocaleString("es-ES");
        w.document.open();
        w.document.write(
          '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>' + titulo + '</title>' +
          '<style>' +
          '@page { size: A4; margin: 18mm; }' +
          'body { font-family: Arial, Helvetica, sans-serif; color: #222; font-size: 11pt; }' +
          'h1 { font-size: 16pt; margin: 0 0 .2rem 0; color: #7B2D40; }' +
          'h2 { font-size: 12pt; margin: 1.2rem 0 .3rem 0; padding-bottom: .15rem; border-bottom: 1.5px solid #7B2D40; color: #7B2D40; text-transform: uppercase; letter-spacing: .04em; }' +
          '.cabecera { display:flex; justify-content:space-between; align-items:flex-start; border-bottom: 2px solid #7B2D40; padding-bottom: .5rem; margin-bottom: 1rem; }' +
          '.cabecera small { color:#555; font-size:9pt; }' +
          'table { width:100%; border-collapse: collapse; margin-bottom:.5rem; }' +
          'th, td { padding: .25rem .5rem; vertical-align: top; font-size: 10.5pt; }' +
          'th { text-align:left; background:#f2f2f2; width: 32%; font-weight:600; }' +
          'td { border-bottom: 1px solid #ddd; }' +
          'img.foto-animal { max-width: 180px; max-height: 180px; border:1px solid #999; padding:2px; background:#fff; }' +
          '.firma { margin-top: 3rem; display:flex; justify-content:space-between; }' +
          '.firma div { width: 45%; border-top: 1px solid #555; padding-top: .3rem; font-size:9pt; text-align:center; color:#555; }' +
          '.no-print { margin-bottom:1rem; }' +
          '@media print { .no-print { display:none; } }' +
          '</style></head><body>' +
          '<div class="no-print" style="background:#f0f0f0;padding:.5rem .8rem;display:flex;gap:.6rem;">' +
          '<button onclick="window.print()" style="background:#7B2D40;color:#fff;border:none;padding:.4rem 1rem;font-weight:700;cursor:pointer;">Imprimir / Guardar PDF</button>' +
          '<button onclick="window.close()" style="background:none;border:1px solid #999;padding:.4rem 1rem;cursor:pointer;">Cerrar</button>' +
          '</div>' +
          '<div class="cabecera">' +
            '<div><h1>Censo Municipal de Animales</h1><small>Ayuntamiento de Navalcarnero</small></div>' +
            '<div style="text-align:right;font-size:9pt;color:#555;">Informe generado<br>' + hoy + '</div>' +
          '</div>' +
          htmlContenido +
          '<div class="firma"><div>Firma del agente / responsable</div><div>Sello / Fecha</div></div>' +
          '</body></html>'
        );
        w.document.close();
        // Lanzar el diálogo de impresión cuando cargue
        w.onload = function() { try { w.focus(); w.print(); } catch (e) {} };
      }
      function _filasInforme(pares) {
        return '<table>' + pares.map(function(p){
          return '<tr><th>' + p[0] + '</th><td>' + (p[1] === undefined || p[1] === null || p[1] === "" ? "—" : p[1]) + '</td></tr>';
        }).join("") + '</table>';
      }
      async function exportarFichaAnimalPDF(chip) {
        try {
          var json = await (await fetch(API + "/ficha_animal/" + encodeURIComponent(chip))).json();
          if (!json.ok) { alert("No se pudo cargar la ficha: " + (json.error || "")); return; }
          var a = json.animal || {};
          var p = json.propietario || null;
          var foto = a.FOTO ? '<div style="text-align:center;margin-bottom:.8rem;"><img src="' + a.FOTO + '" class="foto-animal" alt="Foto"></div>' : '';
          var datosAnim = _filasInforme([
            ["N.º chip", a["Nº_CHIP"] || a["N_CHIP"] || chip],
            ["N.º censo", a.N_CENSO || a["Nº_CENSO"] || ""],
            ["Nombre", a.NOMBRE],
            ["Especie", a.ESPECIE],
            ["Raza", a.RAZA],
            ["Sexo", a.SEXO],
            ["Color", a.COLOR],
            ["Año/Fecha nacimiento", a.FECHA_NACIMIENTO || a.AÑO_DE_NACIMIENTO || a.ANIO_NACIMIENTO],
            ["Esterilizado", String(a.ESTERILIZADO) === "1" ? "Sí" : "No"],
            ["Potencialmente peligroso", String(a.PELIGROSO) === "1" ? "Sí" : "No"],
            ["Última vacuna antirrábica", (a.FECHA_ULTIMA_VACUNA_ANTIRRABICA || a.FECHA_ULTIMA_VACUNACION_ANTIRRABICA || "").toString().substring(0,10)],
          ]);
          var datosProp = "";
          if (p) {
            var nomP = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO].filter(Boolean).join(" ");
            datosProp = _filasInforme([
              ["DNI / NIE", p.DNI],
              ["Nombre completo", nomP],
              ["Teléfono", [p.TELEFONO1, p.TELEFONO2].filter(Boolean).join(" / ")],
              ["Email", p.EMAIL],
              ["Domicilio", p.DOMICILIO],
              ["C.P. / Municipio", [p.CP, p.MINICIPIO].filter(Boolean).join(" ")],
            ]);
          } else {
            datosProp = '<p style="color:#777;font-style:italic;">Sin propietario registrado.</p>';
          }
          var seguros = "";
          if (json.seguros && json.seguros.length) {
            seguros = '<table><tr><th>Compañía</th><th>Póliza</th></tr>' +
              json.seguros.map(function(s){ return '<tr><td>' + (s.SEGURO_COMPANIA || "—") + '</td><td>' + (s.SEGURO_POLIZA || "—") + '</td></tr>'; }).join("") +
              '</table>';
          } else {
            seguros = '<p style="color:#777;font-style:italic;">Sin pólizas registradas.</p>';
          }
          var bajas = "";
          if (json.bajas && json.bajas.length) {
            bajas = '<h2>Historial de bajas</h2><table><tr><th>N.º</th><th>Fecha</th><th>Motivo</th></tr>' +
              json.bajas.map(function(b){
                return '<tr><td>' + (b.N_BAJA || "—") + '</td><td>' + ((b.FECHA_BAJA||"").toString().substring(0,10)) + '</td><td>' + (b.MOTIVO_DESC || b.MOTIVO || "—") + (b.OBSERVACIONES ? "<br><small>" + b.OBSERVACIONES + "</small>" : "") + '</td></tr>';
              }).join("") +
              '</table>';
          }
          var nombre = a.NOMBRE || "(sin nombre)";
          var contenido =
            '<h2>Datos del animal</h2>' + foto + datosAnim +
            '<h2>Propietario</h2>' + datosProp +
            '<h2>Seguros</h2>' + seguros +
            bajas;
          _abrirVentanaInforme("Informe de animal · " + nombre + " · " + chip, contenido);
        } catch (e) {
          logError(e?.message || "Error al exportar PDF", "exportarFichaAnimalPDF", e?.stack);
          alert("Error al generar el informe.");
        }
      }
      async function exportarFichaPropietarioPDF(dni) {
        try {
          var json = await (await fetch(API + "/ficha_propietario/" + encodeURIComponent(dni))).json();
          if (!json.ok) { alert("No se pudo cargar la ficha: " + (json.error || "")); return; }
          var p = json.propietario || {};
          var nom = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO].filter(Boolean).join(" ");
          var datosProp = _filasInforme([
            ["DNI / NIE", p.DNI],
            ["Nombre", p.NOMBRE],
            ["Primer apellido", p.PRIMER_APELLIDO],
            ["Segundo apellido", p.SEGUNDO_APELLIDO],
            ["Teléfono 1", p.TELEFONO1],
            ["Teléfono 2", p.TELEFONO2],
            ["Email", p.EMAIL],
          ]);
          var dirs = json.direcciones || [];
          var htmlDirs = dirs.length
            ? '<table><tr><th>Domicilio</th><th>C.P.</th><th>Municipio</th></tr>' +
              dirs.map(function(d){ return '<tr><td>' + (d.DOMICILIO||"—") + '</td><td>' + (d.CP||"—") + '</td><td>' + (d.MINICIPIO||"—") + '</td></tr>'; }).join("") +
              '</table>'
            : '<p style="color:#777;font-style:italic;">Sin domicilios registrados.</p>';
          var animales = json.animales || [];
          var htmlAnim = animales.length
            ? '<table><tr><th>Chip</th><th>Nombre</th><th>Especie</th><th>Raza</th><th>Estado</th></tr>' +
              animales.map(function(a){
                return '<tr><td>' + (a.N_CHIP||"—") + '</td><td>' + (a.NOMBRE||"—") + '</td><td>' + (a.ESPECIE||"—") + '</td><td>' + (a.RAZA||"—") + '</td><td>' + (a.DADO_DE_BAJA ? "Baja" : "Activo") + '</td></tr>';
              }).join("") +
              '</table>'
            : '<p style="color:#777;font-style:italic;">Sin animales registrados.</p>';
          var htmlSeg = (json.seguros && json.seguros.length)
            ? '<table><tr><th>Chip</th><th>Animal</th><th>Compañía</th><th>Póliza</th></tr>' +
              json.seguros.map(function(s){ return '<tr><td>' + (s.N_CHIP||"—") + '</td><td>' + (s.NOMBRE_ANIMAL||"—") + '</td><td>' + (s.SEGURO_COMPANIA||"—") + '</td><td>' + (s.SEGURO_POLIZA||"—") + '</td></tr>'; }).join("") +
              '</table>'
            : '<p style="color:#777;font-style:italic;">Sin pólizas registradas.</p>';
          var contenido =
            '<h2>Datos del propietario</h2>' + datosProp +
            '<h2>Domicilios (' + dirs.length + ')</h2>' + htmlDirs +
            '<h2>Animales (' + animales.length + ')</h2>' + htmlAnim +
            '<h2>Seguros</h2>' + htmlSeg;
          _abrirVentanaInforme("Informe de propietario · " + (nom || dni), contenido);
        } catch (e) {
          logError(e?.message || "Error al exportar PDF propietario", "exportarFichaPropietarioPDF", e?.stack);
          alert("Error al generar el informe.");
        }
      }
