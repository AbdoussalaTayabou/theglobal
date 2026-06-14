/* Service Worker pour notifications push.
   Servi depuis /sw.js (scope racine) via une route Flask. */
self.addEventListener('install', (e) => { self.skipWaiting(); });
self.addEventListener('activate', (e) => { e.waitUntil(self.clients.claim()); });

self.addEventListener('push', (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (_) {}
  const title = data.title || 'The Global Chronicle';
  const options = {
    body: data.body || '',
    icon: '/static/images/logo.png',
    badge: '/static/images/logo.png',
    data: { url: data.url || '/' },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(clients.matchAll({ type: 'window' }).then((wins) => {
    for (const w of wins) {
      if ('focus' in w) { w.navigate(url); return w.focus(); }
    }
    return clients.openWindow(url);
  }));
});
