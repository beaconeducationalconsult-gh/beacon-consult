# The Code Bible — Building a React + Firebase App, End to End

A hands-on, build-in-order cookbook for making an app like Beacon: a **React SPA**
(Vite + Tailwind v4) on top of **Firebase** (Auth + Firestore), deployed on **Vercel**.

> **How this differs from the other docs.** [`project-blueprint.md`](project-blueprint.md)
> is the *process map* (the phases, in order). This file is the *code cookbook* — the
> concrete patterns and copy-pasteable snippets that fill those phases in. Deeper dives
> live in [`architecture.md`](architecture.md), [`data-model.md`](data-model.md),
> [`security.md`](security.md), [`conventions.md`](conventions.md),
> [`shared-code.md`](shared-code.md), [`pwa-offline.md`](pwa-offline.md),
> [`build-deploy.md`](build-deploy.md), and [`gotchas.md`](gotchas.md).

**Read it once top-to-bottom to learn the shape; then use it as a reference.** Every snippet
is a *pattern* — swap the names (`articles`, `Beacon`, …) for your own.

---

## Part 0 — The mental model

Four ideas carry the whole architecture. Internalise these and the rest is detail.

1. **The client is a thin, untrusted view. The database enforces the rules.**
   Any UI gate (hiding a button) is *cosmetic*. Real authorization lives in
   `firestore.rules`, evaluated on Firebase's servers. Design it in, never bolt it on.
2. **Identity vs. authorization are two things.** *Auth* (Firebase Auth) answers "who are
   you?". *Authorization* is your own data: a `users/{uid}` profile doc holding
   `role` (`member`/`admin`) and `status` (`pending`/`approved`/`suspended`).
3. **Build in vertical slices.** One full feature at a time — data shape → rules → list →
   form → view → wire it up → verify. A thin end-to-end feature beats half of everything.
4. **User context drives architecture.** Beacon's users are on mobile, often offline — so
   it's a PWA with an offline-first Firestore cache. Decide this early; it shapes everything.

**The stack, and why:** React 19 (UI) · Vite (fast dev/build) · Tailwind v4 (CSS-first
design tokens) · react-router (routing) · Firebase Auth + Firestore (auth + realtime +
offline, no server to run) · Vercel (git-push deploys). Best when the backend is mostly
CRUD + auth. If you need SQL relations or server rendering, reach for Next.js + Postgres
instead — the *principles* below still apply.

---

## Part 1 — Scaffold (get an empty app running & deployable first)

```bash
# one package manager, forever — pick yarn OR npm and never mix
yarn create vite my-app --template react
cd my-app
yarn add firebase react-router-dom
yarn add -D tailwindcss @tailwindcss/vite eslint
```

**`vite.config.js`** — wire in React + the Tailwind v4 plugin (no `tailwind.config.js`
needed in v4; config lives in CSS):

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({ plugins: [react(), tailwindcss()] })
```

**`.env.local`** (gitignored) — Firebase web config is *publishable* (not secret), but keep
it in env so dev/prod stay separate. Everything the client reads must be prefixed `VITE_`:

```bash
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_FIREBASE_STORAGE_BUCKET=...
VITE_FIREBASE_MESSAGING_SENDER_ID=...
VITE_FIREBASE_APP_ID=...
```

**Folder structure** — decide the shape on day one:

```
src/
  main.jsx            # entry: provider stack + router
  App.jsx             # route table + protected layout
  firebase.js         # Firebase init (the only place SDK is configured)
  index.css           # design tokens (@theme) + shared classes
  context/            # AuthContext, ToastContext (app-wide state)
  hooks/              # data hooks (useCurriculum, useWisdom, …)
  lib/                # pure helpers + heavy integrations (exporters, calendar math)
  components/         # shared components
    ui/               # design-system primitives (Button, Card, Field, …)
  pages/              # one file per route
firestore.rules       # THE security gate
firestore.indexes.json# composite indexes for where+orderBy queries
```

> **Smoke-deploy now**, before you have features to lose: push to Vercel, confirm the empty
> app builds and serves. A working pipeline early saves debugging later. See
> [`build-deploy.md`](build-deploy.md).

---

## Part 2 — The design system (tokens first, then primitives)

Do this **before** feature pages so every feature reuses the same vocabulary. Tailwind v4 is
CSS-first: an `@theme` block in `index.css` *is* your config. Define semantic tokens once;
change them in one place forever.

**`src/index.css`:**

```css
@import "tailwindcss";

@theme {
  /* Semantic palette — also generates bg-*/text-*/border-* utilities */
  --color-canvas:  #e8e8e8;  /* page background       */
  --color-surface: #f5f5f5;  /* cards / raised         */
  --color-ink:     #3e3e3e;  /* body / heading text    */
  --color-brand:   #047857;  /* primary/accent (AA-safe on light) */
  --color-brand-hover: #065f46;
  --color-frame:   #cfcfcf;  /* hairline borders       */

  /* Fluid type — text-* scales with the viewport (min → max) */
  --text-base: clamp(0.94rem, 0.89rem + 0.25vw, 1.06rem);
  --text-base--line-height: 1.55;
  /* …define xs…3xl the same way… */

  --radius-md: 0.5rem;   /* keep controls in an 8–12px band */
}

body { @apply bg-canvas text-ink antialiased; }

/* A tiny shared vocabulary used across every page */
@layer components {
  .page-title  { @apply text-2xl font-bold tracking-tight text-slate-900; }
  .card        { @apply rounded-xl border border-frame bg-surface shadow-sm; }
  .grid-responsive { @apply grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4; }
}
```

> **Two power moves.** (1) You can *retarget* Tailwind's built-in scales
> (`--color-slate-500: #…`) to reskin an entire app without touching a single component.
> (2) Keeping the `@theme` values semantic (`brand`, not `emerald`) means a rebrand is a
> one-line change.
>
> **Gotcha:** Tailwind v4's parser is fussy about **non-ASCII characters in `index.css`
> comments** (fancy dashes, arrows, apostrophes) — keep those comments plain ASCII or the
> build throws a cryptic `Missing opening (`.

**Primitives** live in `components/ui/`. A joiner + a Button is the whole idea — everything
else follows the pattern:

```jsx
// components/ui/cn.js
export const cn = (...p) => p.filter(Boolean).join(' ')

// components/ui/Button.jsx
import { Link } from 'react-router-dom'
import { cn } from './cn'

const VARIANTS = {
  primary:   'bg-brand text-white shadow-sm hover:bg-brand-hover',
  secondary: 'border border-frame bg-surface text-slate-700 hover:bg-slate-100',
  danger:    'bg-red-600 text-white hover:bg-red-700',
}
const SIZES = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' }

export default function Button({ variant = 'primary', size = 'md', to, className, ...rest }) {
  const cls = cn('inline-flex items-center justify-center gap-2 rounded-lg font-semibold',
    'transition-colors disabled:opacity-50', VARIANTS[variant], SIZES[size], className)
  if (to) return <Link to={to} className={cls} {...rest} />
  return <button type="button" className={cls} {...rest} />
}
```

Barrel-export them (`components/ui/index.js`) so pages do
`import { Button, Card, Field } from '../components/ui'`.

> **Accessibility gotcha:** on a *light* theme, mid-tone accents fail contrast. White text on
> emerald-600 is only ~3:1 (fails AA); emerald-700 is ~5.5:1 (passes). Check contrast before
> you commit a brand color. See [`conventions.md`](conventions.md).

---

## Part 3 — Backend: Firebase init, data model, and the security gate

### 3a. Initialize once — offline-first

**`src/firebase.js`** (the *only* place the SDK is configured):

```js
import { initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { initializeFirestore, persistentLocalCache, persistentMultipleTabManager } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

const app = initializeApp(firebaseConfig)
export const auth = getAuth(app)

// Reads serve from an IndexedDB cache; writes queue offline and sync on reconnect.
export const db = initializeFirestore(app, {
  localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
})
```

### 3b. Model the data (nouns + ownership + visibility)

You don't need final fields — just the entities and how access works. Every document gets:
- `authorId` (who owns it) — the linchpin of security rules,
- `createdAt` / `updatedAt` (`serverTimestamp()`),
- a **visibility/status** field (`public` / `members` / `private`, or `pending` /
  `approved`) that the rules and queries both key off.

Full schema in [`data-model.md`](data-model.md).

### 3c. Write the security rules — **this is the real backend**

Helpers first, then a per-collection read/create/update/delete matrix. `get()` reads the
caller's own profile doc to check role/status:

```js
// firestore.rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    function isSignedIn() { return request.auth != null; }
    function isOwner(uid) { return isSignedIn() && request.auth.uid == uid; }
    function isApproved() {
      return isSignedIn() &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.status == 'approved';
    }
    function isAdmin() {
      return isSignedIn() &&
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }

    // The authorization source of truth: the user's own profile
    match /users/{uid} {
      allow read:   if isSignedIn() && (request.auth.uid == uid || isApproved() || isAdmin());
      allow create: if isOwner(uid);                 // sign-up creates own profile
      allow update: if isOwner(uid) || isAdmin();
      allow delete: if isAdmin();
    }

    // A content collection: read by visibility/ownership; write by owner
    match /articles/{id} {
      allow read:   if resource.data.visibility == 'public'
                    || (isApproved() && resource.data.visibility == 'members')
                    || isOwner(resource.data.authorId) || isAdmin();
      allow create: if isApproved() && request.resource.data.authorId == request.auth.uid;
      allow update, delete: if isOwner(resource.data.authorId) || isAdmin()
        // narrow exception: let any approved member toggle likes
        || (isApproved() &&
            request.resource.data.diff(resource.data).affectedKeys().hasOnly(['likedBy','likesCount']));
    }
  }
}
```

> **Golden rules:** a `create` must assert `authorId == request.auth.uid` (so nobody forges
> ownership); an `update` that should only touch a couple of fields uses
> `diff().affectedKeys().hasOnly([...])`; and **no collection ships without a rule** — an
> unguarded collection is denied in prod (a real bug we hit). Details in
> [`security.md`](security.md).

### 3d. Indexes & deploy the backend separately

Any `where(...)` + `orderBy(...)` query needs a **composite index** in
`firestore.indexes.json` (Firestore's error gives you a one-click link to create it).
Deploy the backend on its own pipeline — **committed ≠ deployed**:

```bash
firebase deploy --only firestore:rules,firestore:indexes
```

---

## Part 4 — Auth: context + the gate + sign-up

One provider subscribes to auth state *and* the live profile doc, and exposes both:

```jsx
// context/AuthContext.jsx
import { createContext, useContext, useEffect, useState } from 'react'
import { onAuthStateChanged, signOut } from 'firebase/auth'
import { doc, onSnapshot } from 'firebase/firestore'
import { auth, db } from '../firebase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(undefined) // undefined=loading, null=no doc
  const [loading, setLoading] = useState(true)

  useEffect(() => onAuthStateChanged(auth, (u) => {
    setUser(u); setLoading(false); setProfile(u ? undefined : null)
  }), [])

  useEffect(() => {
    if (!user) return
    return onSnapshot(doc(db, 'users', user.uid), (s) => setProfile(s.exists() ? s.data() : null))
  }, [user])

  return <AuthContext.Provider value={{ user, profile, loading, logout: () => signOut(auth) }}>
    {children}
  </AuthContext.Provider>
}
export const useAuth = () => useContext(AuthContext)
```

**Sign-up must create the profile doc** — that doc is your authorization source of truth:

```jsx
const cred = await createUserWithEmailAndPassword(auth, email, password)
await updateProfile(cred.user, { displayName: name })
await setDoc(doc(db, 'users', cred.user.uid), {
  uid: cred.user.uid, name, email,
  role: 'member', status: 'pending',        // admin approves later
  createdAt: serverTimestamp(),
})
```

**The gate** redirects unauthenticated users and shows pending/suspended states (Part 5).

---

## Part 5 — The app shell: providers + routing + the protected layout

Provider order matters: **Auth → Router → Toasts → App**.

```jsx
// main.jsx
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <ToastProvider>
          <App />
        </ToastProvider>
      </BrowserRouter>
    </AuthProvider>
  </StrictMode>,
)
```

`App.jsx` splits **public** from **protected** routes; the protected layout is the gate:

```jsx
function ProtectedLayout() {
  const { user, profile, loading } = useAuth()
  if (loading || (user && profile === undefined)) return <FullScreen>Loading…</FullScreen>
  if (!user) return <Navigate to="/login" replace />
  const status = profile?.status ?? 'pending'
  if (profile?.role !== 'admin' && status !== 'approved') return <PendingApproval />
  return <Shell><Outlet /></Shell>   // sidebar + <main> content outlet
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/portal" element={<ProtectedLayout />}>
        <Route index element={<Home />} />
        <Route path="articles" element={<Articles />} />
        <Route path="articles/new" element={<ArticleForm />} />
        <Route path="articles/:id" element={<ArticleView />} />
        <Route path="articles/:id/edit" element={<ArticleForm />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
```

---

## Part 6 — The data layer: read, write, and query patterns

**Read once** (list pages) with `getDocs`; **subscribe** (live data) with `onSnapshot`;
**write** with `addDoc` / `updateDoc` / `deleteDoc`. Always clean up subscriptions.

```jsx
// subscribe (realtime) — return the unsub for cleanup
useEffect(() => {
  const q = query(collection(db, 'posts'), orderBy('createdAt', 'desc'), limit(50))
  return onSnapshot(q, (snap) => setPosts(snap.docs.map((d) => ({ id: d.id, ...d.data() }))))
}, [])

// create — stamp ownership + timestamps so rules pass
await addDoc(collection(db, 'articles'), {
  ...form, authorId: user.uid, authorName: profile.name,
  createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
})
```

**The "public + own" merge** — a rules-friendly way to show *my private items alongside the
public ones* without a query the rules would reject (run two narrow queries, dedupe):

```jsx
const snaps = await Promise.all([
  getDocs(query(col, where('visibility', '==', 'public'), limit(200))),
  getDocs(query(col, where('authorId', '==', user.uid), limit(100))),
])
const map = new Map()
for (const s of snaps) s.forEach((d) => map.set(d.id, { id: d.id, ...d.data() }))
const items = [...map.values()]
```

**Wrap reusable/derived data in a hook** so pages stay declarative:

```jsx
// hooks/useArticles.js
export function useArticles() {
  const [articles, setArticles] = useState(null)   // null = loading
  useEffect(() => { /* fetch + setArticles */ }, [])
  return { articles }
}
```

> **Compute derived state at render time** (with `useMemo`), not in effects. Filtering a list
> by a search box is `useMemo`, not a second `useState` + effect that can desync.

---

## Part 7 — The feature slice recipe (do this per feature)

This is the loop you repeat for every entity. Worked example: **Articles**.

1. **Rules + index** for the `articles` collection (Part 3c/3d).
2. **Routes:** `articles` (list) · `articles/new` · `articles/:id` (view) · `articles/:id/edit`.
3. **Form** (create *and* edit share one component; presence of `:id` = edit mode):

```jsx
const { id } = useParams()
useEffect(() => { if (id) getDoc(doc(db,'articles',id)).then(s => s.exists() && setForm(s.data())) }, [id])
async function submit(e) {
  e.preventDefault()
  if (id) await updateDoc(doc(db,'articles',id), { ...form, updatedAt: serverTimestamp() })
  else    await addDoc(collection(db,'articles'), { ...form, authorId: user.uid, createdAt: serverTimestamp() })
  navigate('/portal/articles')
}
```

4. **Handle the three states, everywhere** — this is the maturity marker most apps skip:

```jsx
{!items ? <SkeletonGrid />              /* loading  */
 : items.length === 0 ? <EmptyState … /> /* empty    */
 : <Grid>{items.map(a => <Card banner={a.title} …/>)}</Grid> /* data */}
```

5. **Add a nav entry**, link list ↔ view ↔ edit.
6. **Verify by driving the flow**: create → see it in the list → edit → delete. Confirm the
   rules allow the allowed ops and *deny the forbidden ones*.

See [`playbooks.md`](playbooks.md) for step-by-step feature recipes.

---

## Part 8 — Cross-cutting concerns (add once, reuse everywhere)

- **Toasts** — a `ToastProvider` + `useToast()` (`toast.success/error/info`) beats scattering
  alert UI. Keep semantic colors (green/red) even in a grayscale theme.
- **Confirm dialog** — replace `window.confirm()` with a `<ConfirmModal>` driven by state:
  `setConfirm({ title, body, onConfirm })`. Never hard-delete without it.
- **Empty & skeleton states** — one `<EmptyState>` and one `<Skeleton*>` set, reused. They
  make loading and "no data" feel designed, not broken.
- **PWA / offline** — web manifest + icons (installable) + a service worker (cache the app
  shell). The persistent Firestore cache (Part 3a) makes reads/writes work offline and sync
  later. Add an online/offline indicator. Full recipe in [`pwa-offline.md`](pwa-offline.md).
- **Heavy integrations lazy-load.** Exporters (PDF/DOCX/PPTX) are big — import them only when
  the user clicks "Download": `const { makePdf } = await import('../lib/schemePdf')`. Keeps
  the initial bundle lean.

---

## Part 9 — Verify, then deploy (two pipelines, never conflated)

```bash
yarn lint && yarn build      # must be clean — this is your gate
```

- **Frontend → Vercel:** connect the repo, set the `VITE_*` env vars (Production *and*
  Preview), add an SPA rewrite so client routes work (`/(.*) → /index.html`). Every push =
  a **preview** deploy; `main` = **production**. Branch + preview for risky changes; commit
  straight to `main` for small, verified ones.
- **Backend → Firebase CLI:** `firebase deploy --only firestore:rules,firestore:indexes`.
  Vercel does *not* do this — the classic "works locally, 403s in prod" bug is un-deployed
  rules.

**Verify by driving the real flow**, not just by building. A build that compiles can still be
broken. Log in, click through each journey, watch the console. See [`build-deploy.md`](build-deploy.md).

---

## Part 10 — Principles & gotchas (the fridge magnet)

1. **Security lives at the data layer.** UI gates are cosmetics; `firestore.rules` is law.
2. **Build vertical slices; keep it always-runnable.** Thin end-to-end > half of everything.
3. **Verify by driving the flow.** Observe behavior; don't trust a green build.
4. **Commit small and often.** A giant uncommitted working tree is the enemy of sanity.
5. **One package manager. Clean lint/build as a gate. `main` stays deployable.**
6. **Stamp `authorId` + timestamps on every write.** Rules and history depend on it.
7. **Three states everywhere:** loading → empty → error → data.
8. **Derive at render time** (`useMemo`), don't mirror state into effects.
9. **Deploy frontend and backend separately.** Committed ≠ deployed.
10. **User context drives architecture** (offline-first, mobile-first) — decide it up front.

More traps and their fixes: [`gotchas.md`](gotchas.md).

---

### Appendix — where things live

| Concern | File(s) |
|---|---|
| Firebase config | `src/firebase.js` |
| Provider stack | `src/main.jsx` |
| Routes + gate | `src/App.jsx` |
| Auth state | `src/context/AuthContext.jsx` |
| Design tokens | `src/index.css` (`@theme`) |
| UI primitives | `src/components/ui/` |
| Data hooks | `src/hooks/` |
| Pure/heavy helpers | `src/lib/` |
| One file per screen | `src/pages/` |
| **The security gate** | `firestore.rules` |
| Composite indexes | `firestore.indexes.json` |

*This cookbook is a living document — update it when the patterns change. Pair it with
[`project-blueprint.md`](project-blueprint.md) (the phase map) and the deep-dive docs above.*
