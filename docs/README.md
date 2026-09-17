# Beacon — Code Bible

The authoritative reference for the **Beacon Educational Consult** codebase. Start here,
then jump to the chapter you need. Keep this current when you change how something works.

> **Audience:** developers (and AI agents) working on this repo.
> **Golden rule:** this documents the code as it *is*. If code and docs disagree, the code
> wins — fix the docs.

## What Beacon is

A mobile-first **Progressive Web App** for a consortium of Ghanaian school teachers. It is
an installable, offline-capable portal where **approved members** browse the NaCCA
curriculum and create/share teaching resources: schemes of learning, lesson plans, a
question bank (with paper & quiz generators), study notes, articles, a community feed, a
"Quote of the Day", vacancies, and a personal progress tracker. A handful of pages are
also exposed publicly (landing, vacancies, quotes, calendar, articles).

## Tech stack (see [`build-deploy.md`](build-deploy.md) for versions)

- **React 19** SPA built with **Vite 8** (Rolldown) + the React Compiler (Babel plugin)
- **React Router 7** (`BrowserRouter`)
- **Tailwind CSS v4.3** (`@tailwindcss/vite`) — tokens in `src/index.css` (`@theme`) and
  the shared class vocabulary (`@utility`)
- **Firebase**: Auth (email/password) + **Firestore** (offline persistence enabled)
- **Tiptap** rich-text editor (articles/notes)
- Client-side document export: **jsPDF**, **docx**, **pptxgenjs**
- Hosted on **Vercel**; Firestore rules/indexes deployed via the **Firebase CLI**
- Package manager: **yarn** (never npm)

## Chapters

| # | Chapter | What's inside |
|---|---------|---------------|
| 1 | [architecture.md](architecture.md) | App shape, routing tree, providers, layout, PWA wiring |
| 2 | [data-model.md](data-model.md) | Every Firestore collection + shape + who writes it; static JSON |
| 3 | [security.md](security.md) | Auth flow, member states/roles, `firestore.rules` explained |
| 4 | [features.md](features.md) | Module-by-module reference (each page, its routes & data) |
| 5 | [shared-code.md](shared-code.md) | Hooks, `lib/` exporters, shared components, contexts |
| 6 | [conventions.md](conventions.md) | Patterns, the Tailwind design vocabulary, code style |
| 7 | [pwa-offline.md](pwa-offline.md) | Service worker, manifest, offline persistence, QOTD determinism |
| 8 | [build-deploy.md](build-deploy.md) | Scripts, env vars, Vercel + Firebase deploy |
| 9 | [playbooks.md](playbooks.md) | How to add a page / collection / exporter / curriculum grade |
| 10 | [gotchas.md](gotchas.md) | Known gaps, footguns, and things that will bite you |
| 11 | [curriculum-data.md](curriculum-data.md) | **The dataset hub** — the three layers (L1/L2/L3), every headline number, the gaps |
| 12 | [book-structure.md](book-structure.md) | The textbook/workbook spec (chapter → unit → topic → lesson; pilot B1 Mathematics) |
| 13 | [deliveries-roadmap.md](deliveries-roadmap.md) | Deferred work: the paid-delivery ledger, server-side hard gate, MoMo automation |
| 14 | [git-codes.md](git-codes.md) | The git commands used on this repo (init → push → track a branch) |

Also in this folder:

- **[project-blueprint.md](project-blueprint.md)** — a reusable lifecycle map (planning → design
  → backend + frontend → deploy → publish), generalized from how Beacon was built.
- **[code-bible.md](code-bible.md)** — the build-in-order cookbook: copy-pasteable snippets for
  scaffolding, tokens, rules, auth, data access, and the feature-slice recipe.
- **[TODO.md](TODO.md)** — the live backlog, ordered by dependency.
- **[analysis/](analysis/)** — the audits that shaped this architecture: `IDENTIFIED-ISSUES.md`
  (performance findings) and `FINAL ANALYSIS.md` (the priorities drawn from them).
- **[OPPORTUNITY_MAP.md](OPPORTUNITY_MAP.md)** / **[NACCA_QUESTION_BANK.yaml](NACCA_QUESTION_BANK.yaml)**
  — product research and the question-bank spec.

## 60-second mental model

```
Browser ──> React SPA (Vite build, hosted on Vercel)
              │
              ├─ Public routes: /  /vacancies /quotes /calendar /articles /login /signup
              │
              └─ /portal/*  (ProtectedLayout: requires signed-in + approved member)
                              │
                              └─ Firestore (single project) ── gated by firestore.rules
                                   ▲                                (isApprovedOrAdmin)
                                   └─ Firestore offline cache (IndexedDB) → works offline

Static curriculum + quotes JSON live in /public and are cached by the service worker.
```

Everything is gated behind **one** idea: a user is `pending` until an admin approves them;
only `approved` members (or `admin`s) can read/write the shared data. See
[security.md](security.md).
