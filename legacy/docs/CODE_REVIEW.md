# Critical Code Review — Beacon Consult / NCOS

**Reviewed:** 2026-09-17 · branch `arena/01a0af88-beacon-consult` @ `18517b1`
**Scope:** whole repository (app/ React portal, ncos/ Python kernel, scripts/ pipeline, data/, deploy/, docs/)
**Method:** read every file in `app/src/` (~3.1k lines), the Python kernel, the pipeline entry points and the docs;
then *executed* the build, the linter, the curriculum validator, the kernel registry and the module boot sequence
against the real data to confirm or discard suspicions. Commands and outputs are quoted inline so every claim
below is reproducible.

---

## Verdict

The **data asset is the strongest thing here** — 4,040 indicators and 13,140 fully-written lesson records that
validate cleanly and pass the repo's own audit scripts. The **software wrapped around it is not in the same
state**: the web app does not compile, the documented kernel CLI is dead on arrival, the "fail-loud-at-boot"
safety net is decorative, and the documents the portal produces are a 4-section skeleton that throws away almost
everything the data contains.

Nothing here is unsalvageable — the app is small (3,100 lines), the data is sound, and most of the blockers are
a day or two of work each. But the gap between what the docs claim and what the code does is wide enough that
**nobody should trust this repo's self-description until the P0 list is closed.**

| # | Severity | Finding | Blast radius |
|---|----------|---------|--------------|
| 1 | 🔴 P0 | `npm run build` fails — 36 TypeScript errors; the app cannot deploy | Deployment |
| 2 | 🔴 P0 | `make boot-check` / `list-modules` crash — `ncos.kernel.drivers` does not exist | Documented workflow |
| 3 | 🔴 P0 | No module validates anything; `validate()` always returns `[]` | The "fail-loud" principle |
| 4 | 🔴 P0 | `math` module id ≠ `mathematics` bundle id → 0 indicators, empty lesson plans & records of work | Flagship subject |
| 5 | 🔴 P0 | History/Dashboard read with a different key than they write; nothing creates `users/{uid}` | Every logged-in user |
| 6 | 🟠 P1 | Generated documents ignore the 13,140 authored lessons; every doc prints `Sub-skill: n/a` | Product value |
| 7 | 🟠 P1 | Question Bank builds an empty document and reports success | Silent data loss |
| 8 | 🟠 P1 | Firestore rules let a user attribute records to another school; `storage.rules` missing | Security / privacy |
| 9 | 🟠 P1 | 38 MB committed JSON bundle, no chunking, PWA cache never invalidates | Mobile performance |
| 10 | 🟠 P1 | Zero tests, zero CI, no lint gate on 39k lines of Python + TS | Regression risk |
| 11 | 🟡 P2 | 13 near-identical subject modules; 8 near-identical math builders; 16 per-grade backfills | Change amplification |
| 12 | 🟡 P2 | Python "spec" and TypeScript "runtime" have already drifted apart | Architectural intent |
| 13 | 🟡 P2 | `schoolContext` is built on every generate and consumed by nothing | Dead work, missing branding |
| 14 | 🟡 P2 | Docs describe a repo that no longer exists (paths, commands, "app is empty") | Onboarding, trust |
| 15 | 🟡 P2 | Repo hygiene: tracked `.pyc`, no root `.gitignore`, 132 MB in one squashed commit, divergent `data/reference/` | Maintenance |
| 16 | 🟡 P2 | Firestore/PWA/env config undocumented; `.env.example` absent; manifest icons 404 | Setup, PWA install |
| 17 | 🔵 P3 | UX/robustness rough edges (no error boundary, raw ids in dropdowns, sync `revokeObjectURL`, no pagination, no a11y) | Polish |

---

## P0 — things that are broken right now

### 1. The app does not build. Deployment is impossible as configured.

```
$ npm run build          # package.json: "build": "tsc -b && vite build"
BUILD EXIT CODE: 2       # 36 × error TS
```

Failures fall into four groups:

| Error | Count | Where |
|---|---|---|
| `TS6133` unused parameter (`noUnusedLocals`/`noUnusedParameters`) | 27 | `app/src/modules/*/*Module.ts:125` — every `generateQuestions(indicator, count)` stub |
| `TS2322` `DocType` includes `'question_bank'` but `recordGeneration()` does not | 1 | `app/src/services/useGenerate.ts:94` vs `app/src/services/firestore.ts:31` |
| `TS2339` Property `generatedAt` does not exist on `{ id: string }` | 6 | `app/src/ui/pages/DashboardPage.tsx:39-45`, `HistoryPage.tsx:31-35` — `getGenerationHistory()` returns untyped `{id, ...data}` |
| `TS2367` comparison to `'question_bank'` has no overlap | 2 | `app/src/ui/pages/GeneratePage.tsx:144,171` |

Note the last one: `GeneratePage` types `DocType` without `'question_bank'` and then casts an array *containing*
`'question_bank'` to `DocType[]`. It works at runtime and is a type error — the classic sign that this code has
never been through a compiler. `docs/TODO.md` confirms it: *"Verify `yarn build` on a real machine — the
Materials screen has never been compiled (no npm registry in the dev sandbox)"*. (It is `npm`, not `yarn`.)

`vite dev` works because Vite does not typecheck, which is exactly why this stayed hidden.

### 2. The kernel CLI — the repo's advertised health check — cannot start.

```
$ make boot-check
  File "tools/ncosctl.py", line 14, in <module>
    from ncos.kernel.drivers.docx_driver import DocxDriver
ModuleNotFoundError: No module named 'ncos.kernel.drivers'
```

`tools/ncosctl.py` imports a driver module that was never ported into this repo (the docx renderer lives at
`app/src/drivers/docx.ts` and the book renderers inside `scripts/`). Both the README ("Check the Python kernel is
healthy") and the Makefile's `boot-check` / `list-modules` targets are dead. So the very first command a new
contributor is told to run fails.

### 3. `validate()` validates nothing — the fail-loud principle is a comment, not code.

Every module:

```ts
validate(): string[] {
  return []   // ScienceModule.ts:33, and identically in the other 12
}
```

I ran the real registry through esbuild + node:

```
BOOT REPORT: {"loaded":["math","english-language",...,"owop"],"failed":[],"durationMs":0.065}
loaded: 13  failed: 0
```

A boot report that is always green carries no information. The registry (`app/src/kernel/registry.ts`) implements
exclusion properly — but nothing ever fails, so the mechanism has never once been exercised. This is the direct
cause of findings #4 and #7 below, both of which a real `validate()` would have caught at startup:
declared grades that do not exist in the bundle, subject ids that match no indicator, and capabilities advertised
without data.

### 4. `math` vs `mathematics`: the reference subject returns nothing, and emits empty documents.

```
$ node  # filter the real bundle exactly as the app does
MODULE+GRADE COMBOS THAT RESOLVE TO ZERO INDICATORS:
  - math B4 => 0 indicators after filter (bundle has: mathematics)
total combos: 59  broken: 1
```

`MathModule.id = 'math'` (`MathModule.ts:9`) but every indicator in `app/public/curriculum/b4_indicators.json`
carries `subjectId: "mathematics"`. Consequences, all silent:

* **Generate → Lesson Plan → Mathematics → B4** shows an empty indicator dropdown, so the button stays disabled.
* **Scheme of Work** for math publishes a table with zero rows.
* **Record of Work** filters `b4_schedules.json` by `subjectId === 'math'` — schedules also use `mathematics` —
  so it *downloads a Word file containing an empty table*, with no warning.

The other 58 module/grade combinations are fine, which makes this worse: it looks like a data gap rather than a
naming bug. `useIndicators` (`app/src/services/useCurriculum.ts:22`) and every module's `loadIndicators` filter by
the *same* id, so there is exactly one place this could have been caught — a real `validate()`.

### 5. Generation history can never display, and nothing onboards a user.

Two independent defects on the same path:

```ts
// write — useGenerate.ts:33
const schoolId = userData?.schoolId ?? user.uid
// read — DashboardPage.tsx:28, HistoryPage.tsx:26
const schoolId = (user as any).schoolId ?? user.uid
```

A Firebase `User` object has no `schoolId`, so the cast is always `undefined` and readers fall back to
`user.uid`, while writers use the real school id from `users/{uid}`. When those differ, the query returns
nothing. When they don't differ (no user document), the read rule fails instead:

```
allow read: if request.auth != null
            && resource.data.schoolId ==
               get(/databases/$(database)/documents/users/$(request.auth.uid)).data.schoolId;
```

With no `users/{uid}` document, `get(...)` is null, `.data` throws, access is denied — and both pages swallow the
error into `console.error` and render "No documents generated yet." Meanwhile **no code in the app writes a
`schools/{id}` or `users/{uid}` document anywhere** (I grepped every `addDoc`/`setDoc`/`updateDoc`: only
`generated_materials` is ever written). So a new teacher who signs in with Google lands on a dashboard showing
"Your School / 0 documents" with no path forward, and self-serve onboarding is impossible without an admin
hand-keying Firestore documents.

---

## P1 — high severity

### 6. The portal's output is a skeleton; the project's best asset is discarded.

`MathModule.generateLessonPlan` (mirrored verbatim in the other 12 modules) emits four sections: Indicator,
Objectives, Core Content, Duration. Nothing else. Meanwhile `data/lessons/*_lessons_enriched.json` holds
13,140 records with `rpk` (relevant previous knowledge), `starter`, `main`, `plenary`, `assessment`,
`competencies`, `resources`, `keywords`, `perf_indicator`, `session_title` — the exact content that makes the 73
sold books worth money. The browser generator reads none of it; it only ever consumes
`<grade>_indicators.json`.

Worse, the one subject-specific field it *does* try to render is missing from the bundle:

```
$ node -e "…count indicators with non-empty extra…"
b4 indicators: 517   with non-empty extra: 0
$ grep -c sub_skill app/public/curriculum/b4_indicators.json
0
```

So the `CalloutBlock` renders the literal string **"Sub-skill: n/a"** (`(ind.extra.sub_skill as string) ?? 'n/a'`)
in every lesson plan produced by the portal. A teacher comparing the download to the printed book will see a
document that is strictly worse.

### 7. Question Bank fails silently and confidently.

```ts
const res = await fetch(`/curriculum/questions/math/${grade}.json`).catch(() => null)
if (res && res.ok) { /* … */ }          // MathModule.ts:124 — no else, no error
```

`app/public/curriculum/questions/` does not exist, so this 404s every time and the module returns a document with
an empty "Questions" section — which the driver happily renders and downloads as a `.docx`. The real (small) data
lives at `data/questions/mathematics/B4.json` and is never copied into the bundle by
`scripts/build_app_curriculum.py`. `capabilities` advertises `questions` for math anyway
(`MathModule.ts:12`), and the code that would gate on it only checks that the capability string exists.

### 8. Security & data-integrity issues in the rules and the archived service.

* **Create is unauthenticated with respect to school:**
  `allow create: if request.auth != null && request.auth.uid == request.resource.data.userId;`
  `schoolId` is never checked, so any signed-in user can write history records attributed to *another* school —
  and those records then become readable by that school's members under the read rule.
* **No update/delete for anyone** (`allow update, delete: if false`) — including legitimate correction paths.
* **Whole-school read of history** with no field-level filtering and no query limit; `getGenerationHistory` has no
  `orderBy`/`limit`, so every dashboard load pulls the school's entire history.
* **`app/storage.rules` does not exist** while `app/src/services/storage.ts` uploads to
  `schools/{schoolId}/documents/{filename}` — and that filename is derived from `subject_grade_docType_Tterm`,
  so two teachers generating the same document overwrite each other with no versioning.
* **`app/src/services/firestore.rules` lives inside `src/` with no deployment wiring** — there is no
  `firebase.json` anywhere in the repo, so these rules are aspirational until someone pastes them into the console.
* **`app/src/services/firestore.indexes.json` is cargo-culted from another project**: it defines indexes for
  `posts`, `lesson_plans`, `weekly_forecasts`, `questions`, `lesson_slides`, `vacancies` and `notes` — collections
  that do not exist here — and none for `generated_materials`, the only collection the app queries.
* **`deploy/main.py` fails open**: `REQUIRE_AUTH` defaults to `"0"` and `ALLOWED_ORIGINS` defaults to `*`
  (lines 70, 88). The docstring tells you to set them, but the default posture is "public document generator,
  any origin". Its deploy instructions also reference a `service/` directory that is now `deploy/`, so the
  documented `gcloud` commands are wrong.

### 9. A 38 MB static bundle with a cache that never invalidates.

```
$ du -sh app/public/curriculum data  →  38M
app/public/curriculum/b9_schedules.json   4,853,239 bytes
app/public/curriculum/b8_schedules.json   4,840,200 bytes
```

The app fetches whole-grade files (`b4_schedules.json` = 3.2 MB) even when the user wants one subject's scheme,
and `IndicatorListPage` loads all 517 B4 indicators to render a list. Three compounding problems:

1. **No chunking.** `docs/TODO.md` already flags this ("Chunk the 38 MB curriculum bundle into per-grade-subject
   files (~50 KB)") — it is the single biggest UX lever for Ghanaian mobile data.
2. **`CacheFirst` with a 30-day `maxAgeSeconds` and no revision key** (`app/vite.config.ts`). Rebuild the
   curriculum and every returning user keeps the old copy for a month, because the filename never changes.
   `public/curriculum/_BUILD_REPORT.json` is committed and would have been a perfect cache-busting key — it is
   never read.
3. **Everything ships in the deployed bundle**, so a Vercel build uploads 38 MB of JSON on every deploy regardless
   of what changed.

### 10. No tests, no CI, no gates.

* No `.github/` directory at all: no workflow runs `npm run build`, `tsc`, `oxlint`, `validate_app_curriculum.py`
  or `boot-check`. A one-line CI job would have caught finding #1 on the first push.
* The only files matching `test_*` are `scripts/inspect/test_parse.py`-style ad-hoc debug scripts — no pytest, no
  vitest, no assertion framework, no fixtures.
* Nothing runs `scripts/validate_app_curriculum.py` (which is genuinely good — see below) automatically.

For a product whose value proposition is *"the data is audited"*, the absence of any automated check between a
pipeline run and a school downloading a document is the risk that matters.

---

## P2 — medium severity and maintainability

### 11. Copy-paste is the dominant design pattern.

| Duplication | Evidence | Cost |
|---|---|---|
| 13 subject modules | A diff between any two non-math modules shows **20–22 changed lines out of 128**; `MathModule` differs by 55 | ~1,500 lines that should be ~150 (a table of `{id, displayName, grades, capabilities, filterId, calloutLabel}` + one factory) |
| 8 math Word builders | `scripts/build/build_math_b2..b9_word_document.py` — 324 lines each, ~2,600 lines total; the B4→B5 diff is grade strings | One script with `--grade` |
| 16 backfill scripts | `scripts/backfill/backfill_b{1..9}_*` — one per grade, 113–178 lines each | Parameterise by grade |
| Indicator fetch/mapping | The identical 15-line fetch+remap exists in `useCurriculum.ts` **and** in all 13 modules | One `fetchIndicators(grade, subjectId)` |

This is not just tidiness — it is the mechanism that produced findings #4 and #6. The `math` subject-id mismatch
exists because the id was typed into 14 places; `schoolContext` is ignored in 13 places because every module was
copied from a module that ignored it. Fixing anything today costs 13 edits, and the next fix will cost 13 more.

### 12. The "Python is the spec, TypeScript is the runtime" promise has already broken.

| Concern | Python (`ncos/kernel/interface.py`) | TypeScript (`app/src/kernel/`) |
|---|---|---|
| `load_indicators` | **synchronous**, `-> list[Indicator]` | **`async Promise<Indicator[]>`** |
| Record of Work | not in the contract | `generateRecordOfWork()` required |
| Question bank | `generate_questions()` (sync, returns `Question[]`) | `generateQuestionsDoc()` (async, returns `MaterialDoc`) **and** `generateQuestions()` returning `any[]` |
| Registration | `module.json` manifest + `interface_version: "1.0"` gate | direct import, **no version, no manifest** |
| Capability lookup | from the manifest, raises `KeyError` for unknown subject | from the class field, returns `false` |

`docs/ARCHITECTURE.md` and `.kiro/steering/project.md` both sell the mirroring as a core principle. It is already
untrue, and nothing detects the drift because the Python side has no tests either.

### 13. `schoolContext` — plumbed, fetched, and thrown away.

```
$ grep -rn "schoolContext" app/src/modules app/src/drivers | wc -l
0
```

`useGenerate` performs two sequential Firestore reads (`getUser` → `getSchool`) on every download to build
`{ schoolName, teacherName }`, passes it into `GenerationRequest`, and **not one consumer reads it**. Generated
documents therefore have no school header, no teacher name, no term/week cover block, no signature lines,
despite `scripts/generate_schemes.py` producing exactly those fields in the printed books. It also means three
extra Firestore round-trips (the `getUser` call is duplicated at `useGenerate.ts:33` and `:88`) on the critical
path of the app's main action, for data that is discarded.

### 14. The documentation actively misleads.

| Doc | Says | Reality |
|---|---|---|
| `README.md` | "React portal UI — `app/src/` — **empty**, ready to scaffold" | 3,100 lines across 45 files |
| `README.md` | "Firestore upload script, Firebase Auth integration, Question bank — not built" | Auth exists; the upload script does not; questions are half-built |
| `docs/TODO.md` | `python tools/build_app_curriculum.py` | Lives at `scripts/build_app_curriculum.py` |
| `docs/TODO.md` | "Verify `yarn build`" | The project uses **npm** |
| `docs/TODO.md` | "Enable `REQUIRE_AUTH=1` on the deployed Material Service" | The service (paths `service/…`) is not in this repo; `deploy/` is documented as unused |
| `scripts/_paths.py` | `APP_CURRICULUM = … # build output, gitignored` | It is committed — 38 MB of it |
| `scripts/build_app_curriculum.py` | "the app (`app/src/hooks/useCurriculum.js`) serves…" | The file is `app/src/services/useCurriculum.ts` |
| `.kiro/steering/project.md` | "**Not yet built:** React app (`app/` is empty)" | Same as above — and this file is `inclusion: always` context for the agent |
| `docs/REPO_ANALYSIS_REPORT.md`, `APP_BUILD_PLAN.md` | Analyse a pre-restructure repo including `saas-files.zip` | Historical; no banner saying so |
| `app/README.md` | Vite boilerplate | Should describe the app |

An always-on steering file that is wrong about what exists is worse than no steering file: it is the context every
future agent session will reason from.

### 15. Repository hygiene.

* **Tracked build artefacts:** `ncos/__pycache__/__init__.cpython-313.pyc`, `ncos/kernel/__pycache__/…`,
  `scripts/__pycache__/_paths.cpython-312.pyc`, `scripts/__pycache__/generate_schemes.cpython-312.pyc`.
* **No root `.gitignore`** (only `app/.gitignore`), so `__pycache__`, `.venv/`, `.pytest_cache/`, ruff caches and
  `dist/` chatter will be committed by default.
* **One squashed commit** (`18517b1`) for 828 files and 132 MB of data + generated curriculum — no history,
  no blame, no way to bisect a data regression.
* **44 MB of source PDFs** in-tree; fine for provenance, but it is why `.git` alone is 44 MB.
* **`data/reference/` is a second, divergent copy** (189 JSONs vs 148 in `data/curriculum/`), and
  `scripts/_paths.py` makes it a silent fallback: *"Order is significant — CURRICULUM is checked first"*. A file
  missing from the primary set is transparently served from a copy the comment itself calls "partly divergent".
  Duplicate sources of truth plus a silent fallback is how wrong curriculum reaches a classroom.
* **`scripts/_compat.py` monkey-patches `builtins.open` globally** to redirect bare-filename reads. It is a
  reasonable migration hack, honestly documented — but it means any script that calls `open_compat()` changes I/O
  behaviour process-wide, which is exactly the kind of thing that makes a "one-shot" script unfixable later.

### 16. Configuration is undocumented and untyped.

`VITE_FIREBASE_API_KEY` and friends are referenced in `app/src/services/firebase.ts` and appear **nowhere** in any
`.md`, `.json` or `.env` file in the repo. There is no `.env.example`, no `src/vite-env.d.ts` declaring
`ImportMetaEnv`, and no mention of a Firebase project id, auth domain or bucket anywhere. I verified the failure
mode: `initializeApp({apiKey: undefined, …})` does **not** throw, so the app boots and only fails later with an
opaque `auth/invalid-api-key` at the first Firestore call — the least debuggable version of "misconfigured".

Also in this bucket:

* The PWA manifest (`app/vite.config.ts:43-44`) references `/icon-192.png` and `/icon-512.png`; **neither exists**
  in `app/public/` (only `favicon.svg` and `icons.svg`), so installability and the install UI are broken.
* `app/index.html` still has `<title>app</title>`, no meta description, no `theme-color`, despite a documented
  brand palette.
* Unused assets shipped: `app/src/assets/hero.png`, `react.svg`, `vite.svg`, `public/icons.svg`.
* `.gitignore` covers `.env.local` but not `.env` — the more commonly used filename is unprotected.
* `vercel.json` (SPA rewrites) sits in `app/` with no root config, so the Vercel project root must be set to
  `app/` — a requirement documented nowhere, and a plausible explanation for a project that is "deployed" while
  its build is red.

### 17. UX, robustness and accessibility rough edges.

* **No error boundary.** `registry.get(params.subject)` (`GeneratePage.tsx:45`) throws during render for an
  unknown subject; any render-phase throw blanks the whole app.
* **The subject dropdown shows module ids** (`english-language`, `creative-arts-design`) even though every module
  carries a `displayName`. It also isn't filtered by the selected document type, so "Question Bank" is offered for
  12 subjects that cannot produce one — you find out by clicking and reading an error.
* **`useIndicators` errors are ignored on the generate page** (only `loading` is destructured), so a failed fetch
  looks like an empty dropdown.
* **`downloadBlob` revokes the object URL synchronously** (`docx.ts:109-110`) — the classic Safari/Firefox
  download race; append the anchor and revoke on a `setTimeout`.
* **Errors after success**: `recordGeneration` runs *after* the download and its failure surfaces as a red
  "permission denied" panel under a document that already downloaded fine.
* **No pagination, search or virtualisation**: `IndicatorListPage` renders every indicator of a grade (up to 590),
  and the indicator `<select>` renders every option with a fixed `substring(0, 100)` truncation that appends
  `...` even to short strings.
* **Accessibility**: labels are not associated with controls (no `htmlFor`/`id`), tables have no `caption` or
  `scope`, status is conveyed by colour only, no skip link, no focus-visible styling.
* **The Tailwind theme is decorative**: `index.css` defines `--color-ncos-green`, `--font-display`, etc. — then
  every component hardcodes `bg-[#1B4332]`, `text-[#C89B3C]`. Changing the brand means a repo-wide find/replace.
* **No i18n scaffolding** for a product aimed at Ghanaian basic schools; UI strings are inline English literals.
* **No offline data layer**: the app is sold as offline-first, but the *only* persistence is the service worker's
  URL cache; Firestore is used without `persistentLocalCache`, so history and school data need network.

---

## What's genuinely good (and worth protecting)

1. **`scripts/validate_app_curriculum.py` is excellent.** It asserts indicator-id uniqueness, subject
   referential integrity, numeric strand numbers (calling out the exact UI bug it prevents), count agreement and
   more — and it passes today, printing 4,040 indicators / 13,140 lessons / 3,212 scheme rows. This is the repo's
   most valuable engineering artefact after the data itself. It should run in CI and in the Vercel build.
2. **The data is clean.** I profiled all 13,140 lesson records: `0` records with empty required fields except 31
   missing `sub_strand`, `4` placeholder-ish records, no empty `resources`. The audit trail
   (`data/audit/audit_a_results.json`: 76/76 PASS) is real, and the one weak spot is honestly recorded
   (mathematics B1 PDF cross-check: 10 hit / 14 miss = 41.7%).
3. **The kernel idea is right.** Content separated from rendering, a single `MaterialDoc` crossing the boundary,
   driver-agnostic blocks — this is the correct shape, and it is *already* paying off: `docx.ts` is 111 lines and
   renders four block types generically. The `EquationBlock` placeholder and the `CalloutBlock` design show real
   foresight.
4. **The registry's design is right even though its inputs are empty** — exclusion + a boot report is exactly the
   pattern that should be used; it just needs modules that can actually fail.
5. **`deploy/main.py`'s security commentary** (allow-lists, `shell=False` argv, length-bounded free text, the
   note about Cloud Run buildpacks grabbing `app/package.json`) is more thoughtful than most production code.
   The defaults are wrong, but the reasoning is not.

---

## Opportunities, ranked by leverage

1. **Make the portal produce what the books produce.** The 13,140 authored lesson records are the moat; the
   portal currently ignores them. Ship per-indicator lesson payloads in the bundle and have
   `generateLessonPlan` emit `Starter / Main / Plenary / Assessment / Competencies / Resources / RP Knowledge` —
   the block types already exist. This single change is the difference between "a thin generator" and "the books,
   on demand, branded per school".
2. **Chunk the bundle per grade+subject** (~50 KB each) and derive a `?v=` cache key from a content hash so the
   service-worker cache invalidates. This is the highest-value performance work for the target network.
3. **Introduce one CI workflow** running `tsc -b`, `oxlint`, `validate_app_curriculum.py` and `boot-check`. Then
   the P0 list cannot silently return.
4. **Fix the publish path**: `schoolId` on create, `list` semantics for history, a `storage.rules`, and a
   deployment-wired rules/index file. Add pagination + `orderBy` to history.
5. **Add a real onboarding flow**: first sign-in asks for school name and writes `schools/{id}` + `users/{uid}`,
   which unblocks self-serve sales (the stated #1 business priority) and makes the dashboard meaningful.
6. **Collapse the duplication** so the next fix is one edit: a `SubjectModule` factory + a subject descriptor
   table in TS, and `--grade` parameters for the Python builders. Then delete the 8 duplicate math builders and
   16 backfills from the tree (they are reproducible from the parameterised script).
7. **Then** the interesting product bets (visualisation engine, offline packs) — they are much safer to build on
   a repo with a green build, a CI gate, and one generator instead of thirteen.

---

## Suggested order of work

| Day | Work |
|---|---|
| 1 | Fix the 36 TS errors; add `npm run build` to CI. **The app becomes deployable.** |
| 1 | Fix `math` → `mathematics` (or accept an alias) and implement real `validate()` for every module; repair `tools/ncosctl.py`. |
| 2 | Fix the history read/write key mismatch; add `schoolId` to the create rule; write `storage.rules`; wire rules + indexes into a `firebase.json`. Add `.env.example` and `vite-env.d.ts`. |
| 3 | Wire the enriched lessons into `generateLessonPlan`; populate `extra.sub_skill` (or delete the `n/a` callout); fix or gate the Question Bank. |
| 4 | Chunk the bundle by grade+subject; add a content-hash cache key; regenerate and re-validate. |
| 5 | CI hardening: `oxlint`, validator, `boot-check`, plus the first real tests — a `validate()` test per module and one snapshot test of `MaterialDoc → docx` for a known indicator. |
| 6–10 | Docs truth pass (README, TODO, `.kiro/steering`, delete or banner the historical reports), onboarding flow, then start the deduplication in #6 above. |

---

## Appendix — how to reproduce the key findings

```bash
# 1. The app does not compile
cd app && npm install && npm run build        # → exit 2, 36 × error TS

# 2. The documented kernel CLI is broken
make boot-check                               # → ModuleNotFoundError: ncos.kernel.drivers

# 3. Nothing validates; 13/13 modules "healthy"
npx esbuild _boottest.ts --bundle --platform=node --format=esm && node /tmp/boottest.mjs

# 4. math resolves to zero indicators
node -e "const i=require('./app/public/curriculum/b4_indicators.json');
         console.log(i.filter(x=>x.subjectId==='math').length)"   # → 0

# 5. Branding is fetched and discarded
grep -rn schoolContext app/src/modules app/src/drivers           # → no hits

# 6. Question bank data is never bundled
ls app/public/curriculum/questions   # → No such file or directory
ls data/questions/mathematics        # → B4.json (never copied into the bundle)

# 7. Bundle size / cache config
du -sh app/public/curriculum && grep -n "CacheFirst\|maxAgeSeconds" app/vite.config.ts

# 8. Repo hygiene
git ls-files | grep -c pycache ; ls .gitignore 2>&1
```

*(A one-line change was made during this review: `app/vite.config.ts` now sets
`server.allowedHosts`/`preview.allowedHosts` so the dev server accepts the sandbox preview hostname instead of
returning `403 Blocked request`. Nothing else in the repository was modified — all other findings above are
reported, not fixed.)*

---

# Addendum — findings from restructuring the docs against the dataset

*Added 2026-09-17 after `README.md`, `docs/TODO.md` and `.kiro/steering/project.md`
were rewritten around a machine-derived inventory (`scripts/build_inventory.py` →
`data/inventory.json`, `make inventory`).*

Building the inventory forced every headline number to be traced to a file. Five
new findings came out of it, and two of them are worse than anything in the original
review because they affect **what a teacher is served**, not just what compiles.

## 18. 🔴 The app serves curriculum that was never audited.

The docs claim "4,040+ NaCCA indicators" and "148 curriculum JSON databases".
Tracing both:

* **"148 databases" = 75 databases + 73 summaries.** 148 is a count of *files*.
* **4,040 indicators is L3** (the app bundle). The audited layer, L1
  (`data/curriculum/`), contains **3,095**.

The difference is 8 subject-grades that exist **only** in `data/reference/`, the
copy `scripts/_paths.py` itself calls "partly divergent":

```
computing B4 (27) · B5 (81) · B6 (98)      french B4 (88) · B5 (90) · B6 (89)
kindergarten KG1 (169) · KG2 (170)
```

`scripts/build_app_curriculum.py` finds them because `DB_SEARCH` falls back to
`REFERENCE` **silently**. Nothing logs the fallback, `validate_app_curriculum.py`
validates internal consistency only (it cannot know a file came from the fallback),
and no audit in `data/audit/` covers them. Add `english-language B5`, which exists
in L1 only as a *summary* (the database lives in reference), and 9 of the app's 84
subject-grades — 945 of its 4,040 indicators — are not backed by the audited
extraction. (The other 75 pairs agree exactly: 3,095 = 3,095.)

For a product whose entire pitch is "the data is audited", this is the most
important finding in the review. It is also invisible from the outside: the bundle
validates, the files parse, the numbers look right.

**Fix:** either audit and promote those pairs into `data/curriculum/`, or delete
`data/reference/` and make the missing files a build failure. A silent fallback
cannot be the permanent state. Tracked as L1-1 in `docs/TODO.md`.

## 19. 🟠 The "enrichment" in L1 is four constants per subject-grade.

`competencies`, `resources`, `keywords` and `assessment` are present on every
indicator record, which makes them look like per-indicator content. They are not:

| Field | Distinct values in `mathematics_B4` (71 indicators) |
|---|---|
| `competencies` | 1 (`"Critical Thinking and Problem Solving; Communication and Collaboration; …"`) |
| `resources` | 1 (`"NaCCA approved textbook; TLMs; ICT tools; community resources"`) |
| `keywords` | 1 (`"mathematics, b4, upper-primary"`) |
| `assessment` | 1 (`"Class exercises; oral questions; practical performance; SBA"`) |

Identical pattern in science B4 (24/24) and career-technology B7 (43/43): 1 distinct
value each. `keywords` is literally `{subject}, {grade}, {band}`.

Any document that prints these under an indicator — as the portal does for
`resources`/`assessment`, and as the book templates do — repeats 71 identical lines
per subject-grade. It reads as padding because it is padding.

## 20. 🟠 L2 is a filled template, not 13,140 authored lesson plans.

Distinct values ÷ lesson slots across all 13,140 slots:

| Field | Ratio | Reading |
|---|---|---|
| `starter` | 75.3% | genuinely varied per lesson |
| `main` | 41.3% | activity text varies; the time budget is constant |
| `perf_indicator` | 25.1% | derived: embeds `ind_desc` in 12,884/13,140 slots |
| `ind_desc` | 24.2% | ~4 slots share each indicator |
| `session_title` | 15.5% | positional (`"Session 2 of 3 — Practice"`) |
| `assessment` | 1.3% | per-subject constant |
| `plenary` | 0.7% | per-subject constant |
| `rpk` | 0.6% | per-subject constant |

This does not make the books wrong — the books are real and usable, and the
per-lesson `starter`/`main` content is real. But "13,140 fully-written lesson plans"
(from `docs/REPO_ANALYSIS_REPORT.md`, repeated in `.kiro/steering/project.md`)
overstates it, and any plan that prices authoring work per lesson must use the
fidelity numbers, not the slot count.

## 21. 🟠 `package_books.py` would produce an empty catalogue, and the book counts are unverifiable.

`scripts/package_books.py` scans `data/books/` for `Basic{N}_{Subject}_Lesson_Plans_Full_Year.docx`.
`data/books/` contains two files, neither matching: a Scheme of Learning and a Record
of Work for Mathematics B4. The 73–77 lesson-plan volumes its docstring cites are not
in the repository (`dist/` is gitignored and was never committed).

So three separate claims cannot be checked from this repo:

| Claim | Where | Reality |
|---|---|---|
| "the 77 lesson-plan DOCX volumes" | `package_books.py` docstring | 0 are present; the script's `canonical` list would be empty |
| "73 lesson plan books … are all finished and unsold" | old `docs/TODO.md` | unverifiable here; L2 has 73 subject-grades, so 73 is a plausible *regeneration* count |
| "73 schemes, 365 records of work" | old `docs/TODO.md` | 365 matches nothing derivable — `--per-term` over 73 subject-grades × 3 terms = 219 |

The generators and their inputs exist. The outputs must be regenerated, and any
count stated before that is a guess.

## 22. 🟡 Two documents referenced by the backlog did not exist.

`docs/TODO.md` linked `docs/SCHOOL_WORKSPACE.md` for "generation history" and
`docs/VISUALIZATION_ENGINE.md` for the largest planned feature. Neither file exists;
`VCTM` — cited as giving "the assessment architecture" — appears nowhere in the
repository except that one line. The restructured `TODO.md` describes the work
inline instead of pointing at phantoms.

## What changed in this pass

| File | Change |
|---|---|
| `scripts/build_inventory.py` | **New.** Derives L1/L2/L3/reference totals, per-grade and per-subject coverage, lesson fidelity, dataset-vs-app agreement, and doc-link integrity. Exits non-zero when the app cannot serve the dataset. |
| `data/inventory.json` | **New (generated).** The numbers every doc now quotes. |
| `docs/DATA_MODEL.md` | **New.** Canonical definition of the three layers, the reference divergence, id conventions, invariants. |
| `README.md` | Rewritten around the three layers and the real state of the app. Correct paths (`scripts/`, not `tools/`), correct package manager (`npm`, not `yarn`), honest "what is broken" section, documentation index with per-doc status. |
| `docs/TODO.md` | Restructured by dependency (P0 build blockers → P1 book/portal parity → L1/L2 data work → P2 structural debt → P3 product bets). Added items the inventory surfaced: the reference decision, the missing L1 summaries, the malformed reference summaries, the enrichment-constant problem, and the L2 fidelity decision. |
| `.kiro/steering/project.md` | Rewritten. It previously told every agent session that `app/` was empty and that `tools/` was the pipeline root. Now carries the derived numbers and the "fail loud" rule that P0-2 enforces. |
| `Makefile` | Added `make inventory` and `make check` (which includes `npm run build`, so a red build cannot be discovered first in production). |
| `app/vite.config.ts` | (Earlier in this review) dev/preview servers accept the sandbox host, unblocking the preview. |

Still unfixed, deliberately: every P0/P1 code finding above. The restructure changed
what the repository *says about itself* and gave the claims a single source; it did
not change the code. `make inventory` now fails on the `math`/`mathematics` mismatch,
which is the intended behaviour — it should stay red until P0-3 is fixed.
