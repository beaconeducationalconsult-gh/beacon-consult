/*
 * Beacon service worker — offline app shell + static curriculum/quotes.
 *
 * Only registered in production builds (see src/registerSW.js), so verify PWA
 * behaviour with `yarn build && yarn preview`, never `yarn dev`.
 *
 * The cache is named after the served bundle's content hash, read from
 * curriculum/_BUILD_REPORT.json (`bundleHash`, written by
 * scripts/build_app_curriculum.py). A rebuilt bundle therefore renames its own
 * cache and activate() drops the old one — no constant to bump by hand, and no
 * "stale curriculum until someone remembers" failure mode. If the manifest
 * cannot be read (offline first run), the fallback name is used and the next
 * install picks the hash up.
 */
const FALLBACK_CACHE = 'beacon-shell'

/*
 * The random query is what makes this read fresh: the *previous* worker is
 * still in control while this one installs, and its stale-while-revalidate
 * handler would otherwise answer from the cache it is about to be retired for.
 * A URL it has never seen is a guaranteed cache miss, so the response is the
 * one the network has now.
 */
async function bundleCacheName() {
  try {
    const url = `${REPORT_URL}?sw=${Math.random().toString(36).slice(2)}`
    const res = await fetch(url, { cache: 'no-store' })
    if (res.ok) {
      const { bundleHash } = await res.json()
      if (bundleHash) return `beacon-${bundleHash}`
    }
  } catch {
    // Offline, or a deploy that has not written the report yet.
  }
  return FALLBACK_CACHE
}

/** Set during install, before any fetch is handled. */
let CACHE = FALLBACK_CACHE

// Resolve the shell against the deploy base, not the domain root, so this
// worker also works when the app is served from a sub-path. `self.location` is
// the worker's own URL, so './' is the base the app was built with —
// the same value as import.meta.env.BASE_URL in src/hooks/useCurriculum.js.
const BASE = new URL('./', self.location).pathname
const SHELL_INDEX = `${BASE}index.html`
const SHELL = [BASE, SHELL_INDEX, `${BASE}manifest.webmanifest`, `${BASE}favicon.svg`]
// Declared after BASE — a module-level `const` that reads it earlier would throw.
const REPORT_URL = `${BASE}curriculum/_BUILD_REPORT.json`

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    CACHE = await bundleCacheName()
    const cache = await caches.open(CACHE)
    await cache.addAll(SHELL)
    await self.skipWaiting()
  })())
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys()
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    await self.clients.claim()
  })())
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
          caches.open(CACHE).then((c) => c.put(SHELL_INDEX, copy))
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
            caches.open(CACHE).then((c) => c.put(request, copy))
          }
          return response
        })
        .catch(() => cached)
      return cached || network
    })
  )
})
