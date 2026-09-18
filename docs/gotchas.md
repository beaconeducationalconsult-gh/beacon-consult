# 10. Gotchas & known gaps

Things that will bite you. Verified against the code in this repository — each entry below
is an **open** issue; when one is fixed, delete it.

## 🔴 A read rule that inspects document fields breaks list queries

Firestore is not a filter. For a `list`, the rules must be provable for **every** document the
query could return, so a read rule that depends on document data denies the *whole query* — not
just the documents that fail it. The client then sees `permission-denied` on a page that should
simply show fewer rows.

This bit us in production. `isApprovedOrAdmin() && (status == 'published' || isOwner(...))` on
`notes`, `lesson_plans`, `weekly_forecasts` and `lesson_slides` broke every un-filtered list in
`src/pages/` — **for ordinary members only**. Admins pass every branch, so an admin testing the
portal sees it working.

A read rule needs one disjunct that holds regardless of the document, and is true for a member:
`isApprovedOrAdmin()`, `isApproved()` or `isSignedIn()`. `isAdmin()` is document-independent but
false for a member, so it does not rescue the query. Where a rule genuinely must gate on a field
(like `articles.visibility == 'public'` for the anonymous public page), the *query* has to carry
a matching `where(...)` — see `PublicArticles.jsx`.

`src/firestoreRules.test.js` fails if a collection the client lists un-filtered loses its
document-independent branch.

## 🟠 Committed rules ≠ deployed rules
Vercel does **not** deploy Firestore rules/indexes. Editing `firestore.rules` and pushing
changes nothing in production until `firebase deploy --only firestore:rules,firestore:indexes`
runs. This is the most common "it works locally / on my emulator but 403s in prod" cause.
`.firebaserc` pins the project (`beacon-educational-consu-8005e`); `make deploy-rules`
runs it. Note that rules pasted into the Firebase console are **not** version-controlled:
the console and `firestore.rules` can silently disagree, and only the repo file is reviewed.

## 🟠 Env vars are required at build time
`VITE_FIREBASE_*` are embedded at build time. Without a `.env.local` (or the equivalent
Vercel env vars) the build **succeeds** and the app fails at the first Firebase call. Copy
`.env.example` → `.env.local`; see [build-deploy.md](build-deploy.md).

## 🟡 Service worker is production-only
`registerSW.js` registers only under `import.meta.env.PROD`. **PWA/offline behavior does not
exist in `yarn dev`** — always verify with `yarn build && yarn preview`.

## 🟡 Stale service worker on localhost
Running several production builds on the same `localhost` origin can leave an old SW serving
a blank shell. Unregister it + clear caches in DevTools, then reload. Harmless on the real
domain.

## 🟡 Slides are browse + export only
`SlideLessons.jsx` builds a deck from the selected week's scheduled lessons and exports PPTX
(`lib/lessonSlidesPptx.js`); it can also save decks to `lesson_slides`. There is **no
authoring form and no deck-view page** — `SlideLessonForm`/`SlideLessonView` do not exist in
this portal. Don't assume slide creation works end-to-end.

## 🟡 The curriculum cache is permanent for the session
`useCurriculum`/`useSchedules` cache each JSON file in a module-level `Map` that never
expires. Curriculum only changes on deploy and the service worker revalidates in the
background, so this is intentional — but it means a hot-fix to a bundle file needs a reload,
and **bumping `CACHE_VERSION` in `public/sw.js`** is what makes existing installs pick up new
curriculum, quotes, or shell files.

## ⚪ Minor
- **The retired NCOS app lives under `legacy/`** and is reference-only — nothing in `src/`
  imports it. `make audit` reports its module manifest in a separate `LEGACY` section; that
  output never fails the audit.
- **`make audit` is only about data.** Errors mean the portal cannot source part of the
  dataset; the 8 subject-grades backed only by `data/reference/` are warnings by design.
- **The dev server runs on port 5199**, and `vite.config.js` needs
  `allowedHosts: ['.e2b.app', 'localhost']` for cloud sandboxes (Vite answers 403
  "Blocked request" otherwise).
- **The curriculum bundle is committed and large** (39.7 MB in `public/curriculum/`). It is
  cached by the service worker, so the first load is the expensive one.
- **Tailwind v4 can't `@apply` classes from `@layer components`.** The design vocabulary in
  `src/index.css` is defined with `@utility` for this reason — see
  [conventions.md](conventions.md).
