# 9. Playbooks

Step-by-step recipes for the common changes. Each mirrors an existing feature — copy the
nearest one and adapt.

## Add a new portal page

1. Create `src/pages/MyThing.jsx` (default export). Wrap in `mx-auto max-w-2xl`, use
   `.page-title`/`.page-subtitle`.
2. Register the route in `src/App.jsx` under the `/portal` `<Route>` block, e.g.
   `<Route path="mything" element={<MyThing />} />` (+ `/new`, `/:id`, `/:id/edit` as needed).
3. Add a nav entry in `src/components/Sidebar.jsx` (`links` array): `{ to, label, icon }`
   using an inline 24×24 SVG. Admin-only links go through the `adminLink` pattern.
4. If it reads/writes Firestore, follow "Add a new collection" below.

## Add a new Firestore collection

Say you're adding `widgets`:

1. **Writes/reads** in your page: `addDoc(collection(db, 'widgets'), { …, authorId: user.uid,
   authorName, createdAt: serverTimestamp() })`. Read with `getDocs`/`onSnapshot`.
2. **Security rule** — add a `match /widgets/{id}` block in `firestore.rules`. Copy the
   closest existing collection (e.g. `notes` for status-gated + likes, `lesson_plans` for
   visibility-gated). The standard shape:
   - `read: if isApprovedOrAdmin() && (<visibility/status/owner check>)`
   - `create: if isApprovedOrAdmin() && request.resource.data.authorId == request.auth.uid`
   - `update: if isApprovedOrAdmin() && (isOwner(resource.data.authorId) || isAdmin())`
   - `delete: if isOwner(resource.data.authorId) || isAdmin()`
   - For like/react fields, allow any approved member via
     `request.resource.data.diff(resource.data).affectedKeys().hasOnly([...])`.
3. **Indexes** — if you query with `where(...) + orderBy(...)` on different fields, add the
   composite index to `firestore.indexes.json` (Firestore's error also gives you a
   create-index link).
4. **Deploy** the backend: `firebase deploy --only firestore:rules,firestore:indexes`.
   *(This is the step most likely to be forgotten — the app will 403 without it. Committed
   rules are not deployed rules; see [gotchas.md](gotchas.md).)*

## Add a document exporter (PDF/DOCX/PPTX)

1. Add `src/lib/myThingPdf.js` (or `…Docx.js`/`…Pptx.js`) exporting a `downloadX(data, opts)`
   function. Reuse `docxShared.js` for Word; jsPDF+autotable for PDF; pptxgenjs for slides.
   For Word, pass `styles: documentStyles()` to the `Document` and use the `H1`/`H2`/`H3`
   constants as `heading:` values — a heading that Word cannot resolve renders as plain body
   text without complaining (see [gotchas.md](gotchas.md)).
2. In the page, **lazy-load** it at click time so it's not in the main bundle:
   ```js
   const { downloadX } = await import('../lib/myThingPdf')
   await downloadX(data, opts)
   ```
3. Model it on the closest existing exporter (`schemePdf.js`, `questionPaper.js`,
   `quizPptx.js`).

## Add a curriculum grade / subject

Curriculum is static JSON in `public/curriculum/`:

1. Add the grade to `grades.json`.
2. Add `<grade>_subjects.json` and `<grade>_indicators.json` (flat indicators with
   strand/sub-strand/content-standard fields — see an existing grade for the exact shape).
   Optionally `schedules/<grade>-<subject>.json` for day-by-day lessons (one file per
   subject-grade; `hasSchedule` on the subject says which exist).
3. No code change needed — `useCurriculum(grade)` / `useSchedules(grade, subjectId)` fetch
   by convention. Rebuild the bundle (`scripts/build_app_curriculum.py`), which writes a new
   `bundleHash`; the service worker names its cache after it, so existing installs pick the
   new files up on the next load without anyone editing a constant.

## Add quotes / theories

Edit `public/quotes/quotes.json` or `theories.json`. Keep the field shape
([data-model.md](data-model.md)); theories must keep `definition` + `theorist` +
`classroom` (Ghana application). Quotes are cached stale-while-revalidate; the app shell
cache is named after the curriculum bundle hash, so a quotes-only edit reaches an
already-installed browser on its next load but leaves the current cache name alone.

## Add a "like" to a new content type

Follow `quote_likes` (a separate `{type}_likes/{id}` collection with `count` + `likedBy[]`)
**or** the inline `posts`/`notes` pattern (`likedBy[]` + `likesCount` on the doc, with a
rules `affectedKeys().hasOnly([...])` allowance). The separate-collection approach suits
content that has no document of its own (like static quotes).
