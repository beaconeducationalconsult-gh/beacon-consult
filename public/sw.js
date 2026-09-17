/*
 * Beacon service worker — offline app shell + static curriculum/quotes.
 *
 * Only registered in production builds (see src/registerSW.js), so verify PWA
 * behaviour with `yarn build && yarn preview`, never `yarn dev`.
 *
 * Bump CACHE_VERSION whenever the curriculum, quotes, or shell change and you
 * want existing installs to pick the new copies up immediately. Bumping also
 * drops every older cache on activate, which is the cure when a stale copy of
 * the curriculum JSON is being served from an earlier build.
 */
const CACHE_VERSION = 'beacon-v2'

// Resolve the shell against the deploy base, not the domain root, so this
// worker also works when the app is served from a sub-path. `self.location` is
// the worker's own URL, so './' is the base the app was built with —
// the same value as import.meta.env.BASE_URL in src/hooks/useCurriculum.js.
const BASE = new URL('./', self.location).pathname
const SHELL_INDEX = `${BASE}index.html`
const SHELL = [BASE, SHELL_INDEX, `${BASE}manifest.webmanifest`, `${BASE}favicon.svg`]

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
          caches.open(CACHE_VERSION).then((c) => c.put(SHELL_INDEX, copy))
          return response
        })
        .catch(() => caches.match(SHELL_INDEX))
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
