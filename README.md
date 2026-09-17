# NCOS — NaCCA Curriculum Operating System

Curriculum-mapped teaching materials for Ghanaian basic schools (KG1–B9),
generated from the official NaCCA Standards-Based Curriculum.

**Hosted on Vercel (React app) + Firebase (Firestore + Auth + Storage).**
There is no server to run or deploy — document generation happens entirely
in the browser using the `docx` npm package.

---

## Repository Layout

```
ncos-starter/
│
├── app/                     React + Vite portal (deploys to Vercel)
│   ├── src/
│   │   ├── kernel/          JS document model — MaterialDoc, Block types
│   │   ├── modules/         One folder per subject (JS equivalents of ncos/modules/)
│   │   ├── drivers/         docx.js renderer — turns a MaterialDoc into a .docx download
│   │   ├── services/        Firestore reads, Firebase Auth, Storage uploads
│   │   └── ui/              React components, pages, layout
│   ├── public/
│   │   └── curriculum/      Static JSON bundle (built by `make build-curriculum`)
│   └── package.json
│
├── ncos/                    Python data model — reference implementations
│   ├── kernel/
│   │   ├── interface.py     SubjectModule contract, Indicator, MaterialDoc, Block types
│   │   └── registry.py      Boot sequence — discovers and validates subject modules
│   └── modules/
│       ├── _template/       Copy-paste scaffold for new subject modules
│       └── math/            Reference implementation (B4 Mathematics)
│
├── scripts/                 Offline data pipeline — runs locally, never deployed
│   ├── ingest/              Parse NaCCA source PDFs → raw indicator records
│   ├── build/               Build curriculum databases + Word documents
│   │   └── lessons/         Per-grade lesson plan generators
│   ├── audit/               Cross-check extracted data against source PDFs
│   ├── backfill/            Inject missing metadata fields into lesson records
│   ├── inspect/             Debugging and inspection helpers
│   ├── generate_schemes.py          Generate Scheme of Learning .docx files
│   ├── generate_records_of_work.py  Generate Record of Work .docx files
│   ├── build_app_curriculum.py      Build app/public/curriculum/ JSON bundle
│   ├── validate_app_curriculum.py   Validate that bundle
│   ├── package_books.py             Zip finished books for distribution
│   ├── _paths.py            Single source of truth for all data/ paths
│   └── _compat.py           Legacy open() shim for older scripts
│
├── data/                    Curriculum asset — source of truth, never deployed directly
│   ├── curriculum/          148 JSON databases: *_curriculum_db_clean.json
│   ├── lessons/             73 JSON files: *_lessons_enriched.json (13,140 lessons)
│   ├── indicators/          Per-grade indicator grouping files
│   └── audit/               Audit results and fix logs
│
├── docs/                    All project documentation
│   ├── ARCHITECTURE.md      System design and the OS metaphor explained
│   ├── DEVELOPMENT_GUIDE.md Staged build roadmap (11 stages)
│   ├── SUBJECT_MODULES.md   Subject module interface specification
│   ├── TODO.md              Live task backlog
│   ├── OPPORTUNITY_MAP.md   Business analysis and go-to-market
│   └── assets/              Architecture diagrams
│
├── deploy/                  Archived Flask/Docker service (not used — kept for reference)
│
├── tools/
│   └── ncosctl.py           CLI: boot-check, list-modules, generate-sample
│
├── Makefile                 Pipeline shortcuts (see below)
└── requirements.txt         Python deps for scripts/ only (python-docx, firebase-admin)
```

---

## The Architecture in One Sentence

The curriculum data lives in `data/`, gets transformed into Firestore and
`app/public/curriculum/` by `scripts/`, and the React app in `app/` lets
teachers browse it and generate `.docx` documents **entirely in the
browser** — no backend, no server, no Docker.

```
data/curriculum/  ──[scripts/build_app_curriculum.py]──►  app/public/curriculum/
                  ──[scripts/upload_to_firestore.py]────►  Firestore
                                                                │
                                                         app/ reads Firestore
                                                         app/ uses docx.js
                                                                │
                                                         Teacher downloads .docx
```

---

## Getting Started

Requires Python 3.11+ and Node 20+.

```bash
git clone <this-repo> && cd ncos-starter

# Python env (for data pipeline scripts only)
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt

# React app
cd app && npm install
```

---

## Data Pipeline (scripts/)

Run these locally to rebuild the curriculum bundles after any data change.

```bash
# Check the Python kernel is healthy (module validation)
make boot-check

# Rebuild app/public/curriculum/ static JSON for the React app
make build-curriculum

# Validate the bundle
make validate-curriculum

# Generate Word documents locally (output goes to dist/)
make generate-schemes
make generate-records
make package-books
```

---

## React App (app/)

```bash
cd app
npm run dev      # http://localhost:5173
npm run build    # production build → dist/
```

The app deploys automatically to Vercel on push to `main`.

---

## Adding a New Subject Module

The Python module in `ncos/modules/` serves as the **reference spec** for
what the equivalent JavaScript module in `app/src/modules/` must do.

1. Copy `ncos/modules/_template/` → `ncos/modules/<subject_id>/`
2. Fill in `module.json` and implement `module.py` (Python spec)
3. Mirror the logic in `app/src/modules/<subject_id>/` (JavaScript runtime)
4. Add curriculum data under `data/curriculum/<subject_id>/<grade>.json`
5. Run `make boot-check` and `make build-curriculum`

See `docs/SUBJECT_MODULES.md` for the full interface contract.

---

## What's Not Built Yet

| Item | Where it goes |
|---|---|
| React portal UI | `app/src/` — empty, ready to scaffold |
| 12 remaining subject modules | `ncos/modules/` + `app/src/modules/` |
| Firestore upload script | `scripts/upload_to_firestore.py` |
| Firebase Storage rules | `app/storage.rules` |
| Firebase Auth integration | `app/src/services/auth.ts` |
| Question bank | `data/questions/` + module `generate_questions()` |

See `docs/TODO.md` for the full live task list.
