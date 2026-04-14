      const PALETA = [
        "#7B2D40",
        "#C8922A",
        "#1A4A8A",
        "#1E6B3C",
        "#C05820",
        "#6B3FA0",
        "#2E8B8B",
        "#8B2E6E",
        "#4A7A1A",
        "#8B6E2E",
      ];
      const PALETA2 = [
        "#9E3D53",
        "#E8B84B",
        "#2E6CB5",
        "#2E8B57",
        "#E07040",
        "#8B5FD0",
      ];
      let _statsCharts = {};
      let _statsLoaded = false;

      function _destroyChart(id) {
        if (_statsCharts[id]) {
          _statsCharts[id].destroy();
          delete _statsCharts[id];
        }
      }

      function _mkDonut(id, labels, values, colors) {
        _destroyChart(id);
        const ctx = document.getElementById(id);
        if (!ctx) return;
        _statsCharts[id] = new Chart(ctx, {
          type: "doughnut",
          data: {
            labels,
            datasets: [
              {
                data: values,
                backgroundColor: colors || PALETA,
                borderWidth: 2,
                borderColor: "#fff",
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "right",
                labels: { font: { size: 12 }, boxWidth: 14, padding: 10 },
              },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                    return ` ${ctx.label}: ${ctx.parsed} (${((ctx.parsed / total) * 100).toFixed(1)}%)`;
                  },
                },
              },
            },
          },
        });
      }

      function _mkEvolucion(altas, bajas) {
        _destroyChart("chart-evolucion");
        const ctx = document.getElementById("chart-evolucion");
        if (!ctx) return;

        const years = [...new Set([...altas.labels, ...bajas.labels])].sort();
        const altasMap = Object.fromEntries(
          altas.labels.map((l, i) => [l, altas.values[i]]),
        );
        const bajasMap = Object.fromEntries(
          bajas.labels.map((l, i) => [l, bajas.values[i]]),
        );
        _statsCharts["chart-evolucion"] = new Chart(ctx, {
          type: "bar",
          data: {
            labels: years,
            datasets: [
              {
                label: "Altas",
                data: years.map((y) => altasMap[y] || 0),
                backgroundColor: "rgba(200,146,42,0.75)",
                borderColor: "#A8761E",
                borderWidth: 1,
                borderRadius: 3,
              },
              {
                label: "Bajas",
                data: years.map((y) => bajasMap[y] || 0),
                backgroundColor: "rgba(123,45,64,0.75)",
                borderColor: "#5C1B2E",
                borderWidth: 1,
                borderRadius: 3,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: "top",
                labels: { font: { size: 12 }, boxWidth: 14 },
              },
              tooltip: {
                callbacks: {
                  label: (c) => ` ${c.dataset.label}: ${c.parsed.y}`,
                },
              },
            },
            scales: {
              x: {
                grid: { color: "rgba(0,0,0,.06)" },
                ticks: { font: { size: 11 } },
              },
              y: {
                grid: { color: "rgba(0,0,0,.06)" },
                ticks: { font: { size: 11 } },
                beginAtZero: true,
              },
            },
          },
        });
      }
      function _mkBar(id, labels, values, label, color, horizontal) {
        _destroyChart(id);
        const ctx = document.getElementById(id);
        if (!ctx) return;
        _statsCharts[id] = new Chart(ctx, {
          type: horizontal ? "bar" : "bar",
          data: {
            labels,
            datasets: [
              {
                label,
                data: values,
                backgroundColor: color || "rgba(123,45,64,0.75)",
                borderColor: color ? color.replace("0.75", "1") : "#5C1B2E",
                borderWidth: 1,
                borderRadius: 3,
              },
            ],
          },
          options: {
            indexAxis: horizontal ? "y" : "x",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (c) => ` ${c.parsed[horizontal ? "x" : "y"]} animales`,
                },
              },
            },
            scales: {
              x: {
                grid: { color: "rgba(0,0,0,.06)" },
                ticks: { font: { size: 11 } },
              },
              y: {
                grid: { color: "rgba(0,0,0,.06)" },
                ticks: { font: { size: 11 } },
                beginAtZero: true,
              },
            },
          },
        });
      }

      async function cargarEstadisticas() {
        if (_statsLoaded) return;
        const loading = document.getElementById("stats-loading");
        const grid = document.getElementById("stats-grid");
        loading.style.display = "block";
        grid.style.opacity = "0.3";
        try {
          const json = await (await fetch(API + "/estadisticas")).json();
          if (!json.ok) {
            mostrarAlerta(
              "alert-estadisticas",
              "error",
              json.error || "Error al cargar datos.",
            );
            return;
          }

          const d = json;
          const tot = document.getElementById("stat-total");
          if (tot)
            tot.textContent =
              d.total_registrados +
              " registrados · " +
              d.total_activos +
              " activos";

          _mkDonut("chart-especies", d.especies.labels, d.especies.values);
          _mkDonut("chart-sexos", d.sexos.labels, d.sexos.values, PALETA2);

          _mkDonut(
            "chart-peligrosos",
            d.peligrosos.labels,
            d.peligrosos.values,
            ["#7B2D40", "#1E6B3C"],
          );
          _mkDonut(
            "chart-esterilizados",
            d.esterilizados.labels,
            d.esterilizados.values,
            ["#1A4A8A", "#C8922A"],
          );

          _mkDonut(
            "chart-anim-prop",
            d.anim_por_prop.labels,
            d.anim_por_prop.values,
            [
              "#1A4A8A",
              "#C8922A",
              "#7B2D40",
              "#1E6B3C",
              "#C05820",
              "#6B3FA0",
              "#2E8B8B",
            ],
          );

          _mkBar(
            "chart-nacimientos",
            d.nacimientos.labels,
            d.nacimientos.values,
            "Animales",
            "rgba(26,74,138,0.75)",
          );

          _mkEvolucion(d.altas_por_anio, d.bajas_por_anio);

          _mkBar(
            "chart-motivos",
            d.motivos_baja.labels,
            d.motivos_baja.values,
            "Registros",
            "rgba(192,88,32,0.75)",
            true,
          );

          _statsLoaded = true;
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          mostrarAlerta(
            "alert-estadisticas",
            "error",
            "Error: " + (err.message || "No se pudo conectar."),
          );
        } finally {
          loading.style.display = "none";
          grid.style.opacity = "1";
        }
      }

      let _statsRaw = null;
      let _statsFilterTimer = null;

      const _cargarEstadisticasOrig = cargarEstadisticas;
      cargarEstadisticas = async function () {
        _statsLoaded = false;
        await _cargarEstadisticasOrig();
      };

      async function _fetchStatsRaw() {
        try {
          const json = await (await fetch(API + "/estadisticas")).json();
          if (!json.ok) return null;
          _statsRaw = json;

          const sel = document.getElementById("filtro-especie");
          if (sel && json.especies) {
            const cur = sel.value;
            sel.innerHTML = '<option value="">— Todas —</option>';
            json.especies.labels.forEach((l, i) => {
              const opt = document.createElement("option");
              opt.value = l;
              opt.textContent = `${l} (${json.especies.values[i]})`;
              sel.appendChild(opt);
            });
            if (cur) sel.value = cur;
          }
          return json;
        } catch (e) {
          logError(
            e?.message || "Error cargando estadísticas",
            "_fetchStatsRaw",
            e?.stack,
          );
          return null;
        }
      }

      function aplicarFiltrosStats() {
        clearTimeout(_statsFilterTimer);
        _statsFilterTimer = setTimeout(_aplicarFiltrosStatsNow, 300);
      }

      async function _aplicarFiltrosStatsNow() {
        const especie = document.getElementById("filtro-especie")?.value || "";
        const anioDesde =
          document.getElementById("filtro-anio-desde")?.value || "";
        const anioHasta =
          document.getElementById("filtro-anio-hasta")?.value || "";

        const noFilters = !especie && !anioDesde && !anioHasta;
        let data;

        if (noFilters && _statsRaw) {
          data = _statsRaw;
        } else {
          if (!_statsRaw) await _fetchStatsRaw();
          const params = new URLSearchParams();
          if (especie) params.set("especie", especie);
          if (anioDesde) params.set("anio_desde", anioDesde);
          if (anioHasta) params.set("anio_hasta", anioHasta);

          const loading = document.getElementById("stats-loading");
          const grid = document.getElementById("stats-grid");
          if (loading) loading.style.display = "block";
          if (grid) grid.style.opacity = "0.3";
          try {
            const json = await (
              await fetch(`${API}/estadisticas?${params}`)
            ).json();
            if (!json.ok) {
              mostrarAlerta(
                "alert-estadisticas",
                "error",
                json.error || "Error al filtrar datos.",
              );
              return;
            }
            data = json;
          } catch (e) {
            logError(
              e?.message || "Error filtrando estadísticas",
              "_aplicarFiltrosStatsNow",
              e?.stack,
            );
            return;
          } finally {
            if (loading) loading.style.display = "none";
            if (grid) grid.style.opacity = "1";
          }
        }

        const tot = document.getElementById("stat-total");
        if (tot) {
          const lbl = especie ? ` (${especie})` : "";
          tot.textContent = `${data.total_registrados} registrados · ${data.total_activos} activos${lbl}`;
        }

        _mkDonut("chart-especies", data.especies.labels, data.especies.values);
        _mkDonut(
          "chart-sexos",
          data.sexos.labels,
          data.sexos.values,
          PALETA2,
        );
        _mkDonut(
          "chart-peligrosos",
          data.peligrosos.labels,
          data.peligrosos.values,
          ["#7B2D40", "#1E6B3C"],
        );
        _mkDonut(
          "chart-esterilizados",
          data.esterilizados.labels,
          data.esterilizados.values,
          ["#1A4A8A", "#C8922A"],
        );
        _mkDonut(
          "chart-anim-prop",
          data.anim_por_prop.labels,
          data.anim_por_prop.values,
          [
            "#1A4A8A",
            "#C8922A",
            "#7B2D40",
            "#1E6B3C",
            "#C05820",
            "#6B3FA0",
            "#2E8B8B",
          ],
        );
        _mkBar(
          "chart-nacimientos",
          data.nacimientos.labels,
          data.nacimientos.values,
          "Animales",
          "rgba(26,74,138,0.75)",
        );
        _mkEvolucion(data.altas_por_anio, data.bajas_por_anio);
        _mkBar(
          "chart-motivos",
          data.motivos_baja.labels,
          data.motivos_baja.values,
          "Registros",
          "rgba(192,88,32,0.75)",
          true,
        );
      }

      function resetFiltrosStats() {
        const se = document.getElementById("filtro-especie");
        const sd = document.getElementById("filtro-anio-desde");
        const sh = document.getElementById("filtro-anio-hasta");
        if (se) se.value = "";
        if (sd) sd.value = "";
        if (sh) sh.value = "";
        if (_statsRaw) aplicarFiltrosStats();
      }

      function generarInformeStats() {
        const hoy = new Date().toLocaleDateString("es-ES", {
          day: "2-digit",
          month: "long",
          year: "numeric",
        });

        const chartIds = [
          "chart-especies",
          "chart-sexos",
          "chart-peligrosos",
          "chart-esterilizados",
          "chart-anim-prop",
          "chart-nacimientos",
          "chart-evolucion",
          "chart-motivos",
        ];
        const titles = [
          "Distribución por especie",
          "Distribución por sexo",
          "Peligrosidad",
          "Esterilización",
          "Animales por propietario",
          "Año de nacimiento",
          "Evolución altas/bajas",
          "Motivos de baja",
        ];
        const wideIds = ["chart-nacimientos", "chart-evolucion", "chart-motivos"];

        let gridHtml = "";
        chartIds.forEach((id, i) => {
          const canvas = document.getElementById(id);
          if (!canvas) return;
          const isWide = wideIds.includes(id);
          const dataUrl = canvas.toDataURL("image/png");
          gridHtml += `
            <div style="${isWide ? "grid-column:span 2;" : ""}margin-bottom:.5cm;">
              <div style="font-size:9pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;
                color:#1A4A8A;border-bottom:1px solid #1A4A8A;padding-bottom:.15cm;margin-bottom:.25cm;">
                ${titles[i]}
              </div>
              <img src="${dataUrl}" style="width:100%;max-height:${isWide ? "180px" : "200px"};">
            </div>`;
        });

        const win = window.open("", "_blank");
        win.document.write(`<!DOCTYPE html><html><head><meta charset="utf-8">
          <title>Estadísticas · Censo Municipal de Animales</title>
          <style>
            body { margin: 1.5cm 2cm; font-family: sans-serif; font-size: 11pt; color: #000; }
            @media print { body { margin: 1.5cm 2cm; } }
          </style>
        </head><body>
          <div style="display:flex;justify-content:space-between;margin-bottom:1cm;
            border-bottom:2px solid #7B2D40;padding-bottom:.5cm;">
            <div>
              <div style="font-size:14pt;font-weight:700;color:#7B2D40;">Ayuntamiento de Navalcarnero</div>
              <div style="font-size:9pt;color:#555;">Censo Municipal de Animales · Estadísticas</div>
            </div>
            <div style="text-align:right;font-size:9pt;color:#555;">Generado: ${hoy}</div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:1cm;">
            ${gridHtml}
          </div>
          <script>window.onload = function(){ window.print(); };<\/script>
        </body></html>`);
        win.document.close();
      }

      function cerrarStats() {
        document.getElementById("stats-print-wrap").style.display = "none";
        document.body.style.overflow = "";
      }

      const _mostrarPaginaStats = mostrarPagina;
      mostrarPagina = function (id, btn) {
        _mostrarPaginaStats(id, btn);
        if (id === "estadisticas" && !_statsRaw) {
          setTimeout(_fetchStatsRaw, 800);
        }
      };

      const estadoVacCad = { datos: [], pagina: 1 };

      async function cargarVacunasCaducadas() {
        const tbody = document.getElementById("tbody-vacunas-cad");
        const cont = document.getElementById("vacunas-contador");
        tbody.innerHTML =
          '<tr class="empty-row"><td colspan="7">Cargando…</td></tr>';
        if (cont) cont.textContent = "";
        try {

          const json = await (await fetch(API + "/alertas")).json();
          if (!json.ok) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Error: ${json.error}</td></tr>`;
            return;
          }
          estadoVacCad.datos = json.vacunas_caducadas;
          estadoVacCad.pagina = 1;
          _renderVacCad();
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          tbody.innerHTML = `<tr class="empty-row"><td colspan="7">Error: ${err.message || "No se pudo conectar."}</td></tr>`;
        }
      }

      function _renderVacCad() {
        const tbody = document.getElementById("tbody-vacunas-cad");
        const cont = document.getElementById("vacunas-contador");
        const pagDiv = document.getElementById("pag-vacunas-cad");
        const datos = estadoVacCad.datos;

        if (cont)
          cont.textContent = datos.length
            ? datos.length +
              " animal" +
              (datos.length > 1 ? "es" : "") +
              " con vacuna caducada"
            : "Sin resultados";

        if (!datos.length) {
          tbody.innerHTML =
            '<tr class="empty-row"><td colspan="7">No hay animales activos con vacuna caducada.</td></tr>';
          if (pagDiv) pagDiv.innerHTML = "";
          return;
        }

        const ini = (estadoVacCad.pagina - 1) * POR_PAGINA;
        const page = datos.slice(ini, ini + POR_PAGINA);

        tbody.innerHTML = page
          .map((r) => {
            const prop =
              [r.NOMBRE_PROP, r.PRIMER_APELLIDO, r.SEGUNDO_APELLIDO]
                .filter(Boolean)
                .join(" ") || "—";
            const fvac = r.FECHA_VACUNA ? r.FECHA_VACUNA.substring(0, 10) : "—";
            const chip = r.N_CHIP || "—";
            const rec = {
              N_CHIP: chip,
              NOMBRE: r.NOMBRE,
              ESPECIE: r.ESPECIE,
              NOMBRE_PROP: r.NOMBRE_PROP,
              PRIMER_APELLIDO: r.PRIMER_APELLIDO,
              SEGUNDO_APELLIDO: r.SEGUNDO_APELLIDO,
              TELEFONO1: r.TELEFONO1,
              DOMICILIO: r.DOMICILIO,
              CP: r.CP,
              MINICIPIO: r.MINICIPIO,
              FECHA_VACUNA: r.FECHA_VACUNA,
              VENCE: r.FECHA_VACUNA
                ? (() => {
                    try {
                      const d = new Date(r.FECHA_VACUNA);
                      d.setFullYear(d.getFullYear() + 1);
                      return d.toISOString().substring(0, 10);
                    } catch {
                      return null;
                    }
                  })()
                : null,
              DIAS_RESTANTES: r.FECHA_VACUNA
                ? (() => {
                    try {
                      const d = new Date(r.FECHA_VACUNA);
                      d.setFullYear(d.getFullYear() + 1);
                      return Math.floor(
                        (d - new Date()) / (1000 * 60 * 60 * 24),
                      );
                    } catch {
                      return null;
                    }
                  })()
                : null,
            };
            return `<tr style="cursor:pointer;" data-chip="${chip}" onclick="abrirFicha(this.dataset.chip)">
      <td data-label="Chip"><span class="tag tag-id">${chip}</span></td>
      <td data-label="Animal">${r.NOMBRE || "(sin nombre)"}</td>
      <td data-label="Especie">${r.ESPECIE || "—"}</td>
      <td data-label="Propietario">${prop}</td>
      <td data-label="Teléfono" style="font-family:'IBM Plex Mono',monospace;">${r.TELEFONO1 || "—"}</td>
      <td data-label="Última vacuna" style="font-family:'IBM Plex Mono',monospace;color:var(--rojo);font-weight:600;">${fvac}</td>
      <td data-label="Carta">
        <button class="btn btn-primary" style="padding:.25rem .6rem;font-size:.7rem;"
          onclick="event.stopPropagation();generarCarta(${JSON.stringify(rec).replace(/"/g, "&quot;").replace(/'/g, "&#39;")})">
          Carta
        </button>
      </td>
    </tr>`;
          })
          .join("");

        const totalPags = Math.ceil(datos.length / POR_PAGINA);
        let html = "";
        if (estadoVacCad.pagina > 1)
          html += `<button class="pag-btn" onclick="irPagVacCad(${estadoVacCad.pagina - 1})">‹ Anterior</button>`;
        if (totalPags > 1)
          html += `<span class="pag-info">Página ${estadoVacCad.pagina} de ${totalPags}</span>`;
        if (estadoVacCad.pagina < totalPags)
          html += `<button class="pag-btn" onclick="irPagVacCad(${estadoVacCad.pagina + 1})">Siguiente ›</button>`;
        if (pagDiv) pagDiv.innerHTML = html;
      }

      function irPagVacCad(n) {
        estadoVacCad.pagina = n;
        _renderVacCad();
        document
          .getElementById("tbody-vacunas-cad")
          ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }

      const estadoAgenda = { datos: [], pagina: 1, dias: 60 };

      async function cargarAgenda(dias) {
        dias = dias || estadoAgenda.dias;
        estadoAgenda.dias = dias;
        estadoAgenda.pagina = 1;

        [30, 60, 90].forEach((d) => {
          const b = document.getElementById("agenda-btn-" + d);
          if (b) {
            b.className = d === dias ? "btn btn-primary" : "btn btn-accion";
          }
        });

        const tbody = document.getElementById("tbody-agenda");
        if (tbody)
          tbody.innerHTML =
            '<tr class="empty-row"><td colspan="9">Cargando…</td></tr>';

        try {
          const json = await (
            await fetch(API + "/vencimientos?dias=" + dias)
          ).json();
          if (!json.ok) {
            mostrarAlerta("alert-agenda", "error", json.error);
            return;
          }
          estadoAgenda.datos = json.datos;
          _renderAgenda();
        } catch (err) {
          logError(err?.message || "Error en ", "", err?.stack);
          mostrarAlerta(
            "alert-agenda",
            "error",
            "Error: " + (err.message || "No se pudo conectar."),
          );
        }
      }

      function _renderAgenda() {
        const tbody = document.getElementById("tbody-agenda");
        const cont = document.getElementById("agenda-contador");
        const pagDiv = document.getElementById("pag-agenda");
        const datos = estadoAgenda.datos;

        if (cont)
          cont.textContent = datos.length
            ? datos.length +
              " animal" +
              (datos.length > 1 ? "es" : "") +
              " encontrado" +
              (datos.length > 1 ? "s" : "")
            : "Sin resultados";

        if (!datos.length) {
          tbody.innerHTML =
            '<tr class="empty-row"><td colspan="9">Sin animales con vacuna próxima a vencer en ese rango.</td></tr>';
          if (pagDiv) pagDiv.innerHTML = "";
          return;
        }

        const ini = (estadoAgenda.pagina - 1) * POR_PAGINA;
        const page = datos.slice(ini, ini + POR_PAGINA);

        tbody.innerHTML = page
          .map((r) => {
            const prop =
              [r.NOMBRE_PROP, r.PRIMER_APELLIDO, r.SEGUNDO_APELLIDO]
                .filter(Boolean)
                .join(" ") || "—";
            const fvac = r.FECHA_VACUNA ? r.FECHA_VACUNA.substring(0, 10) : "—";
            const venc = r.VENCE ? r.VENCE.substring(0, 10) : "—";
            const dias = r.DIAS_RESTANTES;
            let badge = "",
              cls = "";
            if (dias !== null && dias !== undefined) {
              if (dias <= 0) {
                badge = `<span class="dias-badge critica">VENCIDA</span>`;
              } else if (dias <= 15) {
                badge = `<span class="dias-badge critica">${dias}d</span>`;
              } else if (dias <= 30) {
                badge = `<span class="dias-badge alta">${dias}d</span>`;
              } else {
                badge = `<span class="dias-badge normal">${dias}d</span>`;
              }
            }
            const chip = r.N_CHIP || "—";
            return `<tr style="cursor:pointer;" data-chip="${chip}" onclick="abrirFicha(this.dataset.chip)">
      <td data-label="Chip"><span class="tag tag-id">${chip}</span></td>
      <td data-label="Animal">${r.NOMBRE || "(sin nombre)"}</td>
      <td data-label="Especie">${r.ESPECIE || "—"}</td>
      <td data-label="Propietario">${prop}</td>
      <td data-label="Teléfono" style="font-family:'IBM Plex Mono',monospace;">${r.TELEFONO1 || "—"}</td>
      <td data-label="Última vacuna" style="font-family:'IBM Plex Mono',monospace;">${fvac}</td>
      <td data-label="Vence" style="font-family:'IBM Plex Mono',monospace;">${venc}</td>
      <td data-label="Días">${badge}</td>
      <td data-label="Carta"><button class="btn btn-accion" style="padding:.25rem .6rem;font-size:.7rem;"
        onclick="event.stopPropagation();generarCarta(${JSON.stringify(r)})">Carta</button></td>
    </tr>`;
          })
          .join("");

        const totalPags = Math.ceil(datos.length / POR_PAGINA);
        let html = "";
        if (estadoAgenda.pagina > 1)
          html += `<button class="pag-btn" onclick="irPagAgenda(${estadoAgenda.pagina - 1})">‹ Anterior</button>`;
        if (totalPags > 1)
          html += `<span class="pag-info">Página ${estadoAgenda.pagina} de ${totalPags}</span>`;
        if (estadoAgenda.pagina < totalPags)
          html += `<button class="pag-btn" onclick="irPagAgenda(${estadoAgenda.pagina + 1})">Siguiente ›</button>`;
        if (pagDiv) pagDiv.innerHTML = html;
      }

      function irPagAgenda(n) {
        estadoAgenda.pagina = n;
        _renderAgenda();
        document
          .getElementById("tbody-agenda")
          ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }

      function generarCarta(r) {
        const hoy = new Date().toLocaleDateString("es-ES", {
          day: "2-digit",
          month: "long",
          year: "numeric",
        });
        const prop =
          [r.NOMBRE_PROP, r.PRIMER_APELLIDO, r.SEGUNDO_APELLIDO]
            .filter(Boolean)
            .join(" ") || "—";
        const dom =
          [r.DOMICILIO, r.CP, r.MINICIPIO].filter(Boolean).join(", ") || "—";
        const fvac = r.FECHA_VACUNA ? r.FECHA_VACUNA.substring(0, 10) : "—";
        const venc = r.VENCE ? r.VENCE.substring(0, 10) : "—";
        const animal = r.NOMBRE || "(sin nombre)";
        const chip = r.N_CHIP || "—";
        const dias = r.DIAS_RESTANTES;
        const estado =
          dias !== null && dias <= 0 ? "ha caducado" : `vence el ${venc}`;

        document.getElementById("carta-contenido").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.5cm;">
      <div>
        <div style="font-size:14pt;font-weight:700;text-transform:uppercase;letter-spacing:.05em;">
          Ayuntamiento de Navalcarnero
        </div>
        <div style="font-size:9pt;color:#444;margin-top:.2cm;">
          Concejalía de Sanidad y Medio Ambiente<br>
          Censo Municipal de Animales
        </div>
      </div>
      <div style="text-align:right;font-size:9pt;color:#444;">
        Navalcarnero, ${hoy}<br>
        Ref.: ${chip}
      </div>
    </div>

    <div style="margin-bottom:1cm;">
      <strong>D./Dña. ${prop}</strong><br>
      ${dom}
    </div>

    <div style="margin-bottom:.6cm;font-size:10pt;font-weight:700;text-transform:uppercase;
      letter-spacing:.05em;border-bottom:1px solid #000;padding-bottom:.2cm;">
      Asunto: Renovación de vacuna antirrábica obligatoria
    </div>

    <p style="text-align:justify;margin-bottom:.5cm;">
      Por medio de la presente, el Ayuntamiento de Navalcarnero se dirige a usted, en su
      condición de titular registrado en el Censo Municipal de Animales, para comunicarle
      que la vacuna antirrábica del animal <strong>${animal}</strong>
      (N.º chip: <strong>${chip}</strong>, especie: ${r.ESPECIE || "—"})
      inscrito a su nombre, ${estado}.
    </p>

    <p style="text-align:justify;margin-bottom:.5cm;">
      De conformidad con lo establecido en la normativa vigente sobre tenencia de animales
      de compañía, la vacunación antirrábica es obligatoria y debe mantenerse actualizada
      anualmente. La última vacunación registrada data del
      <strong>${fvac}</strong>, con vencimiento el <strong>${venc}</strong>.
    </p>

    <p style="text-align:justify;margin-bottom:.5cm;">
      En consecuencia, le instamos a que, en el plazo máximo de <strong>treinta (30) días
      naturales</strong> desde la recepción del presente escrito, acuda a un veterinario
      colegiado para proceder a la vacunación del animal y remita el correspondiente
      certificado a este Ayuntamiento para la actualización del censo.
    </p>

    <p style="text-align:justify;margin-bottom:1cm;">
      El incumplimiento de la presente notificación podrá conllevar la apertura del
      expediente sancionador correspondiente conforme a la legislación aplicable.
    </p>

    <p style="margin-bottom:2cm;">
      En caso de duda o para cualquier consulta, puede dirigirse a las oficinas municipales
      o contactar con el servicio de Censo de Animales.
    </p>

    <div style="display:flex;justify-content:space-between;margin-top:1.5cm;">
      <div style="text-align:center;width:45%;">
        <div style="border-top:1px solid #000;padding-top:.3cm;font-size:9pt;">
          Firma del Interesado/a
        </div>
      </div>
      <div style="text-align:center;width:45%;">
        <div style="border-top:1px solid #000;padding-top:.3cm;font-size:9pt;">
          El Alcalde/La Alcaldesa<br>
          Ayuntamiento de Navalcarnero
        </div>
      </div>
    </div>
  `;

        document.getElementById("carta-print").style.display = "block";
        document.body.style.overflow = "hidden";
      }

      function cerrarCarta() {
        document.getElementById("carta-print").style.display = "none";
        document.body.style.overflow = "";
      }

      const _formsSucios = new Set(["form-prop", "form-anim", "form-seg"]);
      function _formularioSucio() {
        for (const id of _formsSucios) {
          const f = document.getElementById(id);
          if (!f) continue;
          const inputs = f.querySelectorAll("input,select,textarea");
          for (const inp of inputs) {
            const v = inp.type === "checkbox" ? inp.checked : inp.value || "";
            if (v && v !== inp.getAttribute("data-inicial")) return id;
          }
        }
        return null;
      }
      function _marcarIniciales() {
        for (const id of _formsSucios) {
          const f = document.getElementById(id);
          if (!f) continue;
          f.querySelectorAll("input,select,textarea").forEach((inp) => {
            inp.setAttribute(
              "data-inicial",
              inp.type === "checkbox" ? inp.checked : inp.value || "",
            );
          });
        }
      }

      const _mostrarPaginaOrig = mostrarPagina;
      mostrarPagina = function (id, btn) {
        const sucio = _formularioSucio();
        if (sucio) {
          const nombres = {
            "form-prop": "Alta de Propietario",
            "form-anim": "Alta de Animal",
            "form-seg": "Póliza de Seguro",
          };
          if (
            !confirm(
              `Hay datos sin guardar en «${nombres[sucio] || sucio}».\n¿Desea salir sin guardar?`,
            )
          )
            return;
          document.getElementById(sucio)?.reset();
        }
        _mostrarPaginaOrig(id, btn);
        _marcarIniciales();
        if (id === "inicio") cargarAlertas();
      };
      if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
          navigator.serviceWorker
            .register("/sw.js")
            .then((r) => console.log("SW registrado:", r.scope))
            .catch((e) => console.warn("SW error:", e));
        });
      }
