// =============================================================
//  Service Worker — Notificaciones Push + PWA offline básico
//  Archivo: static/sw.js
// =============================================================

const CACHE_NAME = 'restaurante-v1';
const URLS_CACHE = ['/dashboard', '/static/css/styles.css', '/static/img/icon-192.png'];

// ── Instalación: cachear recursos clave ──────────────────────
self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(URLS_CACHE).catch(() => {}))
            .then(() => self.skipWaiting())
    );
});

// ── Activación: limpiar caches viejas ───────────────────────
self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

// ── Fetch: responder desde caché si no hay red ───────────────
self.addEventListener('fetch', (e) => {
    if (e.request.method !== 'GET') return;
    e.respondWith(
        fetch(e.request)
            .then(res => {
                const clone = res.clone();
                caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
                return res;
            })
            .catch(() => caches.match(e.request))
    );
});

// ── Recibir push del servidor ─────────────────────────────────
self.addEventListener('push', function (event) {
    let data = { title: '🍽️ Pedido listo', body: 'Un pedido está listo para servir.' };
    try {
        if (event.data) data = event.data.json();
    } catch (e) {
        if (event.data) data.body = event.data.text();
    }

    const opciones = {
        body:     data.body || 'Un pedido está listo.',
        icon:     '/static/img/icon-192.png',
        badge:    '/static/img/badge-72.png',
        vibrate:  [300, 150, 300, 150, 500],
        tag:      'pedido-listo',
        renotify: true,
        data:     { mesa: data.mesa || '' },
        actions:  [{ action: 'ver', title: '👀 Ver pedidos' }]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, opciones)
    );
});

// ── Al tocar la notificación → abrir/enfocar el dashboard ────
self.addEventListener('notificationclick', function (event) {
    event.notification.close();
    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then(function (clientes) {
                for (const c of clientes) {
                    if (c.url.includes('/dashboard') && 'focus' in c) return c.focus();
                }
                if (self.clients.openWindow) return self.clients.openWindow('/dashboard');
            })
    );
});
