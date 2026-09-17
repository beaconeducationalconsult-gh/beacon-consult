# Beacon Educational Consult

Curriculum-mapped teaching materials for Ghanaian basic schools (KG1–B9),
built from the official NaCCA curriculum and delivered as generated Word
documents.

## Layout

```
app/          React portal — teachers sign in and generate documents
service/      Material Service (Flask) — runs python-docx on behalf of the browser
data/         the curriculum asset (JSON, source PDFs, extracted text)
tools/        every Python script: parsers, generators, audits
docs/         architecture, service and curriculum documentation
sales/        catalogue and one-pager
marketing/    video script
```

## The asset

| | |
|---|---|
| Lesson plans | 13,140 (73 subject-grade books) |
| Indicators served | 4,040 across 11 grades |
| Subjects | 13 |
| Grades | KG1, KG2, B1–B9 |
| Source | 24 official NaCCA curriculum PDFs |

## Running the portal

Two processes. The portal cannot build `.docx` files in the browser, so the
Material Service does it.

```bash
# 1. Material Service (port 8080)
pip install -r service/requirements.txt
python service/main.py

# 2. Portal (port 5173)
cd app
yarn install
yarn curriculum     # builds app/public/curriculum from data/ (required, gitignored)
yarn dev
```

`yarn curriculum` must run before `yarn dev` — the generated curriculum
bundle is gitignored because it is 38 MB and rebuildable from `data/`.

## Regenerating materials

```bash
python tools/generate_schemes.py --grade B4 --subject math --out dist/schemes
python tools/generate_records_of_work.py --grade B6 --subject science --out dist/records
python tools/build_app_curriculum.py      # rebuilds the app's curriculum bundle
```

## Where data lives

`tools/_paths.py` is the single source of truth. Import from it rather than
hard-coding paths:

```python
from _paths import CURRICULUM, LESSONS, SOURCES, find_data
```

Legacy one-shot scripts open data by bare filename and carry a small
preamble that routes those through `tools/_compat.py`. They now work from
any directory.

> **Note:** curriculum databases exist in both `data/curriculum/` (primary)
> and `data/reference/` (a second, partly-divergent copy formerly at
> `app/data/`). `DB_SEARCH` checks the primary first. See
> `docs/ARCHITECTURE.md` §6.

## Documentation

- `docs/ARCHITECTURE.md` — data model (ER diagrams), pipeline, verification
- `docs/APP_CURRICULUM.md` — how the app's curriculum bundle is built
- `docs/SCHEMES_OF_LEARNING.md`, `docs/RECORDS_OF_WORK.md`
- `docs/MATERIAL_SERVICE.md` — the service API
- `TODO.md` — what is next
