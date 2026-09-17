# Beacon Consult App — Complete Build Plan

This document is the single guide for building the React portal from the
current empty scaffold to a fully working, deployed SaaS. Work the phases
in order. Each phase has a clear definition of done before you move on.

**Stack reminder:** React 19 + Vite + TypeScript + Tailwind CSS v4 +
Firebase (Firestore, Auth, Storage) + docx npm package. No server.
Document generation is entirely client-side.

---

## Phase 1 — The Kernel (JavaScript port of `ncos/kernel/`)

**Goal:** reproduce the Python data model and module contract in
TypeScript. Nothing renders yet — this is pure types and logic.

### 1.1 — Types (`app/src/kernel/types.ts`)

Port every dataclass from `ncos/kernel/interface.py` verbatim into
TypeScript interfaces and types.

```ts
// app/src/kernel/types.ts

export interface Indicator {
  code: string           // e.g. "B4.1.1.1.1"
  strand: string
  subStrand: string
  contentStandard: string
  text: string
  grade: string
  subject: string
  extra: Record<string, unknown>  // subject-specific fields
}

export interface GenerationRequest {
  indicator: Indicator
  grade: string
  term: number
  week: number
  schoolContext: Record<string, unknown>
  options: Record<string, unknown>
}

// ── Block types ───────────────────────────────────────────────
export interface TextBlock {
  type: 'text'
  text: string
  style: 'body' | 'heading' | 'bullet'
}

export interface TableBlock {
  type: 'table'
  headers: string[]
  rows: string[][]
}

export interface CalloutBlock {
  type: 'callout'
  label: string   // e.g. "Safety note", "Core point"
  text: string
}

export interface EquationBlock {
  type: 'equation'
  latex: string
}

export type Block = TextBlock | TableBlock | CalloutBlock | EquationBlock

export interface Section {
  title: string
  blocks: Block[]
}

export interface MaterialDoc {
  title: string
  sections: Section[]
  meta: Record<string, unknown>
}

export interface Question {
  prompt: string
  options: string[] | null   // null for open-ended
  answer: string
  difficulty: 'reinforcement' | 'core' | 'extension'
}
```

### 1.2 — SubjectModule interface (`app/src/kernel/SubjectModule.ts`)

```ts
// app/src/kernel/SubjectModule.ts
import type { GenerationRequest, Indicator, MaterialDoc, Question } from './types'

export interface SubjectModule {
  id: string
  displayName: string
  grades: string[]
  capabilities: Set<string>

  loadIndicators(grade: string): Promise<Indicator[]>
  validate(): string[]   // returns [] if clean, list of problems otherwise
  generateLessonPlan(request: GenerationRequest): MaterialDoc
  generateSchemeOfWork(grade: string, term: number): MaterialDoc
  generateQuestions?(indicator: Indicator, count: number): Question[]
}
```

### 1.3 — Module registry (`app/src/kernel/registry.ts`)

The registry runs at app startup. Any module whose `validate()` returns
problems is excluded and logged — never silently wrong.

```ts
// app/src/kernel/registry.ts
import type { SubjectModule } from './SubjectModule'

export interface BootEntry {
  moduleId: string
  ok: boolean
  detail: string
}

export interface BootReport {
  loaded: string[]
  failed: BootEntry[]
  durationMs: number
}

class ModuleRegistry {
  private modules = new Map<string, SubjectModule>()
  bootReport: BootReport = { loaded: [], failed: [], durationMs: 0 }

  register(module: SubjectModule): void {
    const t0 = performance.now()
    const problems = module.validate()
    if (problems.length > 0) {
      this.bootReport.failed.push({
        moduleId: module.id,
        ok: false,
        detail: problems.join('; '),
      })
      console.warn(`[registry] ${module.id} failed validation:`, problems)
    } else {
      this.modules.set(module.id, module)
      this.bootReport.loaded.push(module.id)
    }
    this.bootReport.durationMs += performance.now() - t0
  }

  get(subjectId: string): SubjectModule {
    const m = this.modules.get(subjectId)
    if (!m) throw new Error(`'${subjectId}' is not loaded — check boot report`)
    return m
  }

  capableOf(subjectId: string, capability: string): boolean {
    return this.modules.get(subjectId)?.capabilities.has(capability) ?? false
  }

  listLoaded(): string[] {
    return [...this.modules.keys()]
  }
}

// Singleton — import this everywhere
export const registry = new ModuleRegistry()
```

### 1.4 — Barrel export (`app/src/kernel/index.ts`)

```ts
export * from './types'
export * from './SubjectModule'
export { registry } from './registry'
export type { BootReport, BootEntry } from './registry'
```

**Definition of done:** `tsc --noEmit` inside `app/` passes with no
errors. No UI yet.

---

## Phase 2 — The Math Module (reference implementation)

**Goal:** port `ncos/modules/math/module.py` to TypeScript. This is the
proof that the JS kernel works end to end, exactly as the Python module
was the proof for the Python kernel.

### 2.1 — Curriculum data format

The math module reads from `app/public/curriculum/math/B4.json`.
Run the build script first to generate it:

```powershell
# from repo root
make build-curriculum
```

The JSON shape it produces (mirrors the Python module's expectation):

```json
{
  "grade": "B4",
  "subject": "math",
  "indicators": [
    {
      "code": "B4.1.1.1.1",
      "strand": "1. Number",
      "sub_strand": "Sub-strand B4.1.1",
      "content_standard": "Demonstrate understanding of...",
      "text": "Count, read and write numbers...",
      "extra": { "sub_skill": "Number recognition" }
    }
  ]
}
```

### 2.2 — Module implementation (`app/src/modules/math/MathModule.ts`)

```ts
// app/src/modules/math/MathModule.ts
import type { SubjectModule } from '../../kernel/SubjectModule'
import type {
  GenerationRequest,
  Indicator,
  MaterialDoc,
} from '../../kernel/types'

export class MathModule implements SubjectModule {
  id = 'math'
  displayName = 'Mathematics'
  grades = ['B4']
  capabilities = new Set(['lesson_plan', 'scheme_of_work'])

  async loadIndicators(grade: string): Promise<Indicator[]> {
    const res = await fetch(`/curriculum/math/${grade}.json`)
    if (!res.ok) return []
    const raw = await res.json()
    return raw.indicators.map((i: any) => ({
      code: i.code,
      strand: i.strand,
      subStrand: i.sub_strand,
      contentStandard: i.content_standard,
      text: i.text,
      grade: raw.grade,
      subject: raw.subject,
      extra: i.extra ?? {},
    }))
  }

  validate(): string[] {
    // Grade list is hardcoded — nothing to validate at construction time.
    // Real data validation happens in loadIndicators at runtime.
    return []
  }

  generateLessonPlan(request: GenerationRequest): MaterialDoc {
    const { indicator: ind, week, options } = request
    const duration = (options.duration_minutes as number) ?? 60

    return {
      title: `Lesson Plan — ${ind.strand} — ${ind.grade} Wk ${week}`,
      sections: [
        {
          title: 'Indicator',
          blocks: [{ type: 'text', text: `${ind.code}: ${ind.text}`, style: 'body' }],
        },
        {
          title: 'Objectives',
          blocks: [
            {
              type: 'text',
              text: `By the end of the lesson, learners will be able to ${ind.text.toLowerCase()}.`,
              style: 'bullet',
            },
          ],
        },
        {
          title: 'Core Content',
          blocks: [
            { type: 'text', text: ind.contentStandard, style: 'body' },
            {
              type: 'callout',
              label: 'Sub-skill',
              text: (ind.extra.sub_skill as string) ?? 'n/a',
            },
          ],
        },
        {
          title: 'Duration',
          blocks: [{ type: 'text', text: `${duration} minutes`, style: 'body' }],
        },
      ],
      meta: { subject: ind.subject, grade: ind.grade, indicatorCode: ind.code },
    }
  }

  generateSchemeOfWork(grade: string, term: number): MaterialDoc {
    // Indicators are async — caller must pre-load and pass via options
    // or this method is called after indicators are already in state.
    // See Phase 4 (Generate screen) for the calling pattern.
    return {
      title: `Scheme of Work — Mathematics ${grade} Term ${term}`,
      sections: [
        {
          title: 'Indicators covered',
          blocks: [
            {
              type: 'table',
              headers: ['Code', 'Strand', 'Indicator'],
              rows: [], // populated by the Generate screen before calling render
            },
          ],
        },
      ],
      meta: { subject: 'math', grade, term },
    }
  }
}
```

### 2.3 — Register the module (`app/src/modules/index.ts`)

```ts
// app/src/modules/index.ts
// Import and register every subject module here.
// The registry picks up whatever is registered at app startup.
import { registry } from '../kernel'
import { MathModule } from './math/MathModule'

registry.register(new MathModule())

// Add future modules here:
// import { EnglishModule } from './english/EnglishModule'
// registry.register(new EnglishModule())
```

Import this file once in `app/src/main.tsx` (before anything renders):

```ts
// app/src/main.tsx
import './modules'   // ← boots the registry
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

**Definition of done:** open the browser console, type
`import('/src/modules/index.ts')` — no errors. The registry is loaded.

---

## Phase 3 — The docx Driver (`app/src/drivers/docx.ts`)

**Goal:** port `ncos/kernel/drivers/docx_driver.py` to TypeScript using
the `docx` npm package. Takes a `MaterialDoc`, returns a `Blob` that the
browser can download.

```ts
// app/src/drivers/docx.ts
import {
  Document,
  HeadingLevel,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
  Packer,
} from 'docx'
import type {
  Block,
  CalloutBlock,
  EquationBlock,
  MaterialDoc,
  TableBlock,
  TextBlock,
} from '../kernel/types'

// ── Block renderers ──────────────────────────────────────────

function renderTextBlock(block: TextBlock): Paragraph {
  if (block.style === 'heading') {
    return new Paragraph({ text: block.text, heading: HeadingLevel.HEADING_3 })
  }
  if (block.style === 'bullet') {
    return new Paragraph({ text: block.text, bullet: { level: 0 } })
  }
  return new Paragraph({ text: block.text })
}

function renderTableBlock(block: TableBlock): Table {
  const headerRow = new TableRow({
    children: block.headers.map(
      (h) =>
        new TableCell({
          children: [new Paragraph({ children: [new TextRun({ text: h, bold: true })] })],
        })
    ),
  })

  const dataRows = block.rows.map(
    (row) =>
      new TableRow({
        children: row.map(
          (cell) => new TableCell({ children: [new Paragraph({ text: cell })] })
        ),
      })
  )

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [headerRow, ...dataRows],
  })
}

function renderCalloutBlock(block: CalloutBlock): Paragraph {
  return new Paragraph({
    children: [
      new TextRun({ text: `${block.label}: `, bold: true }),
      new TextRun({ text: block.text }),
    ],
  })
}

function renderEquationBlock(block: EquationBlock): Paragraph {
  // Placeholder — swap in MathML or an image renderer here without
  // touching any subject module.
  return new Paragraph({ text: `[equation] ${block.latex}` })
}

function renderBlock(block: Block): Paragraph | Table {
  switch (block.type) {
    case 'text':    return renderTextBlock(block as TextBlock)
    case 'table':   return renderTableBlock(block as TableBlock)
    case 'callout': return renderCalloutBlock(block as CalloutBlock)
    case 'equation': return renderEquationBlock(block as EquationBlock)
  }
}

// ── Main render function ─────────────────────────────────────

export async function renderDocx(doc: MaterialDoc): Promise<Blob> {
  const children: (Paragraph | Table)[] = [
    new Paragraph({ text: doc.title, heading: HeadingLevel.HEADING_1 }),
  ]

  for (const section of doc.sections) {
    children.push(
      new Paragraph({ text: section.title, heading: HeadingLevel.HEADING_2 })
    )
    for (const block of section.blocks) {
      children.push(renderBlock(block))
    }
  }

  const document = new Document({ sections: [{ children }] })
  return Packer.toBlob(document)
}

// ── Convenience download helper ──────────────────────────────

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
```

### Usage example (inline test, before any UI exists)

Add this to `App.tsx` temporarily to prove the whole chain works:

```tsx
import { registry } from './kernel'
import { renderDocx, downloadBlob } from './drivers/docx'

async function testGenerate() {
  const math = registry.get('math')
  const indicators = await math.loadIndicators('B4')
  const indicator = indicators[0]
  const doc = math.generateLessonPlan({
    indicator,
    grade: 'B4',
    term: 1,
    week: 1,
    schoolContext: {},
    options: {},
  })
  const blob = await renderDocx(doc)
  downloadBlob(blob, `test_${indicator.code}.docx`)
}

// Call testGenerate() from a button click to verify
```

**Definition of done:** clicking the test button downloads a real `.docx`
file that opens in Word/Google Docs and looks like a lesson plan.

---

## Phase 4 — Firebase Setup

**Goal:** wire Firebase into the app. No UI yet — just confirm the
connection is live.

### 4.1 — Firebase service files

```
app/src/services/
├── firebase.ts    ← app init (already outlined in scaffold steps)
├── auth.ts        ← sign in / sign out / current user
├── firestore.ts   ← curriculum reads, school reads, history writes
└── storage.ts     ← upload / download generated .docx files
```

**`app/src/services/auth.ts`**

```ts
import {
  GoogleAuthProvider,
  signInWithPopup,
  signOut,
  onAuthStateChanged,
  type User,
} from 'firebase/auth'
import { auth } from './firebase'

const provider = new GoogleAuthProvider()

export const signInWithGoogle = () => signInWithPopup(auth, provider)
export const signOutUser = () => signOut(auth)
export const onAuthChanged = (cb: (user: User | null) => void) =>
  onAuthStateChanged(auth, cb)
```

**`app/src/services/firestore.ts`**

```ts
import {
  collection,
  doc,
  getDoc,
  getDocs,
  query,
  where,
  addDoc,
  serverTimestamp,
} from 'firebase/firestore'
import { db } from './firebase'
import type { Indicator } from '../kernel/types'

// ── School ───────────────────────────────────────────────────
export async function getSchool(schoolId: string) {
  const snap = await getDoc(doc(db, 'schools', schoolId))
  return snap.exists() ? snap.data() : null
}

// ── Generation history ───────────────────────────────────────
export async function recordGeneration(payload: {
  schoolId: string
  userId: string
  subject: string
  grade: string
  indicatorCode: string
  documentType: 'lesson_plan' | 'scheme_of_work' | 'record_of_work'
  filename: string
}) {
  return addDoc(collection(db, 'generated_materials'), {
    ...payload,
    generatedAt: serverTimestamp(),
  })
}

export async function getGenerationHistory(schoolId: string) {
  const q = query(
    collection(db, 'generated_materials'),
    where('schoolId', '==', schoolId)
  )
  const snap = await getDocs(q)
  return snap.docs.map((d) => ({ id: d.id, ...d.data() }))
}
```

### 4.2 — Auth context (`app/src/services/AuthContext.tsx`)

```tsx
import { createContext, useContext, useEffect, useState } from 'react'
import type { User } from 'firebase/auth'
import { onAuthChanged } from './auth'

interface AuthContextValue {
  user: User | null
  loading: boolean
}

const AuthContext = createContext<AuthContextValue>({ user: null, loading: true })

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsub = onAuthChanged((u) => {
      setUser(u)
      setLoading(false)
    })
    return unsub
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
```

Wrap `<App />` in `main.tsx`:

```tsx
import { AuthProvider } from './services/AuthContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
)
```

**Definition of done:** `console.log(auth.currentUser)` in the browser
returns `null` (unauthenticated) without throwing. No Firebase errors in
the console.

---

## Phase 5 — Routing & Shell Layout

**Goal:** the app has real pages and a navigation shell. Teachers can
move between screens.

### 5.1 — Routes

```
/                   → Landing / home (public)
/login              → Sign in page
/dashboard          → School dashboard (auth required)
/generate           → Generate a document (auth required)
/history            → Generation history (auth required)
/curriculum         → Browse curriculum by subject + grade (public)
/curriculum/:grade/:subject  → Indicator list
```

### 5.2 — App.tsx with router

```tsx
// app/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Shell } from './ui/layout/Shell'
import { ProtectedRoute } from './ui/layout/ProtectedRoute'
import { LandingPage } from './ui/pages/LandingPage'
import { LoginPage } from './ui/pages/LoginPage'
import { DashboardPage } from './ui/pages/DashboardPage'
import { GeneratePage } from './ui/pages/GeneratePage'
import { HistoryPage } from './ui/pages/HistoryPage'
import { CurriculumPage } from './ui/pages/CurriculumPage'
import { IndicatorListPage } from './ui/pages/IndicatorListPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Shell />}>
          <Route index element={<LandingPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="curriculum" element={<CurriculumPage />} />
          <Route path="curriculum/:grade/:subject" element={<IndicatorListPage />} />

          {/* Auth-gated */}
          <Route element={<ProtectedRoute />}>
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="generate" element={<GeneratePage />} />
            <Route path="history" element={<HistoryPage />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
```

### 5.3 — Shell layout (`app/src/ui/layout/Shell.tsx`)

```tsx
import { Outlet } from 'react-router-dom'
import { Navbar } from './Navbar'

export function Shell() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-5xl">
        <Outlet />
      </main>
    </div>
  )
}
```

### 5.4 — ProtectedRoute (`app/src/ui/layout/ProtectedRoute.tsx`)

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../services/AuthContext'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-8 text-center">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}
```

**Definition of done:** navigating to `/dashboard` redirects to `/login`
when not signed in. `/curriculum` loads without auth.

---

## Phase 6 — Curriculum Browser

**Goal:** teachers can browse all subjects and grades, read indicators,
without logging in. This works offline (reads from static JSON bundle).

### 6.1 — Build the static bundle first

```powershell
# repo root
make build-curriculum
```

This writes `app/public/curriculum/` — Vite serves it as static files.

### 6.2 — useCurriculum hook (`app/src/services/useCurriculum.ts`)

```ts
import { useEffect, useState } from 'react'
import type { Indicator } from '../kernel/types'

export function useIndicators(grade: string, subject: string) {
  const [indicators, setIndicators] = useState<Indicator[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!grade || !subject) return
    setLoading(true)
    fetch(`/curriculum/${subject}/${grade}.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`No data for ${subject}/${grade}`)
        return r.json()
      })
      .then((data) => {
        setIndicators(
          data.indicators.map((i: any) => ({
            code: i.code,
            strand: i.strand,
            subStrand: i.sub_strand,
            contentStandard: i.content_standard,
            text: i.text,
            grade: data.grade,
            subject: data.subject,
            extra: i.extra ?? {},
          }))
        )
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [grade, subject])

  return { indicators, loading, error }
}
```

### 6.3 — CurriculumPage (`app/src/ui/pages/CurriculumPage.tsx`)

Render a grid of grade × subject cards. Clicking a card goes to
`/curriculum/:grade/:subject`.

### 6.4 — IndicatorListPage (`app/src/ui/pages/IndicatorListPage.tsx`)

Read `:grade` and `:subject` from params, call `useIndicators`, render a
table of indicator codes + strands + descriptions. Each row has a
"Generate lesson plan" button that pushes to `/generate?code=B4.1.1.1.1`.

**Definition of done:** a teacher can browse from `/curriculum` → pick
Mathematics B4 → see the full indicator list without being logged in,
even with the network tab throttled to offline.

---

## Phase 7 — Generate Screen (the core action)

**Goal:** the core teacher workflow — pick a document type, pick an
indicator, click Generate, get a `.docx` download.

### 7.1 — GeneratePage flow

```
1. Select subject  (dropdown — populated from registry.listLoaded())
2. Select grade    (dropdown — populated from module.grades)
3. Select term / week
4. Select indicator (searchable list loaded via useIndicators)
5. Optional: enter school branding (school name, teacher name, class)
6. Click Generate
   → module.generateLessonPlan(request) → MaterialDoc
   → renderDocx(doc) → Blob
   → downloadBlob(blob, filename)
   → recordGeneration(...) to Firestore
```

### 7.2 — useGenerate hook (`app/src/services/useGenerate.ts`)

```ts
import { useState } from 'react'
import { registry } from '../kernel'
import { renderDocx, downloadBlob } from '../drivers/docx'
import { recordGeneration } from './firestore'
import { useAuth } from './AuthContext'
import type { Indicator } from '../kernel/types'

interface GenerateParams {
  subject: string
  grade: string
  term: number
  week: number
  indicator: Indicator
  schoolContext: Record<string, unknown>
}

export function useGenerate() {
  const { user } = useAuth()
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function generate(params: GenerateParams) {
    setGenerating(true)
    setError(null)
    try {
      const module = registry.get(params.subject)
      if (!module.capabilities.has('lesson_plan')) {
        throw new Error(`${params.subject} does not support lesson_plan`)
      }

      const doc = module.generateLessonPlan({
        indicator: params.indicator,
        grade: params.grade,
        term: params.term,
        week: params.week,
        schoolContext: params.schoolContext,
        options: {},
      })

      const blob = await renderDocx(doc)
      const filename = `${params.subject}_${params.grade}_${params.indicator.code}_T${params.term}W${params.week}.docx`
      downloadBlob(blob, filename)

      // Record to Firestore if logged in
      if (user) {
        const schoolId = (user as any).schoolId ?? user.uid
        await recordGeneration({
          schoolId,
          userId: user.uid,
          subject: params.subject,
          grade: params.grade,
          indicatorCode: params.indicator.code,
          documentType: 'lesson_plan',
          filename,
        })
      }
    } catch (e: any) {
      setError(e.message)
    } finally {
      setGenerating(false)
    }
  }

  return { generate, generating, error }
}
```

**Definition of done:** a logged-in teacher can generate and download a
lesson plan. The download opens correctly in Word. A record appears in
Firestore under `generated_materials`.

---

## Phase 8 — Dashboard & History

**Goal:** schools can see their generation history and re-download or
regenerate from it.

### 8.1 — DashboardPage

Show:
- School name (from Firestore `schools/{schoolId}`)
- Count of documents generated this term
- Last 5 generated documents (links to HistoryPage)
- Quick-access "Generate" button

### 8.2 — HistoryPage

Pull `generated_materials` where `schoolId == currentSchool`, render
as a sortable table: date, subject, grade, indicator code, document type,
filename. Add a "Regenerate" button per row (re-runs generation from
stored params — no re-upload needed since generation is client-side).

**Definition of done:** history persists across browser sessions and is
school-scoped (two different school accounts see different histories).

---

## Phase 9 — Remaining 12 Subject Modules

**Goal:** all 13 subjects loaded and generating valid documents.

### 9.1 — Module template

Copy `app/src/modules/math/MathModule.ts` → `app/src/modules/<subject>/`.
Change `id`, `displayName`, `grades`. Update `loadIndicators` to point to
the right curriculum file. The `generateLessonPlan` structure is the same
— only the sections and block content differ per subject.

### 9.2 — Order to build

Build in this order (structurally simplest first, most complex last):

1. `english`       — B2–B9, same indicator structure as math
2. `science`       — B2–B9
3. `social-studies` — B7–B9 (JHS only)
4. `history`       — B2–B6
5. `rme`           — B2–B9
6. `ghanaian-language` — B2–B9, UTF-8 check required
7. `computing`     — B7–B9
8. `career-technology` — B7–B9
9. `french`        — B7–B9, UTF-8 / diacritics check
10. `creative-arts`    — B2–B6
11. `creative-arts-design` — B7–B9
12. `owop`         — B1 only

### 9.3 — Per-module checklist

For each subject:
- [ ] `app/src/modules/<subject>/<Subject>Module.ts` — implements `SubjectModule`
- [ ] `make build-curriculum` regenerated (or curriculum file already exists in `app/public/curriculum/<subject>/`)
- [ ] Registered in `app/src/modules/index.ts`
- [ ] `generateLessonPlan` returns a `MaterialDoc` that generates a
      readable `.docx` (open it in Word and eyeball it)
- [ ] `generateSchemeOfWork` returns a `MaterialDoc` with a table of all indicators

**Definition of done:** all 13 subjects appear in the Generate screen's
subject dropdown. Each produces a valid `.docx`.

---

## Phase 10 — Scheme of Work & Record of Work generation

**Goal:** teachers can generate all three document types, not just lesson
plans.

### 10.1 — Scheme of Work

The `generateSchemeOfWork` method already exists on every module. The
Generate screen needs a "Document type" selector:

```
○ Lesson Plan     (per indicator, per week)
○ Scheme of Work  (per subject, per grade, per term — all indicators)
○ Record of Work  (per subject, per grade, per term — full weekly schedule)
```

For Scheme of Work, `useGenerate` loads all indicators for the
grade/subject first, then calls `module.generateSchemeOfWork(grade, term)`
with the pre-loaded indicators injected via `options`.

### 10.2 — Record of Work

Record of Work is the weekly schedule — maps lessons from
`data/lessons/*_lessons_enriched.json` into a term-by-week grid. The
enriched lesson JSON is the same data `scripts/generate_records_of_work.py`
uses. Add a `generateRecordOfWork(grade, term)` method to each module that
reads from the static lesson bundle (`/curriculum/lessons/<subject>/<grade>.json`).

**Definition of done:** all three document types download correctly for
at least Mathematics B4.

---

## Phase 11 — Offline Pack (PWA)

**Goal:** the app works on Ghanaian mobile networks — teachers can browse
curriculum and generate documents with poor or no connectivity.

### 11.1 — Vite PWA plugin

```powershell
cd app
npm install -D vite-plugin-pwa
```

`vite.config.ts`:

```ts
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            // Cache all static curriculum JSON
            urlPattern: /\/curriculum\/.+\.json$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'curriculum-cache',
              expiration: { maxAgeSeconds: 60 * 60 * 24 * 30 }, // 30 days
            },
          },
        ],
      },
      manifest: {
        name: 'Beacon Consult — Beacon Teaching Materials',
        short_name: 'Beacon Consult',
        theme_color: '#1e40af',
        icons: [
          { src: '/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
})
```

### 11.2 — What works offline vs online

| Action | Offline | Online |
|--------|---------|--------|
| Browse curriculum | ✓ (cached JSON) | ✓ |
| Generate lesson plan | ✓ (client-side docx) | ✓ |
| Generate scheme/record | ✓ | ✓ |
| View history | ✗ (needs Firestore) | ✓ |
| Save history | ✗ (queued, syncs on reconnect) | ✓ |
| Auth sign-in | ✗ | ✓ |

**Definition of done:** throttle Chrome to "Offline" in DevTools. Load
`/curriculum`, pick a subject, generate a document — all work without
network.

---

## Phase 12 — Auth, Multi-tenancy & School Branding

**Goal:** schools and teachers are real entities. Documents are printed
under the correct school's name automatically.

### 12.1 — Firestore data model

```
schools/
  {schoolId}/
    name: string
    plan: 'free' | 'pro'
    createdAt: timestamp

users/
  {uid}/
    schoolId: string
    displayName: string
    role: 'teacher' | 'admin'
    createdAt: timestamp

generated_materials/
  {docId}/
    schoolId: string
    userId: string
    subject: string
    grade: string
    indicatorCode: string
    documentType: string
    filename: string
    generatedAt: timestamp
    storageUrl: string | null   // set if stored in Firebase Storage
```

### 12.2 — School context on generation

When a logged-in teacher generates a document, populate `schoolContext`
from Firestore before calling `module.generateLessonPlan()`:

```ts
const school = await getSchool(user.schoolId)
const doc = module.generateLessonPlan({
  indicator,
  grade,
  term,
  week,
  schoolContext: {
    schoolName: school.name,
    teacher: user.displayName,
  },
  options: {},
})
```

The `generateLessonPlan` methods use `request.schoolContext.schoolName`
on the document cover. A teacher cannot print a document under a
different school's name — the field is server-populated, not editable.

### 12.3 — Firestore security rules (`firestore.rules`)

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    match /schools/{schoolId} {
      allow read: if request.auth != null
                  && get(/databases/$(database)/documents/users/$(request.auth.uid)).data.schoolId == schoolId;
      allow write: if false; // admin SDK only
    }

    match /users/{uid} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }

    match /generated_materials/{docId} {
      allow read: if request.auth != null
                  && resource.data.schoolId ==
                     get(/databases/$(database)/documents/users/$(request.auth.uid)).data.schoolId;
      allow create: if request.auth != null
                    && request.auth.uid == request.resource.data.userId;
      allow update, delete: if false;
    }
  }
}
```

**Definition of done:** two different school accounts cannot see each
other's `generated_materials`. An unauthenticated request is rejected.

---

## Phase 13 — Firebase Storage (re-download)

**Goal:** teachers can re-download a previously generated document without
regenerating it.

### 13.1 — Upload on generate

After generating locally, upload the blob to Firebase Storage and save
the URL to Firestore:

```ts
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage'
import { storage } from './firebase'

export async function uploadDocument(
  blob: Blob,
  schoolId: string,
  filename: string
): Promise<string> {
  const storageRef = ref(storage, `schools/${schoolId}/documents/${filename}`)
  await uploadBytes(storageRef, blob)
  return getDownloadURL(storageRef)
}
```

### 13.2 — Storage rules (`storage.rules`)

```
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /schools/{schoolId}/documents/{filename} {
      allow read, write: if request.auth != null
                         && firestore.get(/databases/(default)/documents/users/$(request.auth.uid)).data.schoolId == schoolId;
    }
  }
}
```

**Definition of done:** clicking a history row downloads the file directly
from Storage (no regeneration). A teacher from School A cannot download
School B's files.

---

## Phase 14 — Question Bank

**Goal:** implement the `generateQuestions` capability the interface
already has a slot for.

Each subject module adds `'questions'` to its `capabilities` only when
it actually implements `generateQuestions`. The Generate screen gains a
"Generate questions" document type, gated by the capability check.

Data lives in `data/questions/<subject>/<grade>.json` — needs to be
authored first (see `docs/NACCA_QUESTION_BANK.yaml` for the planned
schema).

---

## Phase 15 — Vercel Deployment

**Goal:** the app is live at a public URL teachers can reach.

### 15.1 — Deploy

```powershell
cd app
npm run build    # tsc + vite build → dist/
```

Connect the repo to Vercel:
1. Vercel dashboard → "Add New Project" → import this repo
2. Set **Root Directory** to `app`
3. Set **Build Command** to `npm run build`
4. Set **Output Directory** to `dist`
5. Add all `VITE_FIREBASE_*` environment variables from `.env.local`

### 15.2 — Verify

- [ ] `/` loads on a real mobile device
- [ ] `/curriculum` loads with network throttled to "Slow 3G"
- [ ] Generate a lesson plan on a real device
- [ ] Auth sign-in works
- [ ] PWA install prompt appears

**Definition of done:** a teacher on a real Ghanaian mobile network can
load the portal and generate a document.

---

## Summary Table

| Phase | What you build | Unblocks |
|-------|---------------|---------|
| 1 | Kernel types + registry | Everything else |
| 2 | Math module (JS) | Phase 3 test |
| 3 | docx driver | Document download |
| 4 | Firebase setup | Auth + history |
| 5 | Routing + shell | All pages |
| 6 | Curriculum browser | Teacher exploration |
| 7 | Generate screen | Revenue — teachers can use this |
| 8 | Dashboard + history | School value, retention |
| 9 | 12 remaining modules | All subjects available |
| 10 | Scheme + record of work | Full document set |
| 11 | PWA / offline | Ghanaian connectivity |
| 12 | Auth + multi-tenancy | School isolation, branding |
| 13 | Firebase Storage | Re-download |
| 14 | Question bank | New content type |
| 15 | Vercel deployment | Live for real schools |

**Phases 1–7 are the revenue path.** Everything from Phase 8 onward
compounds what's already working.
