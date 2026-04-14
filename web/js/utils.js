      async function logError(mensaje, contexto = "", stack = "") {
        try {
          const error_data = {
            mensaje: mensaje || "Error sin mensaje",
            tipo: "ERROR",
            contexto: contexto,
            stack: stack || "",
          };
          const response = await fetch(API + "/log", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(error_data),
          });
          if (!response.ok) {
            console.error("Error al registrar en log:", response.statusText);
          }
        } catch (err) {
          console.error("Error al enviar log al servidor:", err);
        }
      }

      window.onerror = function (msg, src, line, col, err) {
        logError(msg, src + ":" + line + ":" + col, err?.stack || "");
        return false;
      };
      window.addEventListener("unhandledrejection", function (e) {
        logError(
          e.reason?.message || String(e.reason),
          "unhandledrejection",
          e.reason?.stack || "",
        );
      });

      const LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE";
      function calcularLetraDNI(numero) {
        return LETRAS_DNI[numero % 23];
      }
      function validarFormatoDNI(valor) {
        const v = valor.trim().toUpperCase();
        const reDNI = /^(\d{8})([A-Z])$/;
        const mDNI = v.match(reDNI);
        if (mDNI) {
          const esperada = calcularLetraDNI(parseInt(mDNI[1]));
          if (mDNI[2] === esperada) return { ok: true, msg: "✔ DNI válido" };
          return {
            ok: false,
            msg: `✖ Letra incorrecta. La letra correcta es «${esperada}»`,
          };
        }
        const reNIE = /^([XYZ])(\d{7})([A-Z])$/;
        const mNIE = v.match(reNIE);
        if (mNIE) {
          const prefijo = { X: "0", Y: "1", Z: "2" }[mNIE[1]];
          const numero = parseInt(prefijo + mNIE[2]);
          const esperada = calcularLetraDNI(numero);
          if (mNIE[3] === esperada) return { ok: true, msg: "✔ NIE válido" };
          return {
            ok: false,
            msg: `✖ Letra incorrecta. La letra correcta es «${esperada}»`,
          };
        }
        if (/^\d{1,8}$/.test(v)) return { ok: null, msg: "" };
        if (/^\d{8}$/.test(v))
          return {
            ok: null,
            msg: "Falta la letra al final (DNI: 8 dígitos+letra · NIE: X/Y/Z+7 dígitos+letra)",
          };
        if (v.length === 0) return { ok: null, msg: "" };
        return {
          ok: false,
          msg: "✖ Formato incorrecto. DNI: 8 dígitos + letra (12345678A) · NIE: X/Y/Z + 7 dígitos + letra (X1234567A)",
        };
      }
      function validarDNI(input, alBlur = false) {
        const hint = document.getElementById("hint-prop-dni");
        const result = validarFormatoDNI(input.value);
        input.classList.remove("dni-ok", "dni-error");
        if (hint) {
          hint.className = "dni-hint";
          hint.textContent = "";
        }
        if (result.ok === true) {
          input.classList.add("dni-ok");
          if (hint) {
            hint.classList.add("ok");
            hint.textContent = result.msg;
          }
        } else if (result.ok === false) {
          input.classList.add("dni-error");
          if (hint) {
            hint.classList.add("error");
            hint.textContent = result.msg;
          }
        } else if (result.msg && alBlur) {
          input.classList.add("dni-error");
          if (hint) {
            hint.classList.add("error");
            hint.textContent = result.msg;
          }
        }
      }
      async function comprobarChipExistente(
        input,
        hintId,
        alertId,
        requireExiste = false,
      ) {
        const chip = input.value.trim().toUpperCase();
        const hint = document.getElementById(hintId);
        if (!chip) {
          input.classList.remove("dni-ok", "dni-error");
          if (hint) {
            hint.textContent = "";
            hint.className = "dni-hint";
          }
          return;
        }
        try {
          const json = await (
            await fetch(API + "/animales/" + encodeURIComponent(chip))
          ).json();
          const existe = json.ok && json.datos;
          if (!requireExiste) {
            if (existe) {
              input.classList.add("dni-error");
              input.classList.remove("dni-ok");
              const nombre = json.datos.NOMBRE || "";
              const msg = nombre
                ? `Chip ya registrado: ${nombre}`
                : "Este chip ya está registrado";
              if (hint) {
                hint.textContent = msg;
                hint.className = "dni-hint error";
              }
            } else {
              input.classList.add("dni-ok");
              input.classList.remove("dni-error");
              if (hint) {
                hint.textContent = "Chip disponible";
                hint.className = "dni-hint ok";
              }
            }
          } else {
            if (existe) {
              input.classList.add("dni-ok");
              input.classList.remove("dni-error");
              const nombre = json.datos.NOMBRE || "";
              const especie = json.datos.ESPECIE || "";
              const info = [nombre, especie].filter(Boolean).join(" · ");
              if (hint) {
                hint.textContent = info ? `Animal: ${info}` : "Chip encontrado";
                hint.className = "dni-hint ok";
              }
            } else {
              input.classList.add("dni-error");
              input.classList.remove("dni-ok");
              if (hint) {
                hint.textContent = "Chip no encontrado en el censo";
                hint.className = "dni-hint error";
              }
              if (alertId)
                mostrarAlerta(
                  alertId,
                  "error",
                  `El chip «${chip}» no está registrado en el censo de animales.`,
                );
            }
          }
        } catch (e) {
          logError(
            e?.message || "Error al verificar chip",
            "comprobarChipExistente",
            e?.stack,
          );
        }
      }
      function validarCampoDni(input, hintId, alBlur = true) {
        const hint = document.getElementById(hintId);
        const result = validarFormatoDNI(input.value);
        input.classList.remove("dni-ok", "dni-error");
        if (hint) {
          hint.className = "dni-hint";
          hint.textContent = "";
        }
        if (result.ok === true) {
          input.classList.add("dni-ok");
          if (hint) {
            hint.classList.add("ok");
            hint.textContent = result.msg;
          }
          return true;
        } else if (result.ok === false) {
          input.classList.add("dni-error");
          if (hint) {
            hint.classList.add("error");
            hint.textContent = result.msg;
          }
          return false;
        } else if (result.msg && alBlur) {
          input.classList.add("dni-error");
          if (hint) {
            hint.classList.add("error");
            hint.textContent = result.msg;
          }
          return false;
        }
        return false;
      }
      async function comprobarDniDuplicado(dni) {
        if (!dni || dni.length < 8) return;
        const hint = document.getElementById("hint-prop-dni");
        try {
          const json = await (
            await fetch(
              API +
                "/propietarios/" +
                encodeURIComponent(dni.trim().toUpperCase()),
            )
          ).json();
          if (json.ok && json.datos) {
            const p = json.datos;
            const nombre = [p.NOMBRE, p.PRIMER_APELLIDO, p.SEGUNDO_APELLIDO]
              .filter(Boolean)
              .join(" ");
            if (hint) {
              hint.className = "dni-hint error";
              hint.textContent = "Ya está registrad@: " + nombre;
            }
            const input = document.getElementById("input-prop-dni");
            if (input) {
              input.classList.add("dni-error");
              input.classList.remove("dni-ok");
            }
            mostrarAlerta(
              "alert-prop",
              "error",
              "Ya está registrad@: " + nombre,
            );
          }
        } catch (e) {
          logError(
            e?.message || "Error al comprobar DNI duplicado",
            "comprobarDniDuplicado",
            e?.stack,
          );
        }
      }
      function mostrarAlerta(id, tipo, msg) {
        const el = document.getElementById(id);
        el.className =
          "alert show " + (tipo === "ok" ? "alert-ok" : "alert-error");
        el.querySelector(".alert-icon").textContent = tipo === "ok" ? "✔" : "✖";
        el.querySelector(".alert-msg").textContent = msg;
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
        setTimeout(() => el.classList.remove("show"), 6000);
      }
      (function _healthCheck() {
        const dot = document.getElementById("api-status-dot");
        const txt = document.getElementById("api-status-txt");
        const wrap = document.getElementById("api-status");
        async function check() {
          try {
            const r = await fetch(API + "/sexos", {
              signal: AbortSignal.timeout(3000),
            });
            const ok = r.ok;
            if (wrap) wrap.style.display = ok ? "none" : "flex";
          } catch {
            if (wrap)
              wrap.style.display = "flex";
          }
        }
        check();
        setInterval(check, 30000);
      })();
