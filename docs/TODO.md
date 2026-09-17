# Project TODO

Restructured 2026-09-17 against the dataset as it actually is. The previous version
ordered work by aspiration and referenced documents that do not exist; this one is
ordered by **dependency** and every item names the dataset layer it unblocks.

> **Anchor:** the portal must produce at least what the books produce. Everything
> below is scored against that. Selling the printed inventory is a business action,
> not an engineering task, so it is no longer item #1 here.

**Verify state at any time with:**

```bash
make inventory             # dataset vs app agreement -> data/inventory.json
make validate-curriculum   # bundle invariants the UI relies on
```

---

## P0 — the portal cannot ship in its current state

| # | Item | Why | Layer | Size |
|---|------|-----|-------|------|
| P0-1 | **Fix the 36 TypeScript errors so `npm run build` passes** — 27 unused-param stubs, `DocType`/`recordGeneration` union mismatch, untyped Firestore results in Dashboard/History, two impossible `'question_bank'` comparisons | The app cannot deploy at all. `npm run dev` hides this because Vite does not type-check | app | S |
| P0-2 | **Make every module's `validate()` real** — check that its id exists in the bundle, that its declared grades have indicators, and that declared capabilities have backing data | All 13 modules currently `return []`, so boot is always green and cannot catch anything. This is what let P0-3 through | app | S |
| P0-3 | **Rename the math module id `math` → `mathematics`** (or add an alias in one place) | It matches zero indicators: empty lesson-plan dropdown, zero-row scheme, and a Record of Work that downloads a file with an empty table | app | S |
| P0-4 | **Fix the history read/write key mismatch** — writes use `users/{uid}.schoolId`, reads use `(user as any).schoolId ?? user.uid` | Generation history and the dashboard counters can never display | app | S |
| P0-5 | **Add a CI workflow** running `tsc -b`, `oxlint`, `validate_app_curriculum.py`, `build_inventory.py` | Nothing prevents P0-1..P0-4 from returning. One 20-line workflow file | repo | S |

## P1 — close the gap between the bundle and the books

| # | Item | Why | Layer | Size |
|---|------|-----|-------|------|
| P1-1 | **Generate lesson plans from L2, not from the indicator row** — emit Starter / Main / Plenary / Assessment / Competencies / Resources / RP Knowledge for the slot | This is the whole product value. Today `generateLessonPlan` emits four sections and ignores all 13,140 authored slots | app + pipeline | M |
| P1-2 | **Populate `extra` in the bundle, or delete the callout** — every lesson plan currently prints `Sub-skill: n/a` because `extra` is empty for all 4,040 indicators | A document that looks broken is worse than a shorter document | pipeline | S |
| P1-3 | **Fix or gate the Question Bank** — `/curriculum/questions/math/<grade>.json` does not exist; the module returns an empty document and calls it success | Silent failure that looks like a feature. Gate on `capabilities` **and** on the file existing | app + pipeline | S |
| P1-4 | **Chunk the bundle per grade+subject** (~50 KB per file instead of 3–5 MB per grade) and key the service-worker cache off a content hash | 39.7 MB committed; `b9_schedules.json` is 4.85 MB; the PWA caches `CacheFirst` for 30 days with no invalidation, so a rebuilt bundle never reaches returning users | pipeline + app | M |
| P1-5 | **Rule and config hygiene**: add `schoolId` to the `generated_materials` create rule, write `app/storage.rules`, add `firebase.json` that actually deploys the rules and indexes, replace the cargo-culted `firestore.indexes.json` (it indexes `posts`, `vacancies`, `notes`… collections that do not exist) | Create currently lets any user attribute records to another school; indexes are aspirational because nothing deploys them | app | S |
| P1-6 | **Add `.env.example` + `src/vite-env.d.ts`**, and fail fast when `VITE_FIREBASE_*` is missing | `initializeApp` accepts `undefined` values silently and fails later at the first Firestore call | app | S |
| P1-7 | **Real onboarding**: first sign-in writes `schools/{id}` and `users/{uid}` | No code creates either document today, so a new teacher's history can never be read by the rules and there is no self-serve path | app | M |

## L1/L2 — dataset work the app depends on

| # | Item | Why | Layer | Size |
|---|------|-----|-------|------|
| L1-1 | **Decide the fate of `data/reference/`** — either audit and promote the 8 reference-only subject-grades (computing B4–B6, french B4–B6, KG1–KG2) into `data/curriculum/`, or delete the copy and make missing files a loud failure | A silent fallback means the app can serve unaudited curriculum and nobody notices divergence | data | M |
| L1-2 | **Fill the L1 gaps**: `english-language B4`, `mathematics B1`, `science B1` have databases but no summary (no source URL / counts); `english-language B5` has a summary but no database | Unverifiable provenance on 184 indicators | data | S |
| L1-3 | **Repair the 8 malformed summaries in `data/reference/`** (no `counts` block) | Any code that reads `summary["counts"]` raises on them | data | S |
| L1-4 | **Stop treating per-subject-grade constants as per-indicator enrichment** — `competencies`, `resources`, `keywords`, `assessment` have exactly one distinct value per subject-grade | Documents that print "Resources: NaCCA approved textbook; TLMs; ICT tools" under every indicator look templated because they are | data + app | S |
| L2-1 | **Clean the 58 `ind_desc` records with a repeated trailing sentence** (0.4% of slots) at the extraction source | Visible artefact in generated documents | data | S |
| L2-2 | **Decide whether L2 is a template or authored content, and say so** — measured fidelity: `starter` 75%, `main` 41%, but `rpk`/`plenary`/`assessment` ≈ 1% (one value per subject-grade) | Marketing, authoring budget and generation strategy all depend on this; see `docs/DATA_MODEL.md` | product | S |

## P2 — structural debt that makes every future fix expensive

| # | Item | Why | Size |
|---|------|-----|------|
| P2-1 | **Collapse the 13 subject modules into a factory + a subject descriptor table** — any two non-math modules differ by 20–22 of 128 lines | Every fix today costs 13 edits; this is why P0-2/P1-2 exist | M |
| P2-2 | **Collapse the 8 `build_math_b{2..9}_word_document.py` (324 lines each) into one `--grade` script**, and the 16 per-grade backfills into one parameterised script | ~2,600 lines that differ only in grade strings | M |
| P2-3 | **Reconcile the Python spec with the TS runtime** (`ncos/kernel/interface.py` is sync and manifest-driven; `app/src/kernel/` is async and class-driven), and add an `interface_version` check on the JS side | Principle #3 in `README.md` is currently untrue, and nothing detects further drift | M |
| P2-4 | **Repo hygiene**: delete the 4 tracked `.pyc` files, add a root `.gitignore`, stop committing the 39.7 MB bundle (or move it to a release artefact) | 132 MB of tracked data and generated output in one squashed commit | S |
| P2-5 | **Tests and a lint gate** — no pytest, no vitest, no CI. Start with one unit test per module `validate()` and one snapshot test of `MaterialDoc → .docx` for a known indicator | There is currently nothing between a pipeline change and a school downloading a wrong document | M |
| P2-6 | **Delete or banner the historical docs** (`FULL_README.md`, `DEVELOPMENT_GUIDE.md`, `APP_BUILD_PLAN.md`, `REPO_ANALYSIS_REPORT.md`) — they describe `tools/` paths and an empty `app/` that no longer exist | See the status column in `README.md` | S |

## P3 — product bets, once the portal renders what the books render

| # | Item | Notes |
|---|------|-------|
| P3-1 | **Visualisation engine** — 3–5 interactive models on one subject-grade as a pilot, not 50 | Needs chunked/offline data (P1-4) first |
| P3-2 | **Offline packs** — per subject/class downloads for schools without reliable connectivity | Requires P1-4; prerequisite for P3-1 being realistic in classrooms |
| P3-3 | **Store generated documents, not just metadata** — history has no re-download because nothing writes to Storage | Depends on P1-5 (`storage.rules`) |
| P3-4 | **Question bank** — zero questions exist in the bundle; `data/questions/` has one mathematics B4 file | Highest-value content the dataset lacks |
| P3-5 | **Student/teacher portal features** — classrooms, pupil access codes, printable login cards | Scope beyond the current portal; decide before building |

---

## Deferred by decision

| Item | Why not |
|---|---|
| Building the Studio as a separate web app | One author; `scripts/` + git already is the Studio. Revisit when a second content author joins |
| Selling printed books as the primary channel | The owner intends to replace the consortium print model with a self-serve portal |
| Porting the Python generators to JavaScript | They work; the browser needs the *same content model*, not the same language |
| Regenerating the 73 books before every demo | Superseded by CI (P0-5): if the books matter, build them in the pipeline, not by hand |

---

## Numbers referenced by this file

All from `make inventory` (`data/inventory.json`). If an item above disagrees with
the inventory, the inventory is right and the item is stale — fix the item.
