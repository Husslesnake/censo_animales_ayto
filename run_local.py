#!/usr/bin/env python3
"""Lanzador sin Docker.

Arranca en un solo proceso:
  - API Flask en 127.0.0.1:5000 (interno)
  - Servidor web empleados en 0.0.0.0:8000  (X-Admin-Access = "")
  - Servidor web admin      en 0.0.0.0:8181 (X-Admin-Access = "true")

Requiere MariaDB/MySQL corriendo localmente (por defecto 127.0.0.1:3306,
usuario root, pass 123, base censo_animales). Ajustable por variables de
entorno DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.

Soporta SSI <!--#include file="..." --> igual que la versión nginx.
"""
from __future__ import annotations

import http.server
import os
import re
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
API_PORT = 5000

os.environ.setdefault("LOG_DIR", str(ROOT / "logs"))
os.environ.setdefault("AUTH_FILE", str(ROOT / "auth.json"))
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "root")
os.environ.setdefault("DB_PASSWORD", "123")
os.environ.setdefault("DB_NAME", "censo_animales")

sys.path.insert(0, str(ROOT / "api"))

SSI_RE = re.compile(rb'<!--#include\s+file="([^"]+)"\s*-->')

_CT = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".ico": "image/x-icon",
    ".webmanifest": "application/manifest+json",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".txt": "text/plain; charset=utf-8",
}


def _ctype(ext: str) -> str:
    return _CT.get(ext.lower(), "application/octet-stream")


def _render_ssi(path: Path, visitados: set[Path] | None = None) -> bytes:
    visitados = visitados or set()
    if path in visitados:
        return b""
    visitados.add(path)
    data = path.read_bytes()

    def sub(m: re.Match) -> bytes:
        inc = (WEB_ROOT / m.group(1).decode()).resolve()
        try:
            inc.relative_to(WEB_ROOT.resolve())
        except ValueError:
            return b""
        if inc.is_file():
            return _render_ssi(inc, visitados)
        return b""

    return SSI_RE.sub(sub, data)


def _hacer_handler(admin: bool):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _proxy_api(self, method: str) -> None:
            url = f"http://127.0.0.1:{API_PORT}{self.path}"
            body = None
            if "Content-Length" in self.headers:
                body = self.rfile.read(int(self.headers["Content-Length"]))
            req = urllib.request.Request(url, data=body, method=method)
            for h in self.headers:
                if h.lower() in ("host", "content-length", "x-admin-access"):
                    continue
                req.add_header(h, self.headers[h])
            req.add_header("X-Admin-Access", "true" if admin else "")
            try:
                with urllib.request.urlopen(req) as resp:
                    body_out = resp.read()
                    self.send_response(resp.status)
                    for k, v in resp.headers.items():
                        if k.lower() in ("transfer-encoding", "connection", "content-length"):
                            continue
                        self.send_header(k, v)
                    self.send_header("Content-Length", str(len(body_out)))
                    self.end_headers()
                    self.wfile.write(body_out)
            except urllib.error.HTTPError as e:
                body_out = e.read()
                self.send_response(e.code)
                for k, v in e.headers.items():
                    if k.lower() in ("transfer-encoding", "connection", "content-length"):
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(body_out)))
                self.end_headers()
                self.wfile.write(body_out)
            except Exception as e:
                self.send_error(502, f"API no accesible: {e}")

        def _enviar(self, data: bytes, ctype: str, no_cache: bool = False) -> None:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if no_cache:
                self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(data)

        def _static(self) -> None:
            ruta = self.path.split("?", 1)[0].split("#", 1)[0]
            if ruta in ("", "/"):
                ruta = "/index.html"
            archivo = (WEB_ROOT / ruta.lstrip("/")).resolve()
            try:
                archivo.relative_to(WEB_ROOT.resolve())
            except ValueError:
                self.send_error(403)
                return
            if archivo.is_dir():
                archivo = archivo / "index.html"
            if not archivo.is_file():
                # SPA fallback: sirve index.html
                archivo = WEB_ROOT / "index.html"
            ext = archivo.suffix.lower()
            if ext in (".html", ".htm"):
                data = _render_ssi(archivo)
            else:
                data = archivo.read_bytes()
            self._enviar(data, _ctype(ext), no_cache=(ext in (".css", ".js", ".html")))

        def do_GET(self):
            if self.path.startswith("/api/"):
                self._proxy_api("GET")
            else:
                self._static()

        def do_POST(self):
            if self.path.startswith("/api/"):
                self._proxy_api("POST")
            else:
                self.send_error(405)

        def do_PUT(self):
            if self.path.startswith("/api/"):
                self._proxy_api("PUT")
            else:
                self.send_error(405)

        def do_DELETE(self):
            if self.path.startswith("/api/"):
                self._proxy_api("DELETE")
            else:
                self.send_error(405)

        def do_PATCH(self):
            if self.path.startswith("/api/"):
                self._proxy_api("PATCH")
            else:
                self.send_error(405)

        def log_message(self, fmt: str, *args) -> None:  # silenciar stdout
            pass

    return H


class _ServidorHilos(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _arrancar_web(puerto: int, admin: bool) -> None:
    srv = _ServidorHilos(("0.0.0.0", puerto), _hacer_handler(admin))
    srv.serve_forever()


def _arrancar_api() -> None:
    from app import app  # noqa: importa la aplicación Flask
    app.run(host="127.0.0.1", port=API_PORT, debug=False, use_reloader=False)


def main() -> None:
    print("=" * 70)
    print("  CENSO MUNICIPAL DE ANIMALES — modo local (sin Docker)")
    print("=" * 70)
    print(f"  BD: {os.environ['DB_USER']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}")
    print()

    threading.Thread(target=_arrancar_api, daemon=True).start()
    time.sleep(2.0)  # margen para que Flask quede escuchando

    threading.Thread(target=_arrancar_web, args=(8181, True), daemon=True).start()

    print("  Empleados: http://localhost:8000")
    print("  Admin:     http://localhost:8181")
    print("  API:       http://127.0.0.1:5000/api/  (interno)")
    print()
    print("  Ctrl+C para detener.")
    print("=" * 70)
    try:
        _arrancar_web(8000, False)
    except KeyboardInterrupt:
        print("\nDetenido.")


if __name__ == "__main__":
    main()
