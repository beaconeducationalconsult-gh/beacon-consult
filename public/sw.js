/*
 * Beacon service worker — offline app shell + static curriculum/quotes.
 *
 * Only registered in production builds (see src/registerSW.js), so verify PWA
 * behaviour with `yarn build && yarn preview`, never `yarn dev`.
 *
 * Bump CACHE_VERSION whenever the curriculum, quotes, or shell change and you
 * want existing installs to pick the new copies up immediately.
 */
const CACHE_VERSION = 'beacon-v1'
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/favicon.svg']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  // Never intercept Firebase/Firestore, Google Fonts or analytics — Firestore
  // runs its own offline cache and must see every request.
  if (url.origin !== self.location.origin) return

  // App shell: network first, cache fallback (SPA boots offline, Router takes over).
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_VERSION).then((c) => c.put('/index.html', copy))
          return response
        })
        .catch(() => caches.match('/index.html'))
    )
    return
  }

  // Same-origin assets (curriculum JSON, quotes, hashed JS/CSS, icons):
  // stale-while-revalidate.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response && response.status === 200 && response.type === 'basic') {
            const copy = response.clone()
            caches.open(CACHE_VERSION).then((c) => c.put(request, copy))
          }
          return response
        })
        .catch(() => cached)
      return cached || network
    })
  )
})
