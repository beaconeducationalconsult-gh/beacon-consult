# 7. PWA & offline

Beacon is an installable, offline-capable PWA. Three independent pieces make that work.

## 1. Installability — manifest + icons

- `public/manifest.webmanifest` — `standalone` display, cream `#faf6f1` theme,
  `start_url: /portal`, and three icons (192 `any`, 512 `any`, 512 `maskable`) in
  `public/icons/` (generated from `beaconlogo.png`).
- `index.html` links the manifest and sets `theme-color` + Apple touch/status-bar meta.

> On Android/Chrome a successful install mints a **WebAPK** that lands in the app drawer
> (not necessarily the home screen). "Prompt shown but no icon" usually means it installed
> to the drawer — check there.

## 2. Offline app shell — service worker (`public/sw.js`)

Registered by `src/registerSW.js`, which runs **only in production builds**
(`import.meta.env.PROD`) so Vite HMR is untouched in dev. Strategy:

- **Navigations:** network-first, falling back to cached `index.html` (the SPA boots offline
  and React Router takes over).
- **Same-origin assets** (`/curriculum/*`, `/quotes/*`, hashed JS/CSS, icons):
  **stale-while-revalidate** — served from cache instantly, refreshed in the background.
  Falls back to any precached copy when offline.
- **Precache:** the app shell. Curriculum and quotes JSON are cached on first use, so
  Quote-of-the-Day and anything already browsed work offline — and because schedules are per
  subject-grade, a class that has opened one subject's planner has that subject offline, not
  the whole grade's 5 MB. The cache is named after the bundle hash in
  `curriculum/_BUILD_REPORT.json`, so a rebuilt bundle invalidates old caches by itself.
- **Cross-origin (Firebase/Firestore, Google Fonts, analytics):** never intercepted —
  Firestore manages its own offline cache (below).

Because the SW only runs in production, **verify PWA behavior with `yarn preview`**, not
`yarn dev`.

## 3. Offline data — Firestore persistence (`src/firebase.js`)

Firestore is initialised with:

```js
initializeFirestore(app, {
  localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
})
```

Effect: reads are served from an IndexedDB cache and writes **queue locally when offline**,
then sync automatically on reconnect. No code in the pages needs to change — `onSnapshot`
and `addDoc`/`updateDoc` just work offline. The multi-tab manager keeps tabs/PWA windows
consistent.

### Sync indicator (`src/components/OfflineIndicator.jsx`)
A bottom-center pill mounted in `ProtectedLayout`. States, driven by `online`/`offline`
events + `waitForPendingWrites(db)`:
- **offline** — "changes save on this device and sync later"
- **syncing** — flushing queued writes after reconnect
- **synced** — brief confirmation, then hides

## Deterministic Quote of the Day

The daily quote / weekly theory are picked by **local date**, not a server, so they work
fully offline and everyone sees the same pick:

```js
dayNumber = floor(Date.UTC(y, m, d) / 86400000)   // stable per local day
quoteOfTheDay = quotes[dayNumber % quotes.length]
theoryOfTheWeek = theories[floor(dayNumber / 7) % theories.length]
```

(See `src/hooks/useWisdom.js`.)

## Gotcha: stale service worker in local testing

Testing multiple production builds on the same `localhost` origin can leave an old SW
serving a stale shell (blank root). Fix in DevTools → Application → unregister the SW +
clear caches, then reload. Not an issue on the real deployed domain.
