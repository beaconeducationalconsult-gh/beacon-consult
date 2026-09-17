# NCOS — NaCCA Curriculum Operating System

Curriculum-mapped teaching materials for Ghanaian basic schools (KG1–B9): lesson
plans, schemes of learning and records of work, built from the official NaCCA
Standards-Based Curriculum.

Two products share one dataset:

* **The books** — generated offline as Word documents (`scripts/`), the finished,
  sellable artefacts.
* **The portal** — a React app (`app/`) that browses the curriculum and generates
  the same materials in the browser, deployed to Vercel with Firebase for auth and
  history.

> **Read `docs/CODE_REVIEW.md` before trusting anything in this repository.**
> The app currently does not compile, the documented kernel CLI does not run, and
> the portal generates a four-section skeleton that is much thinner than the books.
> The data is in good shape; the software around it is not yet.

---

## The dataset (three layers — do not conflate them)

Produced by `make inventory` → `data/inventory.json`. Full definition in
`docs/DATA_MODEL.md`.

| Layer | Path | Contents |
|---|---|---|
| **L1 curriculum** | `data/curriculum/` | 75 databases · 73 summaries · **3,095 indicators** · audited against 24 NaCCA source PDFs |
| **L2 lessons** | `data/lessons/` | **13,140 lesson slots** (73 files, 13 subjects, B1–B9) with a filled teaching template |
| **L3 bundle** | `app/public/curriculum/` | **4,040 indicators** across 84 subject-grades / 11 grades — what the app serves (39.7 MB) |

L3 is larger than L1 by **945 indicators across 9 subject-grades** (computing B4–B6,
french B4–B6, kindergarten KG1–KG2 come from the unaudited `data/reference/` fallback;
`english-language B5` has an L1 summary but no L1 database). For the other 75
subject-grades the two layers agree exactly. This divergence is tracked, not hidden:
`make inventory` reports it and `docs/DATA_MODEL.md` explains it.

---

## Repository layout

```
app/                     React + Vite portal (Vercel)
  src/kernel/            MaterialDoc / Block types, module registry
  src/modules/           one folder per subject (13 subjects)
  src/drivers/docx.ts    MaterialDoc -> .docx, client-side (docx npm package)
  src/services/          Firestore, Firebase Auth, Storage, React hooks
  public/curriculum/     L3 bundle, committed (rebuilt by make build-curriculum)
  vite.config.ts         PWA + dev server config

ncos/                    Python reference spec for the kernel (never deployed)
  kernel/interface.py    SubjectModule contract, Indicator, MaterialDoc, Block types
  kernel/registry.py     boot sequence: validate modules, exclude failures
  modules/math/          reference implementation (B4 Mathematics)

scripts/                 offline data pipeline — runs locally, never deployed
  build_app_curriculum.py    L1/L2 -> L3 bundle
  build_inventory.py         L1/L2/L3 -> data/inventory.json  (single source of numbers)
  validate_app_curriculum.py invariant checks on the bundle
  generate_schemes.py        Scheme of Learning .docx
  generate_records_of_work.py
  package_books.py           zip finished books for distribution
  ingest/ build/ audit/ backfill/ inspect/   stage-specific one-shot scripts
  _paths.py                where the data lives (single source of truth for paths)

data/                    the dataset itself
  curriculum/            L1: *_curriculum_db_clean.json + *_curriculum_summary.json
  lessons/               L2: *_lessons_enriched.json
  sources/               24 NaCCA source PDFs
  audit/                 audit results and fix logs
  questions/             mathematics B4 only (not yet in the app bundle)
  reference/             second, partly-divergent copy — see docs/DATA_MODEL.md
  inventory.json         generated: the numbers used in this README

docs/                    see the index at the bottom of this file
deploy/                  archived Flask service (not used, not deployed)
tools/ncosctl.py         kernel CLI — currently broken, see docs/CODE_REVIEW.md
```

---

## Getting started

Requires **Python 3.11+** and **Node 20+**. Use `npm` (the repo has
`package-lock.json`; older docs saying `yarn` are wrong).

```bash
# 1. Python environment — for the data pipeline only
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Regenerate the numbers and check dataset/app agreement
make inventory                     # -> data/inventory.json + a report

# 3. The React app
cd app && npm install
npm run dev                        # http://localhost:5173
```

### Known blockers before a demo

`app/` has **no `.env` file**, and `VITE_FIREBASE_*` variables are documented
nowhere. Without them Firebase initialises with `undefined` values and fails
later with an opaque `auth/invalid-api-key`. Create `app/.env.local`:

```
VITE_FIREBASE_API_KEY=…
VITE_FIREBASE_AUTH_DOMAIN=…
VITE_FIREBASE_PROJECT_ID=…
VITE_FIREBASE_STORAGE_BUCKET=…
VITE_FIREBASE_MESSAGING_SENDER_ID=…
VITE_FIREBASE_APP_ID=…
```

Also note **`npm run build` fails today** (36 TypeScript errors) — the portal is
only runnable via `npm run dev`, which does not type-check. `docs/TODO.md` tracks
this as the first blocker.

---

## The pipeline

```bash
make inventory             # derive + check the numbers in this README (fast, no writes to data/)
make validate-curriculum   # enforce the bundle invariants the UI relies on
make build-curriculum      # L1/L2 -> app/public/curriculum/
make generate-schemes      # Word: Scheme of Learning   (output -> dist/)
make generate-records      # Word: Record of Work       (output -> dist/)
make package-books         # zip the finished books for distribution
make boot-check            # kernel module health — BROKEN, see docs/CODE_REVIEW.md
```

The books are **not committed** (`dist/` is gitignored, and the volumes that were
once in `data/books/` are gone). Any claim about "the finished books" has to be
re-established by regenerating them: the inputs exist (13,140 lesson slots), the
generators exist, the outputs do not.

---

## Architecture principles

1. **No server for the portal.** Document generation happens entirely in the browser
   via the `docx` npm package. The Python side is a local pipeline and a reference spec.
2. **Content is separated from rendering.** Subject modules produce a typed
   `MaterialDoc`; only a driver turns that into `.docx`. Adding a document type must
   not require touching subject modules.
3. **Python is the spec, TypeScript is the runtime.** `ncos/kernel/interface.py`
   defines the shapes; `app/src/kernel/` mirrors them. These have already drifted
   (async vs sync, manifest vs class field) — see `docs/CODE_REVIEW.md` §12.
4. **Fail loud at boot.** A module that cannot serve its declared grades must be
   excluded and reported — never silently produce an empty document. Today every
   module's `validate()` returns `[]`, so this principle is not actually enforced.
5. **Offline-first.** The curriculum bundle is static JSON; browsing and generation
   must work without network. The bundle is currently one file per grade (3–5 MB),
   not per subject — chunking is an open task.
6. **The dataset is the source of truth.** Subject ids, grade names and indicator
   codes come from the data, never from hand-typed constants in the app. The
   `math` / `mathematics` mismatch is the cost of ignoring this rule.

---

## Documentation index

| Document | Status |
|---|---|
| `docs/DATA_MODEL.md` | **Current** — the three layers, join keys, ids, invariants |
| `docs/CODE_REVIEW.md` | **Current** — what is broken, with reproductions |
| `docs/TODO.md` | **Current** — restructured backlog, ordered by dependency |
| `docs/SUBJECT_MODULES.md` | Current — module interface specification |
| `docs/ARCHITECTURE.md` | Partly stale — still describes a Flask "Material Service" |
| `docs/OPPORTUNITY_MAP.md` | Current — business analysis and go-to-market |
| `docs/DEVELOPMENT_GUIDE.md` | **Historical** — 11-stage plan from when `app/` was empty |
| `docs/APP_BUILD_PLAN.md` | **Historical** — the plan that produced `app/src/`; keep for reasoning, not for status |
| `docs/FULL_README.md` | **Historical** — pre-restructure; paths (`tools/`, `service/`) no longer exist |
| `docs/REPO_ANALYSIS_REPORT.md` | **Historical** — analyses the pre-restructure repo (describes `saas-files.zip`, then-unbuilt app) |
| `.kiro/steering/project.md` | Agent context — regenerated from the inventory |
