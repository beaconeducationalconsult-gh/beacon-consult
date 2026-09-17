---
inclusion: always
---

# NCOS Project Context

## What This Is

NCOS (NaCCA Curriculum Operating System) is a web app built by Beacon
Educational Consult. It generates curriculum-mapped teaching materials
(lesson plans, schemes of work, records of work) for Ghanaian basic
schools KG1–B9, based on the official NaCCA Standards-Based Curriculum.

## Hosting

- **Frontend**: Vercel (React 19 + Vite)
- **Database**: Firestore
- **Auth**: Firebase Auth
- **File storage**: Firebase Storage
- **No server. No backend process. No Docker.**

Document generation is **client-side only**, using the `docx` npm package
in the browser. The Python `ncos/` package is a reference spec and data
pipeline host — it is never deployed.

## Repository Layout

```
app/          React portal — deploys to Vercel (currently empty, scaffold next)
ncos/         Python reference spec — kernel interface + math module (never deployed)
scripts/      Offline data pipeline — runs locally, never deployed
  ingest/     Parse NaCCA PDFs
  build/      Build curriculum databases + Word documents
    lessons/  Per-grade lesson generators
  audit/      Cross-check data against source PDFs
  backfill/   Inject missing metadata
  inspect/    Debugging helpers
data/         Curriculum source of truth (148 JSON DBs, 73 lesson files, 13,140 lessons)
docs/         All documentation
deploy/       Archived Flask/Docker service — NOT used, kept for reference only
tools/        ncosctl.py CLI
```

## Tech Stack

| Layer | Technology |
|---|---|
| App framework | React 19 + Vite |
| Styling | Tailwind CSS v4 |
| Document generation | docx npm package (client-side) |
| Database | Firestore |
| Auth | Firebase Auth |
| File storage | Firebase Storage |
| Hosting | Vercel |
| Data pipeline | Python 3.11+ (local only) |
| Python doc gen | python-docx (local scripts only) |

## Key Data Facts

- 13 subjects: Mathematics, English, Science, Social Studies, RME,
  Creative Arts, Ghanaian Language, History, French, Computing,
  Career Technology, Creative Arts & Design, OWOP
- Grades: KG1–B9 (Basic 1–9)
- 148 curriculum JSON databases in `data/curriculum/`
- 73 enriched lesson JSON files in `data/lessons/`
- 13,140 daily lesson records total
- 4,040+ NaCCA indicators

## Architecture Principles

1. **No server** — all generation is client-side in the browser
2. **Content separated from rendering** — subject modules produce
   `MaterialDoc` (typed blocks), never `.docx`. Only the driver renders.
3. **Python as spec, JS as runtime** — `ncos/kernel/interface.py` defines
   the shapes; `app/src/kernel/` mirrors them in TypeScript
4. **Fail-loud-at-boot** — broken modules are excluded at startup,
   visible on the boot report, never silently wrong
5. **Offline-first** — `app/public/curriculum/` is a pre-built static
   JSON bundle; indicator browsing + generation works without network

## What's Built vs Not Built

**Built:**
- Python kernel (`ncos/kernel/`) — interface, registry, math module
- Full curriculum data asset (`data/`) — complete and audited
- Data pipeline scripts (`scripts/`) — parsers, generators, audit, backfill
- Documentation (`docs/`)

**Not yet built:**
- React app (`app/` is empty)
- JS kernel + modules (`app/src/kernel/`, `app/src/modules/`)
- docx.js driver (`app/src/drivers/`)
- Firebase services layer (`app/src/services/`)
- 12 remaining subject modules (only math/B4 done in Python)
- Firestore upload script (`scripts/upload_to_firestore.py`)
- Firebase Storage rules (`app/storage.rules`)
- Question bank

## Coding Conventions

- TypeScript for all `app/src/` code
- Functional React components, no class components
- Firestore collection naming: `schools`, `users`, `generated_materials`
- Indicator code format: `B{grade}.{strand}.{substrand}.{standard}.{indicator}`
  e.g. `B4.1.1.1.1`
- Grade naming: `B1`–`B9` (Basic 1–9), `KG1`, `KG2`
- Subject IDs (slug form): `math`, `english`, `science`, `social-studies`,
  `rme`, `creative-arts`, `ghanaian-language`, `history`, `french`,
  `computing`, `career-technology`, `creative-arts-design`, `owop`
