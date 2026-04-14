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
