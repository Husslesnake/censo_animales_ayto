      // ── Autenticación basada en IP ─────────────────────────────────────────
      // El token se guarda en localStorage; el rol viene del servidor.
      var sesion = null; // { rol: "admin"|"empleado", token: "..." }
      var _loginEstado = { es_admin_ip: false, configurado: true }; // caché del estado

      // Recupera token guardado en localStorage
      // Almacenamiento del token:
      // - recordar=true  → localStorage  (persiste 1 año, sobrevive al cierre del navegador)
      // - recordar=false → sessionStorage (desaparece al cerrar la pestaña/navegador)
      function _getToken() {
        try {
          var v = localStorage.getItem("censo_token") || sessionStorage.getItem("censo_token");
          return v ? JSON.parse(v) : null;
        } catch(e) { return null; }
      }
      function _setToken(data, recordar) {
        var str = JSON.stringify(data);
        if (recordar) {
          localStorage.setItem("censo_token", str);
          sessionStorage.removeItem("censo_token");
        } else {
          sessionStorage.setItem("censo_token", str);
          localStorage.removeItem("censo_token");
        }
      }
      function _clearToken() {
        localStorage.removeItem("censo_token");
        sessionStorage.removeItem("censo_token");
      }

      // ID único por navegador/dispositivo — se genera una vez y se persiste en localStorage.
      // El servidor lo usa como clave para empleados (la IP de Docker no distingue usuarios).
      function _getDeviceId() {
        var id = localStorage.getItem("censo_device_id");
        if (!id) {
          try {
            id = crypto.randomUUID();
          } catch(e) {
            id = "dev-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
          }
          localStorage.setItem("censo_device_id", id);
        }
        return id;
      }

      // Llama al backend con X-Token y X-Device-Id en cabecera
      async function apiFetch(url, opts) {
        opts = opts || {};
        opts.headers = opts.headers || {};
        var t = _getToken();
        if (t && t.token) opts.headers["X-Token"] = t.token;
        opts.headers["X-Device-Id"] = _getDeviceId();
        return fetch(url, opts);
      }

      // Inicializa la pantalla de login consultando el estado de auth al backend
      async function _initLoginScreen() {
        var badge = document.getElementById("login-rol-badge");
        var label = document.getElementById("login-pass-label");
        badge.style.display = "block";
        badge.textContent = "Detectando acceso…";
        try {
          var res = await fetch("/api/auth/estado", { headers: { "X-Device-Id": _getDeviceId() } });
          var data = await res.json();
          _loginEstado = data;
          var userInput = document.getElementById("login-user");
          var userLabel = document.getElementById("login-user-label");
          if (data.es_admin_ip) {
            badge.textContent = "Puerto de administración — Administrador";
            badge.style.borderColor = "var(--rojo)";
            badge.style.color = "var(--rojo)";
            if (label) label.textContent = "Contraseña de administrador";
            if (userInput) userInput.style.display = "none";
            if (userLabel) userLabel.style.display = "none";
          } else {
            badge.textContent = "Acceso de empleado";
            badge.style.borderColor = "var(--azul)";
            badge.style.color = "var(--azul)";
            if (label) label.textContent = "Contraseña";
            if (userInput) userInput.style.display = "";
            if (userLabel) userLabel.style.display = "";
          }
          if (!data.configurado && data.es_admin_ip) {
            var desc = document.getElementById("setup-desc");
            if (desc) {
              desc.textContent = "Este es el equipo servidor. Crea la contraseña de administrador para proteger el acceso.";
            }
            var passLbl = document.getElementById("setup-pass-label");
            if (passLbl) {
              passLbl.textContent = "Nueva contraseña (mín. 6 caracteres)";
            }
            document.getElementById("modal-setup-admin").style.display = "flex";
          }
        } catch(e) {
          badge.textContent = "Error al detectar modo de acceso";
          logError(e.message || "Error auth/estado", "_initLoginScreen", e.stack);
        }
      }

      async function doLogin() {
        var userEl = document.getElementById("login-user");
        var user = userEl && userEl.style.display !== "none" ? userEl.value.trim() : "";
        var pass = document.getElementById("login-pass").value;
        var recordar = document.getElementById("login-recordar") && document.getElementById("login-recordar").checked;
        var err = document.getElementById("login-error");
        err.classList.remove("show");
        if (!pass) {
          err.textContent = "Introduzca la contraseña.";
          err.classList.add("show");
          return;
        }
        if (!_loginEstado.es_admin_ip && !user) {
          err.textContent = "Introduzca su usuario.";
          err.classList.add("show");
          return;
        }
        try {
          var body = { password: pass, recordar: !!recordar };
          if (user) body.username = user;
          var res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Device-Id": _getDeviceId() },
            body: JSON.stringify(body)
          });
          var data = await res.json();
          if (data.ok) {
            err.classList.remove("show");
            sesion = { rol: data.rol, token: data.token };
            _setToken(sesion, !!recordar);
            aplicarRol(data.rol);
            document.getElementById("login-screen").classList.add("oculto");
            document.getElementById("login-pass").value = "";
            if (userEl) userEl.value = "";
            var btnInicio = document.getElementById("tab-inicio");
            mostrarPagina("inicio", btnInicio);
            setTimeout(cargarAlertas, 200);
            if (data.must_change) {
              abrirModalCambiarPass(true, data.motivo_cambio || "primer_acceso");
            }
          } else if (data.error === "configure_primero") {
            document.getElementById("modal-setup-admin").style.display = "flex";
          } else {
            err.textContent = data.error || "Contraseña incorrecta.";
            err.classList.add("show");
            document.getElementById("login-pass").value = "";
            document.getElementById("login-pass").focus();
          }
        } catch(e) {
          err.textContent = "Error de conexión con el servidor.";
          err.classList.add("show");
          logError(e.message || "Error doLogin", "doLogin", e.stack);
        }
      }

      async function doSetupAdmin() {
        var p1 = document.getElementById("setup-pass1").value;
        var p2 = document.getElementById("setup-pass2").value;
        var errEl = document.getElementById("setup-error");
        errEl.style.display = "none";
        var minLen = (_loginEstado && !_loginEstado.es_admin_ip) ? 4 : 6;
        if (p1.length < minLen) {
          errEl.textContent = "La contraseña debe tener al menos " + minLen + " caracteres.";
          errEl.style.display = "block"; return;
        }
        if (p1 !== p2) {
          errEl.textContent = "Las contraseñas no coinciden.";
          errEl.style.display = "block"; return;
        }
        try {
          var res = await fetch("/api/auth/setup", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Device-Id": _getDeviceId() },
            body: JSON.stringify({ password: p1 })
          });
          var data = await res.json();
          if (data.ok) {
            document.getElementById("modal-setup-admin").style.display = "none";
            sesion = { rol: data.rol, token: data.token };
            _setToken(sesion, true);
            aplicarRol(data.rol);
            document.getElementById("login-screen").classList.add("oculto");
            document.getElementById("setup-pass1").value = "";
            document.getElementById("setup-pass2").value = "";
            var btnInicio = document.getElementById("tab-inicio");
            mostrarPagina("inicio", btnInicio);
            setTimeout(cargarAlertas, 200);
          } else {
            errEl.textContent = data.error || "Error al configurar.";
            errEl.style.display = "block";
          }
        } catch(e) {
          errEl.textContent = "Error de conexión.";
          errEl.style.display = "block";
          logError(e.message, "doSetupAdmin", e.stack);
        }
      }

      function toggleUserMenu() {
        document.getElementById("user-dropdown").classList.toggle("open");
      }

      function cerrarUserMenu() {
        document.getElementById("user-dropdown").classList.remove("open");
      }

      document.addEventListener("click", function(e) {
        var wrapper = document.getElementById("user-menu-wrapper");
        if (wrapper && !wrapper.contains(e.target)) cerrarUserMenu();
      });

      var _cambioObligatorio = false;

      function abrirModalCambiarPass(obligatorio, motivo) {
        var rol = sesion && sesion.rol;
        var esAdmin = rol === "admin";
        var esEmpleadoNominal = rol === "empleado";
        _cambioObligatorio = !!obligatorio;
        document.getElementById("cambiar-pass-title").textContent =
          esAdmin ? "Cambiar contraseña de administrador"
          : rol === "policia" ? "Cambiar contraseña de agente"
          : "Cambiar contraseña de empleado";
        var avisoEl = document.getElementById("cambiar-aviso");
        if (avisoEl) {
          if (obligatorio) {
            avisoEl.textContent = motivo === "caducada"
              ? "Tu contraseña ha caducado (más de 1 año). Debes cambiarla para continuar."
              : "Es tu primer acceso. Debes establecer una contraseña nueva para continuar.";
            avisoEl.style.display = "block";
          } else {
            avisoEl.style.display = "none";
          }
        }
        var requisitosEl = document.getElementById("cambiar-requisitos");
        if (requisitosEl) {
          requisitosEl.style.display = esEmpleadoNominal ? "block" : "none";
        }
        var labelEl = document.getElementById("cambiar-nueva-label");
        if (labelEl) {
          labelEl.textContent = esEmpleadoNominal
            ? "Nueva contraseña"
            : "Nueva contraseña (mín. " + (esAdmin || rol === "policia" ? 6 : 4) + " caracteres)";
        }
        actualizarRequisitosPass("");
        document.getElementById("modal-cambiar-pass").style.display = "flex";
        document.getElementById("cambiar-error").style.display = "none";
        document.getElementById("cambiar-ok").style.display = "none";
        document.getElementById("cambiar-actual").value = "";
        document.getElementById("cambiar-nueva1").value = "";
        document.getElementById("cambiar-nueva2").value = "";
      }

      function cerrarModalCambiarPass() {
        if (_cambioObligatorio) return; // No se puede cerrar mientras sea obligatorio
        document.getElementById("modal-cambiar-pass").style.display = "none";
      }

      function _testRequisitos(pass) {
        return {
          len: pass.length >= 8,
          min: /[a-z]/.test(pass),
          may: /[A-Z]/.test(pass),
          num: /[0-9]/.test(pass),
          esp: /[^A-Za-z0-9]/.test(pass),
        };
      }

      function actualizarRequisitosPass(pass) {
        var r = _testRequisitos(pass || "");
        ["len","min","may","num","esp"].forEach(function(k) {
          var el = document.getElementById("req-" + k);
          if (!el) return;
          var ok = r[k];
          el.textContent = (ok ? "✓ " : "○ ") + el.textContent.replace(/^[✓○]\s*/, "");
          el.style.color = ok ? "var(--verde)" : "var(--gris3)";
        });
      }

      async function doCambiarPass() {
        var actual = document.getElementById("cambiar-actual").value;
        var nueva1 = document.getElementById("cambiar-nueva1").value;
        var nueva2 = document.getElementById("cambiar-nueva2").value;
        var errEl = document.getElementById("cambiar-error");
        var okEl = document.getElementById("cambiar-ok");
        errEl.style.display = "none"; okEl.style.display = "none";
        var rol = sesion && sesion.rol;
        var esAdmin = rol === "admin";
        var esEmpleadoNominal = rol === "empleado";
        if (esEmpleadoNominal) {
          var r = _testRequisitos(nueva1);
          var faltan = [];
          if (!r.len) faltan.push("8 caracteres");
          if (!r.min) faltan.push("minúscula");
          if (!r.may) faltan.push("mayúscula");
          if (!r.num) faltan.push("número");
          if (!r.esp) faltan.push("carácter especial");
          if (faltan.length) {
            errEl.textContent = "La contraseña no cumple los requisitos: " + faltan.join(", ") + ".";
            errEl.style.display = "block"; return;
          }
        } else {
          var minLen = esAdmin ? 6 : 4;
          if (nueva1.length < minLen) {
            errEl.textContent = "La nueva contraseña debe tener al menos " + minLen + " caracteres.";
            errEl.style.display = "block"; return;
          }
        }
        if (nueva1 === actual) {
          errEl.textContent = "La nueva contraseña debe ser distinta de la actual.";
          errEl.style.display = "block"; return;
        }
        if (nueva1 !== nueva2) {
          errEl.textContent = "Las contraseñas no coinciden.";
          errEl.style.display = "block"; return;
        }
        try {
          var t = _getToken();
          var res = await fetch("/api/auth/cambiar", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Token": (t && t.token) || "", "X-Device-Id": _getDeviceId() },
            body: JSON.stringify({ actual: actual, nueva: nueva1 })
          });
          var data = await res.json();
          if (data.ok) {
            sesion = { rol: data.rol, token: data.token };
            _setToken(sesion);
            okEl.textContent = "Contraseña cambiada correctamente.";
            okEl.style.display = "block";
            _cambioObligatorio = false;
            setTimeout(cerrarModalCambiarPass, 1500);
          } else {
            errEl.textContent = data.error || "Error al cambiar contraseña.";
            errEl.style.display = "block";
          }
        } catch(e) {
          errEl.textContent = "Error de conexión.";
          errEl.style.display = "block";
          logError(e.message, "doCambiarPass", e.stack);
        }
      }

      function togglePoliciaLogin() {
        var formPol = document.getElementById("policia-login-form");
        var formEmp = document.getElementById("empleado-login-form");
        var badge = document.getElementById("login-rol-badge");
        var errEmp = document.getElementById("login-error");
        var errPol = document.getElementById("pol-login-error");
        var visible = formPol.style.display !== "none";
        if (visible) {
          // Volver al login de empleado
          formPol.style.display = "none";
          if (formEmp) formEmp.style.display = "";
          document.getElementById("btn-toggle-policia").textContent =
            "Acceso de Policía Municipal";
          if (badge && _loginEstado) {
            if (_loginEstado.es_admin_ip) {
              badge.textContent = "Puerto de administración — Administrador";
              badge.style.borderColor = "var(--rojo)";
              badge.style.color = "var(--rojo)";
            } else {
              badge.textContent = "Acceso de empleado";
              badge.style.borderColor = "var(--azul)";
              badge.style.color = "var(--azul)";
            }
          }
          if (errPol) errPol.classList.remove("show");
          document.getElementById("login-pass").focus();
        } else {
          // Cambiar a login de policía (reemplaza al de empleado)
          if (formEmp) formEmp.style.display = "none";
          formPol.style.display = "block";
          document.getElementById("btn-toggle-policia").textContent =
            "Volver a acceso de empleado";
          if (badge) {
            badge.textContent = "Acceso de Policía Municipal";
            badge.style.borderColor = "var(--azul)";
            badge.style.color = "var(--azul)";
            badge.style.display = "block";
          }
          if (errEmp) errEmp.classList.remove("show");
          document.getElementById("pol-login-user").focus();
        }
      }

      async function doLoginPolicia() {
        var user  = document.getElementById("pol-login-user").value.trim();
        var pass  = document.getElementById("pol-login-pass").value;
        var recordar = document.getElementById("pol-login-recordar").checked;
        var errEl = document.getElementById("pol-login-error");
        errEl.classList.remove("show");
        if (!user || !pass) {
          errEl.textContent = "Introduzca usuario y contraseña.";
          errEl.classList.add("show");
          return;
        }
        try {
          var res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: user, password: pass, recordar: !!recordar })
          });
          var data = await res.json();
          if (data.ok) {
            sesion = { rol: data.rol, token: data.token };
            _setToken(sesion, !!recordar);
            aplicarRol(data.rol);
            document.getElementById("login-screen").classList.add("oculto");
            document.getElementById("pol-login-pass").value = "";
            mostrarPagina("policia", document.getElementById("tab-policia"));
            cargarIncidencias();
          } else {
            errEl.textContent = data.error || "Usuario o contraseña incorrectos.";
            errEl.classList.add("show");
            document.getElementById("pol-login-pass").value = "";
            document.getElementById("pol-login-pass").focus();
          }
        } catch(e) {
          errEl.textContent = "Error de conexión con el servidor.";
          errEl.classList.add("show");
          logError(e.message || "Error doLoginPolicia", "doLoginPolicia", e.stack);
        }
      }

      function doLogout() {
        var t = _getToken();
        if (t && t.token) {
          fetch("/api/auth/logout", {
            method: "POST",
            headers: { "X-Token": t.token }
          }).catch(function(){});
        }
        sesion = null;
        _clearToken();
        document.getElementById("login-screen").classList.remove("oculto");
        document.getElementById("login-pass").value = "";
        document.getElementById("header-session").style.display = "none";
        document.body.classList.remove("rol-admin", "rol-empleado", "rol-policia");
        document.querySelectorAll(".tab-btn").forEach(function (b) {
          b.classList.remove("active");
        });
        document.querySelectorAll(".page").forEach(function (p) {
          p.classList.remove("active");
        });
        var p = document.getElementById("page-propietarios");
        if (p) p.classList.add("active");
        _initLoginScreen();
      }
      function aplicarRol(rol) {
        document.body.classList.remove("rol-admin", "rol-empleado", "rol-policia");
        document.body.classList.add("rol-" + rol);
        var chip = document.getElementById("session-chip");
        var lbl = document.getElementById("session-label");
        chip.className = "session-chip " + rol;
        var labels = { admin: "Administrador", empleado: "Empleado", policia: "Policía" };
        lbl.textContent = labels[rol] || rol;
        document.getElementById("header-session").style.display = "";
        // Police: skip all non-police UI setup
        if (rol === "policia") return;
        var s = document.getElementById("inicio-saludo");
        var d = document.getElementById("inicio-desc");
        if (s) s.textContent = rol === "admin" ? "Panel de Administrador"
                              : "Panel de Empleado";
        if (d) d.textContent = rol === "admin" ? "Acceso completo al censo municipal"
                              : "Acceso restringido · Búsqueda por DNI requerida";
        if (rol !== "admin") {
          var empty =
            '<tr class="empty-row"><td colspan="10">Introduzca un criterio de búsqueda.</td></tr>';
          ["tbody-prop", "tbody-anim", "tbody-bajas", "tbody-seg"].forEach(
            function (id) {
              var el = document.getElementById(id);
              if (el) el.innerHTML = empty;
            },
          );
          [
            "prop-contador",
            "anim-contador",
            "baja-contador",
            "seg-contador",
          ].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.textContent = "";
          });
          [
            "btn-ocultar-prop",
            "btn-ocultar-anim",
            "btn-ocultar-bajas",
            "btn-ocultar-seg",
          ].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.style.display = "none";
          });
          [
            "tabla-wrap-prop",
            "tabla-wrap-anim",
            "tabla-wrap-bajas",
            "tabla-wrap-seg",
          ].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.classList.remove("oculta");
          });
          estado.prop = { datos: [], pagina: 1 };
          estado.anim = { datos: [], pagina: 1 };
          estadoBajas.datos = [];
          estadoBajas.todosDatos = [];
          estadoBajas.pagina = 1;
          _statsLoaded = false;
          ["pag-prop", "pag-anim", "pag-bajas", "pag-seg"].forEach(
            function (id) {
              var el = document.getElementById(id);
              if (el) el.innerHTML = "";
            },
          );
        }
      }
      // Inicializar sesión al cargar: verifica token guardado con el backend
      (async function _initSession() {
        var saved = _getToken();
        if (saved && saved.token) {
          try {
            var res = await fetch("/api/auth/verificar", {
              headers: { "X-Token": saved.token }
            });
            var data = await res.json();
            if (data.ok && data.rol) {
              sesion = { rol: data.rol, token: saved.token };
              aplicarRol(data.rol);
              document.getElementById("login-screen").classList.add("oculto");
              if (data.rol === "policia") {
                var btnPol = document.getElementById("tab-policia");
                if (btnPol) mostrarPagina("policia", btnPol);
                cargarIncidencias();
              } else {
                var btnInicio = document.getElementById("tab-inicio");
                if (btnInicio) mostrarPagina("inicio", btnInicio);
              }
              return;
            }
          } catch(e) {
            logError(e.message || "Error al restaurar sesión", "_initSession", e.stack);
          }
        }
        _clearToken();
        sesion = null;
        document.getElementById("header-session").style.display = "none";
        _initLoginScreen();
      })();
