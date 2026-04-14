      let _busqTimer = null;

      function busquedaGlobalInput(val) {
        clearTimeout(_busqTimer);
        const drop = document.getElementById("busq-global-dropdown");
        if (val.trim().length < 2) {
          drop.style.display = "none";
          return;
        }
        _busqTimer = setTimeout(() => _ejecutarBusqGlobal(val.trim()), 300);
      }

      async function _ejecutarBusqGlobal(q) {
        const drop = document.getElementById("busq-global-dropdown");
        drop.innerHTML =
          '<div style="padding:.75rem 1rem;font-size:.82rem;color:var(--gris3);">Buscando…</div>';
        drop.style.display = "block";
        try {
          const json = await (
            await fetch(API + "/busqueda_global?q=" + encodeURIComponent(q))
          ).json();
          if (!json.ok) {
            drop.innerHTML =
              '<div style="padding:.75rem 1rem;color:var(--rojo);font-size:.82rem;">Error al buscar.</div>';
            return;
          }
          let html = "";
          if (json.propietarios.length) {
            html +=
              '<div style="padding:.4rem .85rem;font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--gris3);background:var(--gris0);border-bottom:1px solid var(--borde2);">Propietarios</div>';
            html += json.propietarios
              .map((p) => {
                const nom = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO]
                  .filter(Boolean)
                  .join(" ");
                return `<div class="_drop-item" onclick="_selBusqProp('${p.DNI}')" style="padding:.55rem .85rem;cursor:pointer;border-bottom:1px solid var(--borde2);font-size:.82rem;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:.75rem;color:var(--gris3);">${p.DNI}</span>
          <span style="margin-left:.5rem;">${nom || "—"}</span>
          ${p.TELEFONO1 ? `<span style="margin-left:.5rem;font-size:.75rem;color:var(--gris3);">${p.TELEFONO1}</span>` : ""}
        </div>`;
              })
              .join("");
          }
          if (json.animales.length) {
            html +=
              '<div style="padding:.4rem .85rem;font-size:.65rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--gris3);background:var(--gris0);border-bottom:1px solid var(--borde2);">Animales</div>';
            html += json.animales
              .map((a) => {
                const prop = [
                  a.NOMBRE_PROP,
                  a.PRIMER_APELLIDO,
                  a.SEGUNDO_APELLIDO,
                ]
                  .filter(Boolean)
                  .join(" ");
                return `<div class="_drop-item" onclick="abrirFicha('${(a.N_CHIP || "").replace(/'/g, "\\'")}'); _cerrarBusqGlobal();" style="padding:.55rem .85rem;cursor:pointer;border-bottom:1px solid var(--borde2);font-size:.82rem;">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:.75rem;color:var(--gris3);">${a.N_CHIP || "—"}</span>
          <span style="margin-left:.5rem;font-weight:600;">${a.NOMBRE || "(sin nombre)"}</span>
          <span style="margin-left:.35rem;font-size:.78rem;color:var(--gris4);">${a.ESPECIE || ""}</span>
          ${prop ? `<span style="margin-left:.5rem;font-size:.75rem;color:var(--gris3);">· ${prop}</span>` : ""}
        </div>`;
              })
              .join("");
          }
          if (!json.propietarios.length && !json.animales.length)
            html =
              '<div style="padding:.75rem 1rem;font-size:.82rem;color:var(--gris3);">Sin resultados.</div>';
          drop.innerHTML = html;
          drop.style.display = "block";
          drop.querySelectorAll("._drop-item").forEach((el) => {
            el.addEventListener(
              "mouseover",
              () => (el.style.background = "var(--gris0)"),
            );
            el.addEventListener("mouseout", () => (el.style.background = ""));
          });
        } catch (e) {
          logError(
            e?.message || "Error búsqueda global",
            "_ejecutarBusqGlobal",
            e?.stack,
          );
          drop.innerHTML =
            '<div style="padding:.75rem 1rem;color:var(--rojo);font-size:.82rem;">No se pudo conectar.</div>';
        }
      }

      function _selBusqProp(dni) {
        _cerrarBusqGlobal();
        const input = document.getElementById("busq-prop-dni");
        if (input) {
          input.value = dni;
        }
        const btn = document.querySelector(".tab-btn[onclick*=\"'consulta'\"]");
        if (btn) mostrarPagina("consulta", btn);
        setTimeout(() => buscarPropietario(), 100);
      }

      function _cerrarBusqGlobal() {
        const inp = document.getElementById("busq-global-input");
        const drop = document.getElementById("busq-global-dropdown");
        if (inp) inp.value = "";
        if (drop) drop.style.display = "none";
      }

      document.addEventListener("click", (e) => {
        if (!document.getElementById("busq-global-wrap")?.contains(e.target))
          _cerrarBusqGlobal();
      });

      document
        .getElementById("busq-global-input")
        ?.addEventListener("keydown", (e) => {
          if (e.key === "Escape") _cerrarBusqGlobal();
        });
