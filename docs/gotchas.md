# 10. Gotchas & known gaps

Things that will bite you, roughly by severity. Found during the code audit — verify
against the live app before acting.

## 🟠 Committed rules ≠ deployed rules
Vercel does **not** deploy Firestore rules/indexes. Editing `firestore.rules` and pushing
changes nothing in production until `firebase deploy --only firestore:rules,firestore:indexes`
runs. This is the most common "it works locally / on my emulator but 403s in prod" cause.
(There's no `.firebaserc` — you may need `--project <id>`.)

## 🟡 Service worker is production-only
`registerSW.js` registers only when `import.meta.env.PROD`. **PWA/offline behavior does not
exist in `yarn dev`** — always verify with `yarn build && yarn preview`.

## 🟡 Stale service worker on localhost
Running several production builds on the same `localhost` origin can leave an old SW serving
a blank shell. Unregister it + clear caches in DevTools, then reload. Harmless on the real
domain.

## 🟡 Slides authoring is disabled
`SlideLessonForm.jsx` / `SlideLessonView.jsx` exist, but their routes are commented out in
`App.jsx`. Only `SlideLessons.jsx` (browse) is wired up. Don't assume slide creation works
end-to-end.

## 🟡 Feed can't render unauthenticated
`Feed.jsx`'s `posts` `onSnapshot` has no error callback, so rendering the Feed without an
approved session throws (only happens in odd/test contexts — in the app it's always behind
`ProtectedLayout`). Add an error callback if you ever need it to degrade gracefully.

## ⚪ Minor
- **`Navbar.jsx` is unused** — no page imports it (dead code). Landing has its own inline nav.
- **Env vars are required at build time** — a build without `VITE_FIREBASE_*` produces an app
  that can't reach Firebase; failures show at runtime, not build time.
- **`ToastContext.jsx`** trips `react-refresh/only-export-components` (exports a hook + a
  component from one file) — a long-standing lint nit, not a bug.

---

_When you fix any of these, delete the entry (or move it to a CHANGELOG) so this list stays
a list of **open** issues._
