# Beacon Consult

A members-only network and curriculum planning portal for Ghanaian basic-school
teachers (KG1–B9), built on the official NaCCA Standards-Based Curriculum. Teachers
browse the curriculum, build schemes of learning and lesson plans, author questions,
share notes and articles, and export everything as Word, PDF or PowerPoint — all
offline-capable, all from the browser.

Two products share one dataset:

* **The portal** — this repository (`src/`), a React 19 + Vite 8 + Tailwind 4 PWA on
  Firebase, deployed to Vercel.
* **The books** — Word workbooks and textbooks generated offline by `scripts/` and
  `seed/`, the finished, sellable artefacts.

> The retired NCOS kernel/TypeScript app now lives under `legacy/` for reference.
> Nothing in the portal imports from it.

---

## Quick start

```bash
# Node 22+ and Yarn 4 (corepack enable)
yarn install
cp .env.example .env.local     # fill in the VITE_FIREBASE_* values
yarn dev                       # http://localhost:5199
```

Other useful commands:

| Command | What it does |
|---|---|
| `yarn build` / `yarn preview` | Production build, then serve it (PWA behaviour only exists here) |
| `yarn lint` | ESLint incl. the React Compiler rules — must stay clean |
| `make check` | The pre-deploy gate: lint + tests + curriculum validation + inventory + build |
| `make deploy-check URL=…` | Check a live deploy from the outside (Firebase config, curriculum hash, SPA rewrite) — see [verification.md](docs/verification.md) |
| `make audit` (`make inventory`) | The data audit: regenerate `data/inventory.json`, list every dataset gap |
| `make build-curriculum` | Rebuild `public/curriculum/` from `data/` after a dataset change |

Firestore rules and indexes deploy separately from the app:

```bash
firebase deploy --only firestore:rules,firestore:indexes
```

---

## The dataset (three layers — do not conflate them)

Produced by `make inventory` → `data/inventory.json`. Full definition in
`docs/curriculum-data.md`; the hub for every number is that file, not this one.

| Layer | Path | Contents |
|---|---|---|
| **L1 curriculum** | `data/curriculum/` | 84 databases · 84 summaries · **4,040 indicators** · audited against 27 NaCCA source PDFs |
| **L2 lessons** | `data/lessons/` | **13,140 lesson slots** (73 files, 13 subjects, B1–B9) with a filled teaching template |
| **L3 bundle** | `public/curriculum/` | **4,040 indicators** across 84 subject-grades / 11 grades — what the portal serves (39.7 MB) |

L1 and L3 agree exactly: every one of the 84 served subject-grades comes from the
audited copy. That took until 2026-09-18 — nine subject-grades (computing and french
B4–B6, kindergarten KG1/KG2, `english-language B5`) were served from the
`data/reference/` fallback and had no L1 counterpart;
`scripts/promote_reference_subjects.py` moved them and gave them summaries.
`docs/curriculum-data.md` defines the layers and what is left in `data/reference/`.

---

## What the portal does

**Public (no account):** landing page, teaching vacancies, quote of the day and
weekly teaching theory, the academic calendar, and articles set to public.

**Members (after approval):**

| Area | What teachers get |
|---|---|
| Workspace | The home page: network posts and likes, your own contributions, quote of the day, term progress, this week's contribution count, and the term calendar |
| Curriculum | Every indicator by strand → sub-strand → content standard, KG1–B9 |
| Schemes of learning | A term scheme seeded from the curriculum schedule, editable per week, exported to Word/PDF |
| Lesson plans | Indicator-linked plans (objectives, starter, main, plenary, assessment) exported to Word/PDF |
| Question bank | MCQ/short/essay questions, exam-paper PDFs, quiz slideshows (.pptx) |
| Slide lessons | A week's scheduled lessons turned into a presentation |
| Study notes & articles | Shared writing, with comments on notes and public visibility for articles |
| Vacancies | Post openings; published vacancies appear on the public site |
| Search | One box across indicators and everything members have shared |
| Progress | Tick off the weeks you have taught, per subject and term |
| Members (admin) | Approve, suspend and promote accounts |

Accounts start `pending` and are reviewed by an administrator. Roles are `member`
and `admin`, and **Firestore rules are the enforcement point** — the React gate is
only there for a better experience. See `docs/security.md`.

---

## Offline and exports

The app is a PWA: the service worker caches the shell and static curriculum/quotes so
the portal keeps working on a weak connection, and Firestore's persistent cache queues
writes until you are back online (there is an on-screen indicator for both). Instalments
are configured via `public/manifest.webmanifest`.

Every document — scheme, lesson plan, exam paper, quiz, slide deck — is generated
**in the browser** (docx, jsPDF, PptxGenJS). There is no server-side rendering service
and no paid API; the free tier is enough to run the whole thing.

---

## Documentation

The code bible lives in `docs/`. Start with `docs/code-bible.md`, then:

| Document | Purpose |
|---|---|
| `docs/architecture.md` | Folder-by-folder map of the app |
| `docs/curriculum-data.md` | The dataset hub: layers, totals, gaps (regenerable via `make inventory`) |
| `docs/security.md` | Firestore rules, roles and the approval workflow |
| `docs/conventions.md` | Design tokens, class vocabulary, code style |
| `docs/pwa-offline.md` | Service worker, caching strategy, offline behaviour |
| `docs/book-structure.md` | How curriculum maps to books (strand → chapter, indicator → lesson) |
| `docs/deliveries-roadmap.md` | What is live, what is deferred, and why |
| `legacy/docs/CODE_REVIEW.md` | The audit of the previous app, kept for context |

---

## Repository layout

```
src/                  portal source (pages, components, hooks, lib, context)
public/               static assets: curriculum JSON, quotes, icons, service worker
data/                 source dataset (curriculum, lessons, reference)
scripts/, seed/       Python pipeline and book generators
docs/                 the code bible
legacy/               retired NCOS app + its documentation
firestore.rules       security rules (deployed separately)
```

© Beacon Educational Consult. Curriculum data derived from NaCCA materials.
