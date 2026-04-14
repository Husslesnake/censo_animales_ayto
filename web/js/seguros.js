      function filasSeguro(datos) {
        return datos
          .map(
            (r) => `
 <tr style="cursor:pointer;" title="Ver ficha del animal" data-chip="${r.N_CHIP || ""}" onclick="abrirFicha(this.dataset.chip)"> <td data-label="ID"><span class="tag tag-id">${r.ID_SEGUROS || "—"}</span></td> <td data-label="Chip"><span class="tag tag-id">${r.N_CHIP || "—"}</span></td> <td data-label="Animal">${r.NOMBRE_ANIMAL || "—"}</td> <td data-label="Especie">${r.ESPECIE || "—"}</td> <td data-label="Compañía">${r.SEGURO_COMPANIA || "—"}</td> <td data-label="Póliza">${r.SEGURO_POLIZA || "—"}</td> <td data-label="DNI">${r.DNI_PROPIETARIO || "—"}</td> <td data-label="Acción"><button class="btn btn-secondary" style="padding:.25rem .6rem;font-size:.7rem;" onclick="event.stopPropagation();eliminarSeguro(${r.ID_SEGUROS})">Eliminar</button></td> </tr>`,
          )
          .join("");
      }
      async function submitSeguro(e) {
        e.preventDefault();
        const btn = document.getElementById("btn-seg");
        const sp = document.getElementById("sp-seg");
        btn.disabled = true;
        sp.style.display = "block";
        const data = Object.fromEntries(new FormData(e.target).entries());
        Object.keys(data).forEach((k) => {
          if (!data[k]) delete data[k];
        });
        try {
          const res = await fetch(API + "/seguros", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
          });
          const json = await res.json();
          if (json.ok) {
            mostrarAlerta("alert-seg", "ok", json.mensaje);
            e.target.reset();
            cargarSeguros();
          } else {
            mostrarAlerta("alert-seg", "error", json.error);
          }
        } catch (e) {
          logError(
            e?.message || "Error al enviar seguro",
            "submitSeguro",
            e?.stack,
          );
          mostrarAlerta(
            "alert-seg",
            "error",
            "No se pudo conectar con el servidor.",
          );
        } finally {
          btn.disabled = false;
          sp.style.display = "none";
        }
      }
      async function cargarSeguros() {
        const tbody = document.getElementById("tbody-seg");
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="8">Cargando…</td></tr>';
        setContador("seg-contador", null);
        try {
          const json = await (await fetch(API + "/seguros")).json();
          if (!json.ok) throw new Error(json.error);
          if (!json.datos.length) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="8">Sin pólizas registradas.</td></tr>';
            return;
          }
          setDatos("seg", json.datos, "encontradas");
        } catch (err) {
          logError(
            err?.message || "Error al cargar seguros",
            "cargarSeguros",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="8">Error: ${err.message}</td></tr>`;
        }
      }
      async function buscarSegurosPorChip() {
        const chip = document
          .getElementById("busq-seg-chip")
          .value.trim()
          .toUpperCase();
        const tbody = document.getElementById("tbody-seg");
        if (!chip) {
          mostrarAlerta(
            "alert-seg",
            "error",
            "Introduzca un chip para buscar.",
          );
          return;
        }
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="8">Buscando…</td></tr>';
        setContador("seg-contador", null);
        try {
          const json = await (await fetch(API + "/seguros")).json();
          if (!json.ok) throw new Error(json.error);
          const filtrados = json.datos.filter(
            (r) => (r.N_CHIP || "").toUpperCase() === chip,
          );
          if (!filtrados.length) {
            tbody.innerHTML =
              '<tr class="empty-row"><td colspan="8">No se encontraron pólizas para ese chip.</td></tr>';
            mostrarAlerta(
              "alert-seg",
              "error",
              `No hay pólizas para el chip «${chip}».`,
            );
            return;
          }
          setDatos("seg", filtrados, "encontradas");
        } catch (err) {
          logError(
            err?.message || "Error al buscar seguros por chip",
            "buscarSegurosPorChip",
            err?.stack,
          );
          tbody.innerHTML = `<tr class="empty-row"><td colspan="8">Error: ${err.message}</td></tr>`;
        }
      }
      async function eliminarSeguro(id) {
        if (!confirm(`¿Eliminar la póliza con ID ${id}?`)) return;
        try {
          const json = await (
            await fetch(API + "/seguros/" + id, { method: "DELETE" })
          ).json();
          if (json.ok) {
            mostrarAlerta("alert-seg", "ok", json.mensaje);
            cargarSeguros();
          } else {
            mostrarAlerta("alert-seg", "error", json.error);
          }
        } catch (e) {
          logError(
            e?.message || "Error al eliminar seguro",
            "eliminarSeguro",
            e?.stack,
          );
          mostrarAlerta(
            "alert-seg",
            "error",
            "No se pudo conectar con el servidor.",
          );
        }
      }
