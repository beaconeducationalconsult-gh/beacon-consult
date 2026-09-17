# NCOS Architecture

## The Core Idea

NCOS is structured like an operating system because the problem has the
same shape: many subjects (processes) need controlled access to shared
curriculum data (the file system) through one stable interface (the
kernel), without any of them needing to know about each other.

The difference from a traditional OS: **there is no server process**. The
"kernel" runs entirely in the browser. Document generation happens
client-side using the `docx` npm package. Firebase handles auth, storage,
and the database. Vercel serves the static React app.

---

## Hosting Model

```
┌─────────────────────────────────────────────────────────┐
│  BROWSER (Vercel-hosted React app)                       │
│                                                          │
│  app/src/kernel/     ← document model (JS)              │
│  app/src/modules/    ← subject logic (JS)               │
│  app/src/drivers/    ← docx.js renderer                 │
│  app/src/services/   ← Firestore + Auth + Storage       │
│                                                          │
│  Teacher clicks Generate                                 │
│    → module builds a MaterialDoc (pure JS objects)      │
│    → docx driver turns it into .docx bytes              │
│    → browser triggers download                          │
│    → metadata saved to Firestore                        │
│    → file optionally saved to Firebase Storage          │
└─────────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
  Firebase Auth             Firestore
  (who you are)         (curriculum data,
                         usage history,
                         school records)
```

No Flask. No Docker. No Cloud Run. No server to operate.

---

## The OS Metaphor (still applies, shifted to the browser)

| OS Concept        | NCOS Equivalent                                      |
|-------------------|------------------------------------------------------|
| Kernel            | `app/src/kernel/` — document model + module contract |
| Drivers           | `app/src/drivers/docx.ts` — renders MaterialDoc      |
| Kernel modules    | `app/src/modules/<subject>/` — one per subject       |
| File system       | Firestore + `data/curriculum/` (the data layer)      |
| Boot sequence     | Module registry validates at app startup             |
| Package manager   | Curriculum versioning (designed, not yet built)      |
| User space        | React UI in `app/src/ui/`                            |
| Syscall boundary  | `app/src/services/` — Firestore reads, Auth checks   |

The Python `ncos/` package is retained as the **reference specification**
and **data pipeline host** — it is never deployed. The JavaScript
`app/src/kernel/` mirrors its types and contracts exactly.

---

## Data Flow

```
NaCCA Source PDFs
      │
      ▼
scripts/ingest/          ← parse PDFs into raw indicator records
      │
      ▼
data/curriculum/         ← 148 JSON curriculum databases (source of truth)
data/lessons/            ← 73 JSON enriched lesson records (13,140 lessons)
      │
      ├──[scripts/build_app_curriculum.py]──► app/public/curriculum/
      │                                        (static JSON, offline-capable)
      │
      └──[scripts/upload_to_firestore.py]───► Firestore
                                               (queryable, live-updated)
```

The React app reads from **both** sources depending on context:
- `app/public/curriculum/` for offline / cached indicator browsing
- Firestore for user records, school data, generation history, auth-gated content

---

## Document Generation (client-side)

The `MaterialDoc` is a pure data structure — no rendering code, no file
format knowledge. It is the payload that crosses the boundary between a
subject module and a document driver.

```
Indicator (from Firestore or static JSON)
      │
      ▼
SubjectModule.generateLessonPlan(request)
      │
      ▼
MaterialDoc { title, sections: [Section { title, blocks: [Block] }] }
      │
      ▼
DocxDriver.render(doc) → Uint8Array
      │
      ▼
Browser download / Firebase Storage upload
```

Block types: `TextBlock`, `TableBlock`, `CalloutBlock`, `EquationBlock`.
Subject-specific fields that don't fit the generic schema go in
`Indicator.extra` — the module interprets them; the kernel never needs to.

---

## Module Contract

Every subject module (JS and Python) implements the same interface:

```typescript
interface SubjectModule {
  id: string
  displayName: string
  grades: string[]
  capabilities: Set<string>

  loadIndicators(grade: string): Promise<Indicator[]>
  validate(): string[]                                    // [] = clean
  generateLessonPlan(request: GenerationRequest): MaterialDoc
  generateSchemeOfWork(grade: string, term: number): MaterialDoc
  generateQuestions?(indicator: Indicator, count: number): Question[]
}
```

A module that fails `validate()` is excluded from the registry at startup
and never reached by any generation request. Failures are visible on the
boot report, not silently swallowed.

---

## What Lives Where

| Concern                      | Location                        |
|------------------------------|---------------------------------|
| JS document model + contract | `app/src/kernel/`               |
| Subject logic (JS)           | `app/src/modules/<subject>/`    |
| docx rendering               | `app/src/drivers/docx.ts`       |
| Firestore / Auth / Storage   | `app/src/services/`             |
| React UI                     | `app/src/ui/`                   |
| Python reference spec        | `ncos/kernel/interface.py`      |
| Python module reference      | `ncos/modules/math/`            |
| Curriculum source data       | `data/curriculum/`, `data/lessons/` |
| Static app bundle            | `app/public/curriculum/`        |
| Data pipeline scripts        | `scripts/`                      |
| Documentation                | `docs/`                         |
| Archived Flask service       | `deploy/` (not used)            |

---

## Key Design Decisions

**No server** — Vercel + Firestore is the deployment target. Python Flask
and Docker are retired as runtime components. The `deploy/` folder is an
archive, not a deployment artifact.

**Content separated from rendering** — subject modules produce
`MaterialDoc` objects (typed blocks), never `.docx`. The `DocxDriver` is
the only code that knows about the docx format. Adding a PDF driver or a
Google Slides driver never requires touching any subject module.

**Python as spec, JavaScript as runtime** — the Python `ncos/` package
defines the data shapes and module contract authoritatively. The JS
`app/src/kernel/` mirrors it. When the two diverge, the Python spec wins.

**Fail-loud-at-boot** — broken modules are caught at registry startup,
recorded in the boot report, and excluded from routing. A bad module
never silently produces a wrong document.

**Offline-first data** — `app/public/curriculum/` is a pre-built static
JSON bundle. Browsing indicators and generating documents works without a
live Firestore connection. Only auth-gated writes (save history, upload
file) require network.

**`Indicator.extra` as the extension point** — subject-specific fields
(a Math "sub-skill", a Language "genre") live in `extra` rather than
forcing every subject into one shared schema.
