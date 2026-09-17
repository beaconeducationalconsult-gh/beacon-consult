# Repository Analysis — `Lecturer-Sam/staff-common-room`

*Studied 2026-09-11 · branch `arena/01a09129-staff-common-room` @ `c9a186c` ("SaaS Program Files")*

---

## 1. Executive summary

This is **not one project — it's two distinct workstreams that were dumped flat into a single
folder**, plus their raw source materials.

| | Workstream A | Workstream B |
|---|---|---|
| **What** | A Python **curriculum-data factory** that turns NaCCA curriculum PDFs into structured JSON and then into Word lesson-plan books | A React/Vite/Firebase **SaaS web app** ("Beacon Educational Consult") for Ghanaian teachers |
| **Where it lives** | Loose in the repo root (533 files) | Inside `saas-files.zip` (534 files, 17 MB unzipped) |
| **Maturity** | Complete, audited, finished deliverables produced | Feature-rich, documented, deployed (Vercel + Firebase), with a known backlog |
| **Language** | Python (182 scripts), `python-docx` | JavaScript/React (155 JSX + 48 JS), Tailwind 4, Firebase |

The connective tissue: **Workstream A's JSON output is the curriculum database that
Workstream B serves.** The app's `data/` folder is a copy of (part of) the root JSONs.

**Bottom line:** you own a pipeline that has produced **13,140 fully-written daily lesson
plans across Basic 1–9 and 13 subjects**, published as **73 Word documents**, and a
members-only teacher portal that is meant to consume that same curriculum data. The
pipeline is finished and audited; the portal is built but has unclosed gaps (billing,
student analytics, rule deployment discipline).

---

## 2. Inventory at a glance

533 files, **97 MB**, flat — no subdirectories except `.git`. One commit in history.

| Type | Count | Role |
|---|---|---|
| `.json` | 238 | Curriculum DBs, enriched lessons, audit reports |
| `.py` | 182 | Extraction / enrichment / generation / audit scripts |
| `.docx` | 73 | **The deliverables** — full-year lesson plan books |
| `.pdf` | 24 | **The sources** — official NaCCA curriculum documents |
| `.txt` | 11 | Intermediate raw text extracted from the PDFs |
| `.zip` | 1 | `saas-files.zip` — the entire web application |

### 2.1 Source PDFs (24) — official NaCCA curriculum
Grouped by band, matching Ghana's new Standards-Based Curriculum structure:

- **Lower primary B1–B3:** `math_B1-B3`, `science_B1-B3`, `english_B1-B3`, `gh_lang_b1b3`, `creative_arts_B1-B3`, `owop_B1-B3`
- **Upper primary B4–B6:** `mathematics_B4-B6`, `science_B4-B6`, `english_B4-B6`, `ghanaian_language_B4-B6`, `creative_arts_B4-B6`, `owop_B4-B6`
- **Across B1–B6:** `history.pdf`, `rme_B1-B6.pdf`
- **JHS / Common Core Programme B7–B9 (drafts):** `mathematics_CCP_B7-B9_draft`, `science_CCP`, `english_CCP`, `ghanaian_language_CCP`, `rme_CCP`, `social_studies_CCP`, `career_tech_CCP`, `computing_CCP`, `creative_arts_design_CCP`, `french_CCP`

### 2.2 Deliverables (73 DOCX)
`Basic{1-9}_{Subject}_Lesson_Plans_Full_Year.docx`

| Grade | Subjects | Count |
|---|---|---|
| B1 | Creative Arts, English, Ghanaian Language, History, Mathematics, OWOP, RME, Science | 8 |
| B2–B6 | Creative Arts, English, Ghanaian Language, History, Mathematics, RME, Science | 7 each = 35 |
| B7–B9 | Career Technology, Computing, Creative Arts & Design, English, French, Ghanaian Language, Mathematics, RME, Science, Social Studies | 10 each = 30 |

**73 subject-grade combinations = 73 files.**

Each book: a title page, then **180 numbered daily lesson plans** (36 weeks × 5 days,
3 terms × 60). Every plan follows the national GES/NaCCA template:

> Header (week ending, day/date, class, class size, duration, references) →
> Strand / Sub-strand / **Content Standard** (e.g. `B4.1.1.1`) / **Indicator** (`B4.1.1.1.1`) →
> Performance indicator → Core Competencies → Keywords → T/L Resources →
> Relevant Previous Knowledge (RPK) →
> **Three-phase structure**: PHASE 1 Starter (5 min) / PHASE 2 Main (20 min) / PHASE 3 Plenary (5 min) →
> Assessment → **Teacher's Reflection block** → Teacher signature / HoD vetting lines.

---

## 3. Workstream A — the curriculum-data factory

### 3.1 Pipeline (four stages, visible in the file names)

```
  24 NaCCA PDFs
       │  extract_*.py, parse_*.py, print_page*.py  (scratch/forensic PDF readers)
       ▼
  11 raw .txt dumps            (creative_arts_raw.txt, math_raw_text.txt, rme_raw.txt, …)
       │  build_clean_curriculum_db.py, build_clean_math_curriculum_db.py
       │  extract_curriculum_database.py, extract_unique_indicators.py
       ▼
  75 × *_curriculum_db_clean.json   ← 3,095 indicators, keyed by code
  73 × *_curriculum_summary.json    ← per-subject strand/sub-strand/standard/indicator tallies
       │  backfill_b{2..9}_metadata.py / _remaining3 / _remaining6
       │     (inject authentic NaCCA text: competencies, resources, keywords, assessment)
       │  generate_b{1..9}_core4.py / _remaining3.py / _remaining6.py
       ▼
  73 × *_lessons_enriched.json      ← 13,140 lesson records (73 × 180)
       │  build_*_word_document.py  (one per subject-grade)
       ▼
  73 × .docx
```

### 3.2 The curriculum database

`*_curriculum_db_clean.json` is a **flat dict keyed by indicator code**, e.g.:

```json
"B4.1.1.1.1": {
  "cs_code": "B4.1.1.1",
  "cs_desc": "Demonstrate an understanding of quantities and place value for
              multi-digit whole numerals up to 100,000.",
  "ind_desc": "Model number quantities, place value for multi-digit using graph
               sheets or multi-base materials up to 100,000",
  "competencies": "Critical Thinking and Problem Solving; Communication and
                   Collaboration; Creativity and Innovation; …",
  "resources": "NaCCA approved textbook; TLMs; ICT tools; community resources",
  "keywords": "mathematics, b4, upper-primary",
  "assessment": "Class exercises; oral questions; practical performance; SBA"
}
```

Coding follows the NaCCA convention `B{grade}.{strand}.{substrand}.{standard}.{indicator}`.

**Indicator counts by grade:** B1 287 · B2 249 · B3 276 · B4 402 · B5 286 · B6 385 ·
B7 454 · B8 379 · B9 377 — **3,095 total.**

By subject: English 557, Ghanaian Language 512, Mathematics 407, Science 281,
Creative Arts 223, French 166, RME 136, Career Technology 132, Computing 123,
Creative Arts & Design 100, OWOP 74, Social Studies 54, History 43.

### 3.3 The enriched lesson record

One flat record per teaching session (180 per subject-grade):

```json
{
  "lesson_num": 1, "term": 1, "week": 1, "day": "Monday",
  "strand_num": 1, "strand_name": "1. NUMBER", "sub_strand": "Sub-strand B4.1.1",
  "cs_code": "B4.1.1.1", "cs_desc": "…", "ind_code": "B4.1.1.1.1", "ind_desc": "…",
  "is_revision": false, "session_title": "Session 1 of 3 — Introduction",
  "perf_indicator": "By the end of the lesson, learners will be able to: …",
  "competencies": "…", "resources": "…", "keywords": "…", "rpk": "…",
  "starter": ["…", "…", "…", "…"],
  "main":    ["ACTIVITY 1 (Concrete – 5 min): …", "ACTIVITY 2 (Guided – 5 min): …", …],
  "plenary": ["…", "…", "…", "…"],
  "assessment": "…"
}
```

The generator scripts (`generate_b4_core4.py` etc.) encode real pedagogical logic, not just
templating: per-subject **weekly strand rotation** (e.g. B4 Maths: Mon→Number, Tue→Algebra,
Wed→Geometry, Thu→Data, Fri→Number, giving Number two periods/week), **spiral session
naming** (Session 1 "Introduction" → middle "Practice" → last "Consolidation"), and
**special-cased period types** — English and Ghanaian Language have a dedicated weekly
*Extensive Reading* slot (`B4.6` / `B4.6`) with its own silent-reading/pair-read/reading-log
template and a rotating reader list.

### 3.4 The audit trail — this is the strongest part of the repo

You didn't just generate; you verified. Four audits, all with committed results:

- **`audit_a_databases.py` → `audit_a_results.json`** — structural validation of all 76 DB
  files: code format, required fields, placeholder-vs-rich content, expected counts.
  **Result: all PASS.**
- **`audit_b_pdf_crosscheck.py` → `audit_b_results.json`** — the important one: every DB
  is re-checked **against the source PDF text**. 76 entries measuring `valid_pct` and
  `coverage_pct`. Sample results: Mathematics B1/B2/B3/B4/B5 100% coverage,
  English B1–B3 100%, Ghanaian Language B1–B3 100%, Creative Arts B1–B3 100%.
  Known `WARN`s remain: OWOP B1 (95.8%, `B1.1.2.1.1` missing), History B1 (88.9%),
  RME B1 (90.0%), Science B3 (one extra code `B3.2.4.1.2` in PDF not in DB).
- **`audit_c_*.py` → `audit_c_results.json`** — verifies the 180-record counts in every
  enriched JSON and that each DOCX is well-formed and non-trivially sized.
  **All PASS at exactly 180 lessons each.**
- **`apply_audit_fixes.py` → `audit_fixes_log.json`** — the remediation log. 32 entries,
  each with a backup step, e.g. *"REMOVE B3.1.2.2.4 from creative-arts_B3… (not in official
  NaCCA PDF)"*, *"FILL 69 empty assessment fields in english_curriculum_db_clean.json"*,
  *"FIX 172 empty assessment in english_lessons_enriched.json"*.

This is a genuinely rigorous provenance chain — official PDF → parsed text → database →
cross-check against PDF → fix → regenerate → re-audit.

---

## 4. Workstream B — the Beacon web app (inside `saas-files.zip`)

### 4.1 What it is

> **Beacon Educational Consult — Teacher Network.** A members-only, mobile-first,
> installable **PWA** where Ghanaian teachers browse the NaCCA curriculum (Basic 1–9),
> generate Schemes of Learning and weekly Lesson Plans in the national format, build a
> shared Question Bank, run classroom quizzes, and export to branded PDF / Word / PowerPoint.

It was **rebranded** partway through — `process.md` records the rename from
*Lecturer Sam Consult* → *Beacon Educational Consult*.

### 4.2 Stack

| Layer | Choice |
|---|---|
| Frontend | React 19, Vite 8 (Rolldown) + React Compiler, React Router 7 |
| Styling | Tailwind CSS v4 via `@tailwindcss/vite` |
| Backend | Firebase Authentication (email/password) + Cloud Firestore (offline persistence) |
| Curriculum data | Static JSON in `public/curriculum/` — **no Firestore reads to browse** |
| Rich text | Tiptap |
| Exports | `jspdf` + `jspdf-autotable` (PDF), `docx` (Word), `pptxgenjs` (PPTX) |
| Hosting | Vercel; Firestore rules/indexes via Firebase CLI |
| Package manager | Yarn (never npm) |

### 4.3 Scope — it's big. ~15 modules

**Public:** landing + membership application, published teaching vacancies, quotes, calendar, articles.

**Member portal** (`/portal/*`, all behind `ProtectedLayout` which requires an *approved* member):

| Module | Notes |
|---|---|
| Curriculum library | B1–B9, all subjects, strand → sub-strand → content standard → indicator drill-down |
| Schemes of Learning | Termly, one row/week, REVISION/EXAMINATION/VACATION rows; auto-generated or assembled via picker; clone & adapt |
| Lesson Plans | The same national weekly format your DOCX files use; header block + DAYS × PHASES grid; PDF/Word export |
| Question Bank | MCQ / short / essay tagged class→subject→strand→sub-strand→indicator; **weekly quota of 5 questions per teacher** |
| Questions Generator | Assemble shuffled exam papers with optional marking scheme |
| Quiz Maker | Package the bank as a classroom `.pptx` |
| Classrooms & in-app quizzes | 6-char class code; synthetic pupil logins (no email); instant MCQ marking; teacher grades written answers |
| School workspaces | Multi-tenant `schools` + `school_codes` join codes; `school_admin` role; school-only sharing |
| Subscriptions | Free (5 downloads/mo) vs Pro (unlimited); Mobile Money paid out-of-band, **admin confirms manually** |
| Community | Teacher feed, one-minute slide lessons, author pages, term progress tracker |
| Other | Study notes, articles, Quote of the Day, Scratch playground, admin approval queues |

### 4.4 Data model — 17 Firestore collections

`users`, `posts`, `articles`, `notes`(+`comments`), `weekly_forecasts` (schemes),
`lesson_plans`, `questions`, `lesson_slides`(+`comments`), `vacancies`, `schools`,
`school_codes`, `classrooms`, `quizzes`, `quiz_attempts`, `subscriptions`, `progress`,
`quote_likes` — plus the static curriculum/quotes JSON.

The single most important invariant: **a user is `pending` until an admin approves them.**
Only `approved` members (or `admin`s) read/write shared data. Enforced twice — once in the
client gate `ProtectedLayout` (UX only) and once for real in `firestore.rules` (23 KB,
committed in the zip).

### 4.5 Documentation quality — unusually good

`saas-files/docs/` is a 10-chapter **"Code Bible"**: `architecture.md`, `data-model.md`,
`security.md`, `features.md`, `shared-code.md`, `conventions.md`, `pwa-offline.md`,
`build-deploy.md`, `playbooks.md`, `gotchas.md`, plus `project-blueprint.md`,
`saas-gap-analysis.md`, `deliveries-roadmap.md`, `IDENTIFIED-ISSUES.md`,
`FINAL ANALYSIS.md`. There are also 4 large HTML design/PDD documents and
`process/` (project outline, DB schema, working notes).

### 4.6 There are 4 generations of the app in the zip

The `App-II / App-III / App-IV` and `components-II / -III / -IV` prefixes show successive
iterations, plus a **"NACCA QuizBank"** variant (`README-X.md`, `db-III/IV`, `routes-III/IV`,
`stores-III/IV`, `lib-III/IV`) — a separate offline-first Dexie/IndexedDB **student quiz PWA**
for B7–B9 with its own 4-phase build roadmap. `src/` is the current, canonical Beacon app.

---

## 5. What I noticed — issues and risks

### Structural

1. **Everything is flat and unorganised.** 533 files in one directory with no
   `README.md`, no `.gitignore`, no `requirements.txt`, no folder structure. A newcomer
   (or future you) cannot tell `generate_lesson_plans.py` from
   `generate_lesson_plans2.py` from `generate_lesson_plans_fixed.py` (all ~49 KB, near-identical).
2. **The web app is sealed in a ZIP.** You cannot `yarn dev` the app from the repo root.
   There is no `package.json`, `src/`, or `public/` at root — they only exist inside
   `saas-files.zip`. Unzip it (or better, commit it expanded) before doing any app work.
3. **~30 scratch/forensic scripts are still there.** `print_page6.py`, `print_page10.py`,
   `print_page11.py`, `read_notes.py`, `read_math_notes.py`, `scan_cells.py`,
   `test_block_split.py`, `test_parse_math.py`, … These were PDF-reconnaissance one-offs.
4. **Hard-coded absolute paths.** 16 scripts reference `/home/user/curriculum_db/…`, which
   doesn't exist here (the JSONs are flat at root). **Most generator scripts will not run
   as-is** without rewriting those paths.
5. **B1 files use a different naming convention.** `math_curriculum_db_clean.json` (no
   `_B1_`) vs `mathematics_B4_curriculum_db_clean.json`. Also `ghanaian_language_*` vs
   `ghanaian_b2_*` vs `ghanaian-language_B2_*`, and `mathematics_*` vs `math_*`. This
   inconsistency means most glob-based scripts need per-subject special-casing.

### Data

6. **Root and `saas-files/data/` have diverged.** Neither is a superset:
   - Root has all **73 `*_lessons_enriched.json`** files; `data/` has only two.
   - `data/` has **Computing B4–B6, French B4–B6, KG1/KG2 kindergarten, `jhs_maths.json`**,
     and several non-`_clean` variants that the root does not have.
   The app's curriculum loader expects `<grade>_subjects.json` / `_indicators.json` /
   `_schedules.json` in `public/curriculum/` — **those files are not present anywhere in
   the repo**; they're produced by `seed/build_curriculum.py`, which only handles B1.
7. **`is_revision` is inconsistently populated.** B1 Mathematics marks 140/180 lessons and
   B1 Science 149/180 as revision; **every other one of the 73 files marks 0.** Either the
   flag was only wired up for the two pilot subjects, or it's stale. Worth checking before
   you rely on it for REVISION rows in schemes.
8. **Four orphan `_v2` DOCX files** for B1 (Maths, English, Ghanaian Language, Creative
   Arts). **RESOLVED — v2 promoted to the canonical filenames, `_v2` files deleted.**
   v1's Ghanaian Language book contained **540 placeholder strings** (it printed
   `"Ghanaian Language Content Standard B1.1.1.1"` where real NaCCA text belongs); v2
   has none. See the resolution section at the end of this report.
9. **Audit-B caveats are real, if small.** OWOP B1 is missing `B1.1.2.1.1`; History B1 and
   RME B1 each have one PDF code not in the DB; Science B3 has one DB code not in the PDF.
   Also note `audit_b2_results.json` shows an older, harsher cross-check for Mathematics B1
   (41.7% hit rate) — resolved later, but the two result files tell different stories.

### Application (self-documented, still open)

10. **Committed Firestore rules ≠ deployed rules.** Called out as the #1 gotcha: Vercel
    does not deploy rules. `firebase deploy --only firestore:rules,firestore:indexes` must
    be run manually, and there's no `.firebaserc`.
11. **Performance debt.** `IDENTIFIED-ISSUES.md` lists 10 issues — `limit(1000)` bulk
    fetches, client-side-only filtering, no pagination, module-level caches with no TTL,
    synchronous export generation blocking the main thread. `saas-gap-analysis.md` shows
    Phase 0 hardening already fixed the worst (lazy + TTL-cached SearchPanel, server-side
    scoped question queries) — worth confirming that's live.
12. **Billing is manual.** Members pay by Mobile Money and an admin clicks "Mark as paid".
    Deliberate (free-tier decision, documented in `deliveries-roadmap.md`), but it means
    revenue does not scale without a Blaze plan.
13. **Slide-lesson authoring is disabled** (routes commented out in `App.jsx`); dead
    `Navbar.jsx`; a long-standing `react-refresh` lint nit in `ToastContext.jsx`.
14. **No tests.** No test runner in `package.json`, no test files for the app, and the
    `test_*.py` files at root are manual scratch scripts, not a suite.
15. **Third-party review flagged strategic risk.** `FINAL ANALYSIS.md` argues ~15 modules is
    too broad for a small team and recommends doubling down on the
    *planning → assessment spine* (curriculum → scheme → lesson plan → questions → assessment)
    and putting vacancies/articles/quotes into maintenance mode.

---

## 6. What I'd suggest, in priority order

1. **Unpack and restructure.** Expand `saas-files.zip` into `app/`, move the Python
   pipeline into `pipeline/`, raw text into `pipeline/raw/`, the JSON DBs into
   `data/curriculum/`, the DOCX into `deliverables/`, PDFs into `sources/`. Add a README
   and a `.gitignore`. Delete or archive the ~30 scratch scripts.
2. **Fix the path dependencies** so the pipeline is re-runnable (`/home/user/curriculum_db`
   → relative paths), and normalise the B1 file naming.
3. **Pick a canonical B1** — v1 or v2 — and delete or clearly archive the loser.
4. **Reconcile root JSON vs `data/` JSON**, and generate the app's
   `public/curriculum/<grade>_*.json` for **all** grades B1–B9 (currently only B1 is scripted).
   This is the single highest-value connection between the two workstreams: you have
   13,140 generated lessons sitting outside the app that could power its lesson-plan
   pre-fill and scheme auto-generation.
5. **Wire `firebase deploy --only firestore:rules`** into your release checklist, and write
   rules unit tests against the emulator.
6. **Decide the module-focus question** from `FINAL ANALYSIS.md` before building anything new.

---

## 7. Files worth opening first

| To understand… | Open |
|---|---|
| The finished product | `Basic4_Mathematics_Lesson_Plan_Full_Year.docx` (or any `Basic*_*.docx`) |
| The data shape | `math_b4_lessons_enriched.json` |
| The DB shape | `mathematics_B4_curriculum_db_clean.json` + `mathematics_B4_curriculum_summary.json` |
| How lessons are generated | `generate_b4_core4.py` (the richest generator) |
| How Word files are built | `build_math_b4_word_document.py` |
| Verification rigour | `audit_b_pdf_crosscheck.py` + `audit_b_results.json` + `audit_fixes_log.json` |
| The app | `saas-files.zip` → `README.md`, then `docs/` (start with `architecture.md`, `data-model.md`, `gotchas.md`) |
| Where the app is going | `docs/saas-gap-analysis.md`, `docs/deliveries-roadmap.md`, `docs/IDENTIFIED-ISSUES.md` |


---

## Resolution update (applied after this analysis)

Two of the open items above have since been closed. The counts in this report are
**as-found** at commit `c9a186c`; the current tree differs as noted.

| # | Item | Status |
|---|---|---|
| 8 | Four orphan B1 `_v2` DOCX files, no canonical version recorded | **RESOLVED** — v2 promoted to the canonical filenames, `_v2` files deleted. The library is 73 books. |
| — | 33 books carried the wrong grade band on the title page | **RESOLVED** — B4–B6 now read `Upper Primary`; the spurious `· Lower Primary` was stripped from B7–B9. Verified 73/73 correct. |

**B1 v1 vs v2 — the decisive finding.** The two versions are structurally identical
(4,684 paragraphs each). The "Session 1 of 3 vs Session 1 of 2" difference quoted above
was a measurement error: it compared **B4 against B1**, two different grades. The real
difference is content quality: **v1's Ghanaian Language book contains 540 placeholder
strings**, printing `"Ghanaian Language Content Standard B1.1.1.1"` in place of real
curriculum text. v2 has none. v1 was unsellable as printed.

**Placeholder sweep:** 0 of 73 books now contain placeholder strings.

**Grade bands** (NaCCA): KG1–KG2 Kindergarten · B1–B3 Lower Primary · B4–B6 Upper
Primary · B7–B9 JHS 1–3. The 33 corrected books were B4–B6 (21) and B7–B9 (12).

Scripts — dry-run by default, `--apply` to commit, both idempotent:

```bash
python3 tools/promote_b1_v2.py
python3 tools/fix_grade_band_labels.py
```

Every original remains in git: `git checkout c9a186c -- <file>`
