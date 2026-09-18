# Project TODO

The live backlog, ordered by **dependency**. Rewritten 2026-09-17 after the NCOS kernel app
was folded out to `legacy/` — items about that app (module `validate()`, `schoolId` history,
`generated_materials`, `storage.rules`, the 36 TypeScript errors) are **retired**, not
pending. Nothing in `src/` imports `legacy/`.

> **Anchor:** the portal must produce at least what the books produce, and must not serve
> curriculum it cannot source. Everything below is scored against that.

**Verify state at any time with:**

```bash
make check     # lint + tests + validate-curriculum + inventory + production build
make audit     # dataset vs portal agreement -> data/inventory.json (warnings are honest)
yarn test      # vitest: src/lib, buildTree, and contracts over public/curriculum
```

`make check` is also run by CI (`.github/workflows/ci.yml`) on every push, which
additionally fails if `data/inventory.json` is stale.

---

## P0 — the portal cannot run for real users yet

| # | Item | Why | Size |
|---|------|-----|------|
| P0-1 | **Configure Firebase**: copy `.env.example` → `.env.local` with the six `VITE_FIREBASE_*` values, and set the same on Vercel (Production + Preview) | Vite embeds these at build time. Without them the build is green and every Firebase call fails at runtime — no login, no content | S |
| P0-2 | **Deploy rules + indexes**: `make deploy-rules` (or paste `firestore.rules` into the console). `.firebaserc` is committed and pins `beacon-educational-consu-8005e` | **Done** — the user published the ruleset and reported it working. Caveat: the copy in the console predates the list-query fix in `08b19ab` and needs re-pasting (see P2-7 and gotchas.md) | S |
| P0-3 | **Bootstrap the first admin**: create an account, then set `role: 'admin'` (and `status: 'approved'`) on its `users/{uid}` doc in the Firebase console | **Done** — confirmed by the user. This is the only way in: sign-up forces `status: 'pending'`/`role: 'member'`, self-edits cannot change `role`/`status`, and only an admin can approve — so the console is the bootstrap path, and it must be repeated for each new school's first admin | S |
| P0-4 | **Drive the real flows once deployed** (the code bible's Phase 7): sign up → approve → create → view → edit → delete for a scheme, a plan, a question, and a note; check offline behavior with `yarn build && yarn preview` | A green build proves nothing about rules, indexes, or the service worker | M |

## P1 — data integrity (what teachers actually read)

| # | Item | Why | Size |
|---|------|-----|------|
| P1-1 | **Decide the fate of `data/reference/`** — audit the 8 bundle pairs that exist ONLY there (computing B4–B6, french B4–B6, KG1–KG2) and promote them into `data/curriculum/`, or drop them from the bundle | The portal currently serves unaudited curriculum for 8 subject-grades (~714 indicators) and nothing in the app says so | M |
| P1-2 | **Fill the L1 provenance gaps**: `english-language B4`, `mathematics B1`, `science B1` have databases but no summary (no source URL, no counts); `english-language B5` has a summary but no database in `data/curriculum/` | 184 indicators with unverifiable provenance are served to teachers | S |
| P1-3 | **Repair the 8 malformed reference summaries** (no `counts` block) | Any code that reads `summary['counts']` raises on them | S |
| P1-4 | **Say what L2 is, then act on it** — `competencies`, `resources`, `keywords`, `assessment` have exactly one distinct value per subject-grade; `starter` 75% / `main` 41% distinct, `rpk`/`plenary`/`assessment` ≈ 1% | Marketing and authoring budget depend on this. Either enrich per indicator or label generated documents honestly as templated | S |
| P1-5 | **Question bank content**: zero questions exist in the bundle (`public/curriculum/questions/` does not exist); `data/questions/` holds one mathematics B4 file | The generators render an empty selection from an empty bank — the highest-value content the dataset lacks | L |
| P1-6 | **Clean the 58 L2 `ind_desc` records with a repeated trailing sentence** (0.4% of slots) at the extraction source | Visible artefact in generated documents | S |
| P1-7 | **`indicatorDocId` keys on the bare indicator code** (`src/hooks/useCollection.js`) | `B4.1.1.1.1` exists in all ten B4 subjects, so the id is not grade-unique. Currently exported but unused — scope it by subject (or use `id`) before anything adopts it. See `docs/curriculum-data.md` | S |
| P1-8 | **The book skeleton seeds only the first session of each indicator** — `seed/build_book_skeleton.py` reads `sessions[0]` for the title, RPK, starter, main, plenary and performance indicator | Its own docstring promises "everything the database knows is *seeded*". Measured on B4: 263 of 377 indicator slots carry more than one session, and for 134 of them the later sessions hold *different* main-activity text — so those sessions' teaching content never reaches the draft books. Either collapse the sessions into the one lesson deliberately (and say so), or emit them as lesson sessions/variants | M |

## P2 — engineering debt that makes every future fix expensive

> **P2-2 (CI workflow) is done** — `.github/workflows/ci.yml` runs `make check` plus a
> stale-inventory guard on every push. Its number is left empty rather than renumbering,
> because other items reference these ids.

| # | Item | Why | Size |
|---|------|-----|------|
| P2-1 | **Firestore rules unit tests** with the emulator, and smoke tests for the exporters (`lessonPlanDocx`, `schemePdf`, …) | Rules are the real security surface (see `docs/analysis/FINAL ANALYSIS.md`). The **Word** exporters are no longer untested — `src/lib/docxExport.test.js` unzips the generated `.docx` and checks the parts Word obeys (styles resolve, fonts declared, A4, footer present); the PDF/PPTX exporters and the emulator half of this item remain open. `src/lib` helpers, `buildTree`, the `public/curriculum` bundle contracts **and the rules invariants** are now covered by `yarn test` — but those are static: they prove a guard was not deleted, not that a permission decision is right. Only the emulator can do that | M |
| P2-3 | **Bundle strategy**: chunk the 39.7 MB bundle per grade+subject and key the service-worker cache off a content hash (or automate the `CACHE_VERSION` bump) | `b9_schedules.json` alone is 4.85 MB; today a rebuilt bundle reaches returning users only after a manual `sw.js` edit | M |
| P2-4 | **Pagination** for the capped lists (`useCollection` max 100, `QuestionBank` 200, `Search` 100 per collection) with `startAfter` cursors | Silent truncation is indistinguishable from "no more data" | M |
| P2-5 | **Slides**: browse + PPTX export exist; there is no authoring form and no deck-view page | Half-built feature; either finish the authoring flow or remove the affordance (see `docs/gotchas.md`) | M |
| P2-7 | **Rework note/plan visibility into queries** — `visibility` and note `status` are saved but cannot gate reads while the list pages query un-filtered (gotchas.md). To bring back private drafts, split each list into "mine" (`where authorId == uid`) and "published" (`where status/visibility == …`), then re-add the field conditions to the rules | Restores per-document privacy without breaking list queries | M |
| P2-6 | **Repo hygiene**: decide whether the 38 MB curriculum bundle stays in git (or moves to a release artefact) | Keeps clones and diffs manageable. **Partly done**: the 4 tracked `.pyc` files were untracked on 2026-09-18 (`.gitignore` already covered the pattern — they predated it, and gitignore never applies to already-tracked files). The bundle question is open | S |

## P3 — product bets, once the P0s are done

| # | Item | Notes |
|---|------|-------|
| P3-1 | **Publish the B1 Mathematics pilot books** and roll the generator out subject by subject | `make book-skeleton SUBJECT=mathematics GRADE=B1` works; `books/` is gitignored (regenerable, never overwritten) |
| P3-2 | **Offline packs** — per subject/class downloads for schools without reliable connectivity | Needs P2-3 first |
| P3-3 | **Store generated documents, not just metadata** — history has no re-download because nothing writes to Storage | Needs a `storage.rules` (see the paid-delivery work in `docs/deliveries-roadmap.md`) |
| P3-4 | **Visualisation engine** — 3–5 interactive models on one subject-grade as a pilot, not 50 | Needs P2-3 to be realistic in classrooms |
| P3-5 | **Study-notes export** (PDF/DOCX) | Notes are network-only today; the code bible lists exactly how to add an exporter |

---

## Deferred by decision

| Item | Why not | Revisit when |
|---|---|---|
| **Server-side hard gate** for paid downloads (moves final generation server-side so a clean file cannot exist before approval) | Needs Cloud Functions; Spark plan does not allow them | Agents are selling consistently, or bypassing the soft gate becomes a real risk |
| **Mobile Money automation** (gateway webhook → `paid`) | Same infrastructure blocker; manual "Mark as paid" collects MoMo today at ₵0 | Volume makes the manual loop a bottleneck |
| **Ad-hoc quiz/question-paper delivery** | They are generated from a selection with no stored doc, so the approve/regenerate flow has nothing to re-render; persist the artefact first | P1-5 gives the bank content worth gating |
| Building the Studio as a separate web app | One author; `scripts/` + git already is the Studio | A second content author joins |
| Selling printed books as the primary channel | The owner is replacing the consortium print model with a self-serve portal | — |
| Porting the Python generators to JavaScript | They work; the browser needs the *same content model*, not the same language | The pipeline becomes a runtime dependency |
| Regenerating the 73 books before every demo | The CI workflow exists, but does not build books yet: if the books matter, build them in the pipeline, not by hand | — |

---

## Numbers referenced by this file

All from `make audit` (`data/inventory.json`). If an item above disagrees with the
inventory, the inventory is right and the item is stale — fix the item.
