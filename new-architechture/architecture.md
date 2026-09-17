# 1. Architecture

## Shape

A single-page React app. There is no backend server of our own — the "backend" is
Firebase (Auth + Firestore) talked to directly from the browser. Static data
(curriculum, quotes) is shipped as JSON in `public/` and served by Vercel.

```
src/
  main.jsx            App bootstrap: providers + router + service-worker registration
  App.jsx             The route table + ProtectedLayout (the auth gate)
  firebase.js         Firebase app init; exports `auth` and `db` (Firestore w/ offline cache)
  index.css           Tailwind entry + the design-system class vocabulary
  context/            React contexts (auth, toasts)
  hooks/              Data hooks (curriculum JSON, wisdom/quotes)
  lib/                Pure helpers + document exporters (PDF/DOCX/PPTX)
  components/         Reusable UI (sidebar, modals, skeletons, editor, …)
  pages/              One component per route
  registerSW.js       Service-worker registration (production only)
public/
  curriculum/*.json   NaCCA curriculum data (KG1–B9)
  quotes/*.json       Quote-of-the-Day content
  manifest.webmanifest, sw.js, icons/   PWA assets
```

## Bootstrap (`src/main.jsx`)

Providers wrap the app in this order (outer → inner):

```
<StrictMode>
  <AuthProvider>          // Firebase auth state + the current user's profile doc
    <BrowserRouter>
      <ToastProvider>     // transient toast notifications
        <App />
        <Analytics />     // @vercel/analytics
```

After render, `registerServiceWorker()` runs (no-op in dev — see
[pwa-offline.md](pwa-offline.md)).

## Routing (`src/App.jsx`)

Two zones:

**Public** (no auth): `/` (Landing), `/vacancies`, `/quotes`, `/calendar`, `/articles`,
`/articles/:articleId`, `/login`, `/signup`.

**Protected portal** — all under `/portal`, rendered inside `ProtectedLayout`:

```
/portal                       Feed (index)
/portal/curriculum            Curriculum  →  /curriculum/:subjectId  SubjectBrowser
/portal/wisdom                Quote of the Day
/portal/articles              Articles  (+ /new, /:id, /:id/edit)
/portal/forecasts             Schemes of learning  (+ /new, /:id, /:id/edit)
/portal/plans                 Lesson plans  (+ /new, /:id, /:id/edit)
/portal/questions             Question bank  (+ /new, /generate, /quiz, /:id/edit)
/portal/notes                 Study notes  (+ /new, /:id, /:id/edit)
/portal/vacancies             Vacancies  (+ /new, /:id/edit)
/portal/slides                Slide lessons (sub-routes disabled — see gotchas)
/portal/wall                  My Wall (the member's own content)
/portal/authors/:authorId     Author profile page
/portal/search /progress /calendar /profile /members
```

`*` (anything else) → redirect to `/`.

## The auth gate (`ProtectedLayout`)

Every `/portal/*` route renders through `ProtectedLayout`, which reads `useAuth()` and:

1. Shows a "Loading…" splash while auth state or the profile doc is resolving.
2. If not signed in → `<Navigate to="/login">`.
3. If signed in but **not** `approved` (and not admin):
   - `status === 'suspended'` → `<PendingApproval suspended />`
   - otherwise → `<PendingApproval />` (awaiting approval)
4. Otherwise renders the shell: fixed **`<Sidebar>`** (desktop) / sticky top bar + drawer
   (mobile), the routed page in `<Outlet>`, and the global `<OfflineIndicator>`.

> This client-side gate is UX only. **Real enforcement is in `firestore.rules`** — the
> data layer independently rejects unapproved users. See [security.md](security.md).

## Layout

- Desktop: fixed 224px (`w-56`) sidebar on the left; content offset with `lg:ml-56`.
- Mobile: sidebar collapses to a sticky top bar with a slide-over drawer.
- Content column is centered, `max-w-5xl`. Individual pages narrow further
  (`max-w-2xl`/`max-w-3xl`) as needed.

## Data flow

- **Reads:** pages call Firestore directly (`getDoc`/`getDocs`/`onSnapshot`) via `db`
  from `src/firebase.js`. Real-time screens (Feed, note/article views) use `onSnapshot`.
- **Writes:** `addDoc`/`updateDoc`/`setDoc`/`deleteDoc`, always stamping `authorId` and
  `serverTimestamp()`.
- **Offline:** Firestore is initialised with `persistentLocalCache`, so reads are served
  from IndexedDB and writes queue when offline, then sync on reconnect
  ([pwa-offline.md](pwa-offline.md)).
- **Static curriculum/quotes:** fetched from `/curriculum/*.json` and `/quotes/*.json`
  via hooks with module-level caches ([shared-code.md](shared-code.md)).
