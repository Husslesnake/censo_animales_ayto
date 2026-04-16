      const estado = {
        prop: { datos: [], pagina: 1 },
        anim: { datos: [], pagina: 1 },
      };

      function toggleNav() {
        const btn = document.getElementById("nav-hamburger");
        const nav = document.getElementById("header-nav");
        const ovl = document.getElementById("nav-overlay");
        const open = btn.classList.toggle("open");
        btn.setAttribute("aria-expanded", open);
        nav.classList.toggle("open", open);
        ovl.classList.toggle("open", open);
      }
      function cerrarNav() {
        document.getElementById("nav-hamburger").classList.remove("open");
        document.getElementById("header-nav").classList.remove("open");
        document.getElementById("nav-overlay").classList.remove("open");
      }
      function mostrarPagina(id, btn) {
        cerrarNav();
        document
          .querySelectorAll(".page")
          .forEach((p) => p.classList.remove("active"));
        document
          .querySelectorAll(".tab-btn")
          .forEach((b) => b.classList.remove("active"));
        document.getElementById("page-" + id).classList.add("active");
        btn.classList.add("active");
      }
      function resetForm(formId, alertId) {
        document.getElementById(formId).reset();
        document.getElementById(alertId).classList.remove("show");
        // Limpiar domicilios dinámicos extra (dejar solo el primero)
        const cont = document.getElementById("domicilios-container");
        if (cont) {
          const rows = cont.querySelectorAll(".domicilio-row");
          rows.forEach((r, i) => { if (i > 0) r.remove(); });
        }
      }
      function filasProp(datos) {
        return datos
          .map(
            (r) => `
 <tr style="cursor:pointer;" title="Ver ficha del propietario" data-dni="${r.DNI || ""}" onclick="abrirFichaProp(this.dataset.dni)"> <td data-label="DNI"><span class="tag tag-id">${r.DNI || "—"}</span></td> <td data-label="Nombre">${r.NOMBRE || "—"}</td> <td data-label="1.º Apellido">${r.PRIMER_APELLIDO || "—"}</td> <td data-label="2.º Apellido">${r.SEGUNDO_APELLIDO || "—"}</td> <td data-label="Teléfono">${r.TELEFONO1 || "—"}</td> <td data-label="Municipio">${r.MINICIPIO || r.MUNICIPIO || "—"}</td> </tr>`,
          )
          .join("");
      }
      function filasAnim(datos) {
        return datos
          .map((r) => {
            const chip = r["N_CHIP"] || r["Nº_CHIP"] || "—";
            const pelig =
              r.PELIGROSO == 1
                ? '<span class="tag tag-peligroso">Peligroso</span>'
                : '<span class="tag tag-sano">No</span>';
            return `
 <tr style="cursor:pointer;" title="Ver ficha completa" data-chip="${chip}" onclick="abrirFicha(this.dataset.chip)"> <td data-label="Chip"><span class="tag tag-id">${chip}</span></td> <td data-label="Nombre">${r.NOMBRE || "—"}</td> <td data-label="Especie">${r.ESPECIE || "—"}</td> <td data-label="Raza">${r.RAZA || "—"}</td> <td data-label="Sexo">${r.SEXO || "—"}</td> <td data-label="DNI propietario">${r.DNI_PROPIETARIO || "—"}</td> <td data-label="Peligroso">${pelig}</td> </tr>`;
          })
          .join("");
      }
      function renderPagina(tipo, pagina) {
        const e = estado[tipo];
        const total = e.datos.length;
        const npags = Math.ceil(total / POR_PAGINA);
        pagina = Math.max(1, Math.min(pagina, npags));
        e.pagina = pagina;
        const inicio = (pagina - 1) * POR_PAGINA;
        const trozo = e.datos.slice(inicio, inicio + POR_PAGINA);
        const tbody = document.getElementById("tbody-" + tipo);
        const ncols = tipo === "prop" ? 6 : tipo === "seg" ? 8 : 7;
        tbody.innerHTML = trozo.length
          ? tipo === "prop"
            ? filasProp(trozo)
            : tipo === "seg"
              ? filasSeguro(trozo)
              : filasAnim(trozo)
          : `<tr class="empty-row"><td colspan="${ncols}">Sin resultados.</td></tr>`;
        const contenedor = document.getElementById("pag-" + tipo);
        if (!contenedor) return;
        if (npags <= 1) {
          contenedor.innerHTML = "";
          return;
        }
        let html = `<button onclick="renderPagina('${tipo}',${pagina - 1})" ${pagina === 1 ? "disabled" : ""}>‹</button>`;
        const ventana = [];
        if (npags <= 7) {
          for (let i = 1; i <= npags; i++) ventana.push(i);
        } else {
          ventana.push(1);
          if (pagina > 3) ventana.push("…");
          for (
            let i = Math.max(2, pagina - 1);
            i <= Math.min(npags - 1, pagina + 1);
            i++
          )
            ventana.push(i);
          if (pagina < npags - 2) ventana.push("…");
          ventana.push(npags);
        }
        ventana.forEach((p) => {
          if (p === "…") {
            html += `<button disabled>…</button>`;
          } else {
            html += `<button class="${p === pagina ? "activa" : ""}" onclick="renderPagina('${tipo}',${p})">${p}</button>`;
          }
        });
        html += `<button onclick="renderPagina('${tipo}',${pagina + 1})" ${pagina === npags ? "disabled" : ""}>›</button>`;
        html += `<span class="pag-info">pág. ${pagina} / ${npags} · ${total} registros</span>`;
        contenedor.innerHTML = html;
      }
      function setDatos(tipo, datos, label) {
        if (!estado[tipo]) estado[tipo] = { datos: [], pagina: 1 };
        estado[tipo].datos = datos;
        estado[tipo].pagina = 1;
        renderPagina(tipo, 1);
        setContador(tipo + "-contador", datos.length, label);
      }
      function setContador(id, n, label) {
        const el = document.getElementById(id);
        if (el)
          el.textContent =
            n !== null ? `${n} registro${n !== 1 ? "s" : ""} ${label}` : "";
        const tipo = id.replace("-contador", "");
        const btn = document.getElementById("btn-ocultar-" + tipo);
        if (btn) btn.style.display = n !== null && n > 0 ? "inline" : "none";
        const wrap = document.getElementById("tabla-wrap-" + tipo);
        if (wrap && n !== null && n > 0) {
          wrap.classList.remove("oculta");
          if (btn) btn.textContent = "▲ Ocultar registros";
        }
      }
      function ocultarTabla(tipo) {
        const wrap = document.getElementById("tabla-wrap-" + tipo);
        const btn = document.getElementById("btn-ocultar-" + tipo);
        const oculta = wrap.classList.toggle("oculta");
        btn.textContent = oculta
          ? "▼ Mostrar registros"
          : "▲ Ocultar registros";
      }
      function mostrarTabla(tipo) {
        const wrap = document.getElementById("tabla-wrap-" + tipo);
        if (wrap) {
          wrap.classList.remove("oculta");
        }
      }
      function irA(id) {
        var btn = document.querySelector(".tab-btn[onclick*='" + id + "']]");
        if (!btn)
          btn = document.querySelector('.tab-btn[onclick*="' + id + '"]');
        if (btn) mostrarPagina(id, btn);
      }
      async function cargarSexos() {
        const sel = document.getElementById("sel-sexo");
        try {
          const json = await (await fetch(API + "/sexos")).json();
          if (!json.ok || !json.datos.length) throw new Error();
          sel.innerHTML =
            '<option value="">— Seleccionar —</option>' +
            json.datos
              .map((r) => {
                const valor = r.SEXO || r.CLAVE || "";
                return `<option value="${valor}">${valor}</option>`;
              })
              .join("");
        } catch (e) {
          logError(
            e?.message || "Error al cargar sexos",
            "cargarSexos",
            e?.stack,
          );
          sel.innerHTML = `
 <option value="">— Seleccionar —</option> <option value="Macho">Macho</option> <option value="Hembra">Hembra</option>`;
        }
      }
      function toggleDarkMode() {
        const dark = document.body.classList.toggle("dark-mode");
        localStorage.setItem("censo_dark", dark ? "1" : "0");
        document.getElementById("btn-dark-mode").title = dark
          ? "Tema claro"
          : "Tema oscuro";
      }
      (function _initDark() {
        if (localStorage.getItem("censo_dark") === "1") {
          document.body.classList.add("dark-mode");
          const btn = document.getElementById("btn-dark-mode");
          if (btn) btn.title = "Tema claro";
        }
      })();
      estado.seg = { datos: [], pagina: 1 };
      (function () {
        const hoy = new Date().toISOString().split("T")[0];
        ["inp-fecha-nac", "inp-fecha-vac"].forEach((id) => {
          const el = document.getElementById(id);
          if (el) el.max = hoy;
        });
      })();
      (function () {
        const params = new URLSearchParams(window.location.search);
        const tab = params.get("tab");
        if (tab) {
          const btn = document.querySelector(`.tab-btn[onclick*="'${tab}'"]`);
          if (btn) btn.click();
        }
      })();
