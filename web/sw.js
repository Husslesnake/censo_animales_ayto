// Service Worker — Censo Municipal de Animales
// Estrategia:
//   - Shell (HTML/CSS/JS) → stale-while-revalidate
//   - API GET (animales, incidencias) → network-first con fallback a caché
//   - API POST/PUT/DELETE → network-only (nunca cacheado)
//   - Otras peticiones → network-first

const VERSION = "censo-v1";
const SHELL_CACHE = "shell-" + VERSION;
const API_CACHE = "api-" + VERSION;

const SHELL_URLS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/css/base.css",
  "/css/forms.css",
  "/css/pages.css",
  "/css/print.css",
  "/js/config.js",
  "/js/utils.js",
  "/js/auth.js",
  "/js/ui.js",
  "/js/policia.js",
  "/js/busqueda.js",
  "/icons/icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) =>
      // addAll falla si cualquiera falla; usamos add por URL y toleramos errores
      Promise.all(
        SHELL_URLS.map((u) => cache.add(u).catch(() => null))
      )
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== SHELL_CACHE && k !== API_CACHE)
            .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

function esApiCacheable(url) {
  // Solo cacheamos consultas de lectura útiles sin token específico del usuario
  return (
    url.pathname.startsWith("/api/animales") ||
    url.pathname.startsWith("/api/propietarios") ||
    url.pathname.startsWith("/api/incidencias")
  );
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Mismo origen únicamente
  if (url.origin !== self.location.origin) return;

  // Mutaciones API: siempre red, nunca cache
  if (url.pathname.startsWith("/api/") && req.method !== "GET") {
    return; // deja que pase por red
  }

  // API GET: network-first con fallback a caché
  if (url.pathname.startsWith("/api/") && req.method === "GET") {
    if (!esApiCacheable(url)) return; // auth/verificar, estado, etc. → red directa
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const clone = res.clone();
            caches.open(API_CACHE)
              .then((c) => c.put(req, clone))
              .catch((err) => console.warn("SW: no se pudo cachear API", req.url, err));
          }
          return res;
        })
        .catch(() => caches.match(req).then((r) => r || new Response(
          JSON.stringify({ ok: false, error: "Sin conexión y sin datos en caché." }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        )))
    );
    return;
  }

  // Shell / recursos estáticos: stale-while-revalidate
  event.respondWith(
    caches.match(req).then((cached) => {
      const fetchPromise = fetch(req).then((res) => {
        if (res && res.ok && req.method === "GET") {
          const clone = res.clone();
          caches.open(SHELL_CACHE)
            .then((c) => c.put(req, clone))
            .catch((err) => console.warn("SW: no se pudo cachear shell", req.url, err));
        }
        return res;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
