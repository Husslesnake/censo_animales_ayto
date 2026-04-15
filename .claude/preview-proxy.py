#!/usr/bin/env python3
"""Mini-proxy HTTP que reenvía al contenedor nginx local (puerto 8181).

Permite que la herramienta de preview (que arranca su propio proceso en un
puerto asignado) sirva el contenido SSI del contenedor sin tocar Docker.
"""
import http.server
import socketserver
import urllib.request
import urllib.error
import sys
import os

TARGET = "http://127.0.0.1:8181"


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def _proxy(self, method):
        url = TARGET + self.path
        body = None
        if "Content-Length" in self.headers:
            body = self.rfile.read(int(self.headers["Content-Length"]))
        req = urllib.request.Request(url, data=body, method=method)
        for h in self.headers:
            if h.lower() in ("host", "content-length"):
                continue
            req.add_header(h, self.headers[h])
        try:
            with urllib.request.urlopen(req) as resp:
                self.send_response(resp.status)
                for h in resp.headers:
                    if h.lower() in ("transfer-encoding", "connection"):
                        continue
                    self.send_header(h, resp.headers[h])
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for h in e.headers:
                if h.lower() in ("transfer-encoding", "connection"):
                    continue
                self.send_header(h, e.headers[h])
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")

    def do_GET(self):     self._proxy("GET")
    def do_POST(self):    self._proxy("POST")
    def do_PUT(self):     self._proxy("PUT")
    def do_DELETE(self):  self._proxy("DELETE")
    def do_OPTIONS(self): self._proxy("OPTIONS")
    def do_HEAD(self):    self._proxy("HEAD")

    def log_message(self, *args):
        pass  # silencio para no contaminar la salida


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8889))
    with ReusableTCPServer(("127.0.0.1", port), ProxyHandler) as httpd:
        print(f"Preview proxy listening on http://127.0.0.1:{port} -> {TARGET}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
