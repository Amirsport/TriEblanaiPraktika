/* Service worker PWA «Умная AI-Теплица».
   Кэширует оболочку приложения, чтобы панель открывалась офлайн.
   Запросы к /api/ всегда идут в сеть (данные датчиков не кэшируются).

   Хостинг отдаёт .js и .css с кэшем на 45 дней, поэтому ссылки версионируются
   (?v=N): при выпуске новой версии поднимите N здесь, в js/app.js
   (регистрация service worker) и в front/index.html. */
'use strict';

const VERSION = '16';
const CACHE = `ai-greenhouse-v4-${VERSION}`;
const ASSETS = [
  './',
  './index.html',
  `./css/main.css?v=${VERSION}`,
  `./js/app.js?v=${VERSION}`,
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.pathname.startsWith('/api/')) return; // данные всегда свежие
  // Текущий адрес API тоже всегда из сети: из кэша страница получила бы адрес
  // прошлого запуска туннеля и не смогла бы подключиться.
  if (url.pathname.endsWith('/api-address.json')) return;

  // Страницы всегда тянем из сети: иначе после обновления версии браузер
  // отдавал бы старый HTML из кэша. Кэш — только запасной вариант офлайн.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
          }
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match('./index.html')))
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response.ok && url.origin === location.origin) {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
        }
        return response;
      }).catch(() => caches.match('./index.html'));
    })
  );
});
