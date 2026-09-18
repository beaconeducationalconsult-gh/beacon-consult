# 5. Shared code

Reusable building blocks. Prefer these over re-implementing.

## Contexts (`src/context/`)

### `AuthContext.jsx` → `useAuth()`
`{ user, profile, loading, logout }`. `user` is the Firebase auth user; `profile` is the
live `users/{uid}` doc (`undefined` = loading, `null` = none). This is the single source of
truth for "who am I / am I approved / am I admin".

### `ToastContext.jsx` → `useToast()`
`toast.success(msg)` / `toast.error(msg)` for transient notifications. Use it instead of
`alert()`.

## Hooks (`src/hooks/`)

### `useCurriculum.js`
- `useCurriculum(grade = 'B1')` → `{ loading, grade, subjects, indicators }`
- `useSchedules(grade)` → `{ loading, lessons }` (day-by-day scheduled lessons, if any)
- `useGrades()` → grades that have extracted data (`grades.json`)
- `isPlaceholder(text)` → true while an indicator is still an extraction placeholder
- `buildTree(indicators, subjectId)` → nests flat indicators into
  strand → sub-strand → content standard → indicators
- Fetches `/curriculum/*.json` with **module-level caches** (each file fetched at most once
  per session). Resolves instantly when cached.

### `useWisdom.js`
- `useQuotes()` / `useTheories()` → the static JSON arrays
- `quoteOfTheDay(quotes)` / `theoryOfTheWeek(theories)` — **deterministic by local date**
  (`dailyIndex`) so everyone sees the same pick, changing at local midnight; no server
- `useQuoteLikes()` → live `{ quoteId: { count, likedBy[] } }` map (one `onSnapshot` on the
  `quote_likes` collection; error-handled so it degrades when unauthenticated)
- `toggleQuoteLike(quoteId, uid, likes)` → create-on-first-like toggle
- `topLikedQuotes(quotes, likes, n)` → top-N by count, joined to quote objects (workspace
  leaderboard)

## Document exporters (`src/lib/`)

All run **client-side** (no server). Heavy ones are `import()`-ed lazily at click time.

| File | Produces | Used by |
|---|---|---|
| `schemePdf.js` / `schemeDocx.js` | Scheme of learning (PDF / Word) | Schemes |
| `lessonPlanPdf.js` / `lessonPlanDocx.js` | Lesson plan (PDF / Word) | Lesson plans |
| `questionPaper.js` | Exam paper (PDF) | Question generator |
| `quizPptx.js` | Quiz slideshow (PPTX) | Quiz maker |
| `docxShared.js` | Shared Word-generation helpers | the `*Docx` exporters |

Libraries: `jspdf` + `jspdf-autotable` (PDF), `docx` (Word), `pptxgenjs` (PowerPoint).

## Pure helpers (`src/lib/`)

- `week.js` — ISO week keys + the `WEEKLY_QUOTA` constant (question-bank target)
- `academicCalendar.js` — Ghana term calendar; `getAcademicStatus()`, `termProgress()`,
  `daysUntil()`, `fmtDate()` (drives the workspace widgets and `components/TermCalendar.jsx`)
- `grades.js` — grade id ↔ label helpers (`gradeLabel`)
- `subjectThemes.js` — per-subject colour theming

## Components (`src/components/`)

| Component | Purpose |
|---|---|
| `Sidebar.jsx` | Primary nav (fixed desktop / drawer mobile). Study notes, Quote of the day and Slide lessons are commented out of `LINKS` (pages still routed); header + user footer stay pinned. |
| `Navbar.jsx` | Public marketing nav (currently unused by pages) |
| `PendingApproval.jsx` | Shown to unapproved/suspended members by `ProtectedLayout` |
| `OfflineIndicator.jsx` | Bottom-center pill: offline / syncing / synced (see pwa-offline.md) |
| `RichEditor.jsx` | Tiptap WYSIWYG (bold/italic/headings/lists/links/align…); outputs **HTML**. Used by articles. |
| `Skeleton.jsx` | `Skeleton`, `SkeletonCard`, `SkeletonList`, `SkeletonGrid` loading placeholders |
| `EmptyState.jsx` | Standard empty-state block |
| `ConfirmModal.jsx` | Confirm dialog for destructive actions |
| `Stepper.jsx` | Multi-step form stepper |
| `NotesTabs.jsx` | Tab strip used in the notes area |
| `SubjectIcon.jsx` | Per-subject icon |
| `SubjectSelect.jsx` | Subject dropdown for a grade; reports load failures and "no subjects" distinctly instead of rendering an empty-looking select |
| `DataError.jsx` | "Could not load X" block naming the Firestore error (pending approval, undeployed rules, offline, missing index) — used by every data page |
| `TermCalendar.jsx` | One term's weeks + scheduled lessons (a section of the Workspace) |

> `RichEditor` and the article views render content with Tailwind `prose` classes, backed by
> the `@tailwindcss/typography` plugin (registered via `@plugin "@tailwindcss/typography";`
> in `src/index.css`).
