---
inclusion: always
---

# NCOS Project Context

## What this is

NCOS (NaCCA Curriculum Operating System) is built by Beacon Educational Consult.
It produces curriculum-mapped teaching materials for Ghanaian basic schools KG1–B9
from the official NaCCA Standards-Based Curriculum, in two forms:

* **books** — Word documents generated offline by `scripts/` (the sellable artefacts)
* **portal** — a React app in `app/` that browses the curriculum and generates the
  same materials in the browser (Vercel + Firebase)

**Current state, in one line:** the data is good, the portal is not shippable.
`app/` does not compile (36 TypeScript errors), every module's `validate()` is a
stub, the math module's id matches zero indicators, and generated lesson plans are
a four-section skeleton that ignores the 13,140 authored lesson slots.
Read `docs/CODE_REVIEW.md` before making claims about what works.

## The dataset — three layers, three different totals

Never say "the dataset has N indicators" without naming the layer. Full definition
in `docs/DATA_MODEL.md`; regenerate the numbers with `make inventory`
(→ `data/inventory.json`).

| Layer | Path | Contents |
|---|---|---|
| L1 curriculum | `data/curriculum/` | 75 DBs · 73 summaries · **3,095 indicators** (audited) |
| L2 lessons | `data/lessons/` | **13,140 lesson slots** — 3 terms × 12 weeks × 5 days × 73 subject-grades, 13 subjects, B1–B9 |
| L3 bundle | `app/public/curriculum/` | **4,040 indicators** across 84 subject-grades / 11 grades (39.7 MB) — what the app serves |

`data/reference/` is a **second, partly-divergent copy** that `scripts/_paths.py`
searches as a silent fallback. It supplies 8 L3 subject-grades that L1 does not have
(computing B4–B6, french B4–B6, kindergarten KG1–KG2). It is never a total — only a
fallback, and an open decision (TODO L1-1).

Measured fidelity of L2: `starter` 75% distinct, `main` 41%, `rpk`/`plenary`/
`assessment` ≈ 1% (one value per subject-grade). It is a **filled template**, not
13,140 hand-written plans. Say so.

## Hard rules

1. **Subject ids come from the dataset.** Canonical ids are `mathematics`,
   `english-language`, `ghanaian-language`, `creative-arts`, `creative-arts-design`,
   `career-technology`, `social-studies`, `science`, `rme`, `history`, `french`,
   `computing`, `owop`, `kindergarten`. `math` is wrong — it is why
   `MathModule` matches nothing today.
2. **Grades are `KG1`–`KG2`, `B1`–`B9`.** Kindergarten indicator codes on disk say
   `K1`/`K2`; normalise to `KG1`/`KG2`.
3. **Indicator codes are the join key**: `B<grade>.<strand>.<substrand>.<standard>.<indicator>`,
   e.g. `B4.1.1.1.1`.
4. **Content is separated from rendering.** A subject module returns a `MaterialDoc`
   (typed blocks); only a driver renders `.docx`. Never import `docx` into a module.
5. **Fail loud.** A module that cannot serve a declared grade or capability must be
   excluded at boot and reported. An empty document is never an acceptable success.
   If you touch a module, replace its `validate()` stub with real checks.
6. **The portal must render at least what the books render.** A generated lesson
   plan containing less than the book for the same indicator is a bug.
7. **Never hand-type numbers into docs.** Run `make inventory` and quote it.
8. **`data/` is source; `app/public/curriculum/` is generated.** Do not hand-edit the
   bundle; change `scripts/build_app_curriculum.py` and rebuild.

## Layout

```
app/            React 19 + Vite + Tailwind v4 portal (Vercel)
  src/kernel/     MaterialDoc/Block types + module registry (mirrors ncos/kernel)
  src/modules/    13 subject modules
  src/drivers/    docx renderer (client-side `docx` npm package)
  src/services/   Firestore, Auth, Storage, React hooks
ncos/           Python reference spec (never deployed) — has drifted from app/src/kernel
scripts/        offline pipeline: build/, audit/, backfill/, inspect/, ingest/
data/           the dataset (L1, L2, sources, audit, questions, reference)
docs/           DATA_MODEL.md, CODE_REVIEW.md, TODO.md are current; the rest are historical
deploy/         archived Flask service — not deployed; `tools/ncosctl.py` is currently broken
```

## Commands

```bash
make inventory             # derive + check the numbers (fast, read-only)
make validate-curriculum   # bundle invariants the UI depends on
make build-curriculum      # rebuild app/public/curriculum/
make generate-schemes      # Word output -> dist/  (dist/ and the books are NOT committed)
cd app && npm run dev      # the only way the app currently runs (dev skips type-checking)
cd app && npm run build    # FAILS today — 36 TS errors; this is P0-1 in docs/TODO.md
```

Use **npm** (`package-lock.json` is the lockfile). Older docs saying `yarn` or
`tools/` are wrong: the pipeline lives in `scripts/`.

## Priority

`app/` must first compile (P0-1..P0-5 in `docs/TODO.md`), then render L2 content
(P1-1..P1-2). Those two steps are the difference between a demo and a product.
