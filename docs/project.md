---
inclusion: always
---

# Beacon Consult — project context

## What this is

Beacon Educational Consult builds curriculum-mapped teaching materials for Ghanaian
basic schools (KG1–B9) from the official NaCCA Standards-Based Curriculum. Two
products share one dataset:

* **The portal** — the React PWA at the repository root (`src/`), deployed to Vercel
  with Firebase Auth + Firestore. This is what the repository *is* now.
* **The books** — Word workbooks/textbooks generated offline by `scripts/` and
  `seed/`, the sellable artefacts.

The previous kernel/TypeScript application (NCOS) has been retired under `legacy/`.
Nothing in the repository imports from it; it is reference material only.

**Current state, in one line:** the portal is built and passes `make check`
(lint + production build); the books pipeline and the roadmap features
(deliveries/records of work, payments ledger UI) are next.

## Repository map

| Path | What it holds |
|---|---|
| `src/` | Portal source — `pages/`, `components/`, `hooks/`, `lib/`, `context/` |
| `public/curriculum/` | Static per-grade JSON the portal reads offline (39.7 MB, 4,040 indicators) |
| `public/quotes/`, `public/icons/`, `public/sw.js`, `public/manifest.webmanifest` | PWA assets |
| `data/curriculum/`, `data/lessons/`, `data/reference/` | Source dataset (Python side) |
| `scripts/` | Data pipeline: inventory, bundle build, validation, book generation |
| `docs/` | The code bible — architecture, data model, security, conventions, playbooks |
| `legacy/` | Retired NCOS app and its documentation |
| `firestore.rules`, `firestore.indexes.json` | Deployed separately from the app |

## The dataset — three layers, three different totals

Never say "the dataset has N indicators" without naming the layer. Full definition in
`docs/curriculum-data.md`; regenerate the numbers with `make inventory`
(→ `data/inventory.json`).

| Layer | Path | Contents |
|---|---|---|
| L1 curriculum | `data/curriculum/` | 75 DBs · 73 summaries · **3,095 indicators** (audited) |
| L2 lessons | `data/lessons/` | **13,140 lesson slots** — 3 terms × 12 weeks × 5 days × 73 subject-grades, 13 subjects, B1–B9 |
| L3 bundle | `public/curriculum/` | **4,040 indicators** across 84 subject-grades / 11 grades (39.7 MB) — what the portal serves |

`data/reference/` is a **second, partly-divergent copy** that `scripts/_paths.py`
searches as a silent fallback. It supplies 8 L3 subject-grades that L1 does not have
(computing B4–B6, french B4–B6, kindergarten KG1–KG2). It is never a total — only a
fallback, and an open decision (TODO P1-1).

Measured fidelity of L2: `starter` 75% distinct, `main` 41%, `rpk` 2%, `plenary` 3% —
templated structure with indicator-specific content. Do not describe these as
"authored lesson plans".

## Working rules

* **Yarn 4** manages the frontend (`yarn install`, `yarn dev`, `yarn build`, `yarn lint`).
  Node 22+. The Python side uses `requirements.txt`.
* `docs/code-bible.md` is the standalone spec: routes, collections, class vocabulary,
  security model and the build order. Read it before adding a feature.
* Firestore rules are a **tested surface**, not an afterthought: the portal's
  authorization is enforced there, and the React gate is UX only.
* Curriculum JSON is static and offline-first. Anything that needs a network call at
  read time is a design smell.
* Exports (Word/PDF/PPTX) are generated **client-side** — no server, no paid plan.
* Never commit `node_modules/`, `dist/`, or generated `books/` artefacts.

## Related repositories

`beaconeducationalconsult-gh/{beacon-consult, nacca-library, peacemaker-novel, nacca-ai}`.
