const parameters = new URLSearchParams(self.location.search);
const cacheName = parameters.get("cache_name") ?? "poker-reconstruction-upload-v1";
const cachedPaths = [
  "/upload_benchmark.html",
  "/pkg-web/client_wasm.js",
  "/pkg-web/client_wasm_bg.wasm",
];

self.addEventListener("install", event => {
  event.waitUntil((async () => {
    const cache = await caches.open(cacheName);
    await cache.addAll(cachedPaths);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(key => key !== cacheName).map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener("message", event => {
  if (event.data?.type !== "POKER_SERVICE_WORKER_VERSION") return;
  event.source?.postMessage({
    type: "POKER_SERVICE_WORKER_VERSION",
    version: self.SERVER_BYTE_VERSION ?? 0,
  });
});

self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET"
    || url.origin !== self.location.origin
    || url.pathname === "/proof-upload"
    || url.pathname === "/network-results") {
    return;
  }
  event.respondWith((async () => {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(event.request, {ignoreSearch: true});
    if (cached) return cached;
    const response = await fetch(event.request);
    if (response.ok && cachedPaths.includes(url.pathname)) {
      await cache.put(event.request, response.clone());
    }
    return response;
  })());
});
