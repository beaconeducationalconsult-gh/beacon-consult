# 2. Data model

Two data sources:

1. **Firestore** — all user/member content (dynamic).
2. **Static JSON** in `public/` — the NaCCA curriculum and the quotes (read-only, shipped
   with the app, cached offline).

> Field lists below name the **important** fields. The authoritative shape for each
> collection is whatever its create/edit form writes — the "written by" file is the source
> of truth. Every document also carries `authorId`, `authorName`, and server timestamps
> unless noted.

## Firestore collections

| Collection | Purpose | Written by | Rule |
|---|---|---|---|
| `users/{uid}` | Member profile & status | `SignUp`, `Profile`, `Members` (admin) | ✅ |
| `posts/{id}` | Community feed posts | `Workspace` | ✅ |
| `articles/{id}` | Longform articles (WYSIWYG) | `ArticleForm` | ✅ |
| `notes/{id}` (+`comments`) | Study notes | `NoteForm`, `NoteView` | ✅ |
| `weekly_forecasts/{id}` | Schemes of learning | `ForecastForm` | ✅ |
| `lesson_plans/{id}` | Lesson plans | `LessonPlanForm` | ✅ |
| `questions/{id}` | Question bank | `QuestionForm` | ✅ |
| `lesson_slides/{id}` (+`comments`) | Slide lessons (exported from schedules) | `SlideLessons` | ✅ |
| `vacancies/{id}` | Teaching vacancies | `VacancyForm` | ✅ |
| `progress/{uid}` | Per-member teaching tracker | `Progress`, `Workspace` | ✅ |
| `quote_likes/{quoteId}` | Shared likes on quotes | `useWisdom` | ✅ |

> All collections are enforced by [`firestore.rules`](../firestore.rules) — read
> [security.md](security.md) alongside this.

### `users/{uid}`
Key fields: `name`, `status` (`'pending' | 'approved' | 'suspended'`),
`role` (`'member' | 'admin'`), plus profile bits (`school`, etc.).
- Created at sign-up (`SignUp.jsx`) as `pending`. An admin flips `status`/`role` in
  `Members.jsx`. The current user's profile is streamed live by `AuthContext`.

### `posts/{id}` — feed
`content`, `timestamp`, `likesCount`, `likedBy[]`. Any approved member may like/unlike
(rules restrict the diff to `likedBy` + `likesCount`); only the author can edit content.

### `articles/{id}` — articles
`title`, `content` (HTML from Tiptap), `excerpt` (first 200 chars, stripped),
`category`, `subjectId`, `visibility` (`'public' | 'members'`), `likesCount`, `likedBy[]`.
Public ones surface on `/articles` and `PublicArticleView`.

### `notes/{id}` (+ `comments/{id}`)
`visibility` (`'members' | 'public' | 'private'`), `status` (`'draft' | 'published'` — written
by the form, not read by the rules; older notes have neither), `likes`, `likesBy`, content.
`private` → author/admin only, enforced by the read rule; `members`/`public` → network-wide.
Has a `comments` subcollection. The like fields diff-limited to `likes` + `likesBy`; no
note-like UI exists yet.

### `weekly_forecasts/{id}` — schemes of learning
`kind: 'scheme'`, `subjectId`, `grade`, `term`, `rows[]` (per-week strand/sub-strand/
content-standards/indicators/resources/indicatorIds), `notes`,
`visibility` (`'members' | 'public' | 'private'`). Shared schemes are a library; a member can
clone one as a template (`?from=<id>` in `ForecastForm`). `private` is a draft only the author
(and admins) can read — the read rule says so and the list pages query accordingly.

### `lesson_plans/{id}`
`visibility` (`'members' | 'public' | 'private'`), `indicatorIds[]` (for curriculum-linked
lookups — indexed), plan phases/content. Indexed on `visibility+createdAt`,
`authorId+createdAt`, and `indicatorIds` (array-contains) combos.

### `questions/{id}` — question bank
`subjectId`, `grade`, `strandName`, `subStrandName`, `type` (`'mcq' | 'short' | 'essay'`),
question/options/answer/marks, and **`weekKey`** (ISO week — drives the weekly quota
reminder on the Workspace home page; indexed `authorId+weekKey`). Consumed by the generators
(`QuestionGenerator`, `QuizMaker`) and `Search`.

### `lesson_slides/{id}` (+ `comments`)
`status` (`'published'` gates public-ish reads within the network). The browse/export page
exists; there is no authoring form (see [gotchas.md](gotchas.md)).

### `vacancies/{id}`
`status` (`'published'` is readable **without auth** — powers the public `/vacancies`
page), `deadline`, school/role details.

### `progress/{uid}`
Owner-only (`read,write: request.auth.uid == uid`). Shape: `{ weeks: { '<subjectKey>_T<term>': [...] } }`.
The workspace summarises it into a "subject-weeks taught" card; `Progress.jsx` is the full
broader tracker.

### `quote_likes/{quoteId}`
`{ count, likedBy[] }`, created on first like. Members toggle only their own uid; the rule
enforces `count` moves ±1 in step. Read live across the collection by `useQuoteLikes()`
(feeds the Quotes page hearts + the workspace "most-loved" leaderboard). Quote ids come from the
static `quotes.json` — there is **no** `quotes` document collection.

## Static JSON (`public/`)

### Curriculum — `public/curriculum/`
Per grade **KG1, KG2, B1…B9** (`grades.json` lists them):
- `<grade>_subjects.json` — subjects for the grade (`id`, `name`, `hasSchedule`, …)
- `<grade>_indicators.json` — flat indicators (strand → sub-strand → content standard →
  indicator), grouped in memory by `buildTree()` in `useCurriculum.js`
- `schedules/<grade>-<subject>.json` — day-by-day scheduled lessons, one file per
  subject-grade (used to pre-fill schemes; the term calendar loads all of a grade's)

Loaded via `useCurriculum(grade)` / `useSchedules(grade, subjectId)` / `useGrades()` with
module-level caches. Also **precached by the service worker** for offline use.

### Quotes — `public/quotes/`
- `quotes.json` — famous education quotes + Ghanaian/Adinkra proverbs
  (`id`, `type`, `text`, `author`, `source?`, `meaning?`, `tags[]`)
- `theories.json` — teaching theories (`id`, `title`, `theorist`, `definition`,
  `classroom` [Ghana application], `category`, `tags[]`)

Loaded by `useWisdom.js`. The daily quote / weekly theory are chosen **deterministically
by local date** (see [pwa-offline.md](pwa-offline.md)).

## Composite indexes (`firestore.indexes.json`)

Defined for `posts` (2), `lesson_plans` (4), `weekly_forecasts` (2), `questions` (2),
`lesson_slides` (2), `vacancies` (2), `notes` (3), `articles` (1) — the last three for the
`authorId + createdAt`/`visibility + createdAt` shape the member lists and `Search.jsx` use.
`articles`' public page still needs no index: `where('visibility','==','public')` is covered by
the automatic single-field index. Every `where(...) + orderBy(...)` pair in `src/` has an index
here; a missing one shows up as `failed-precondition` in the page's error banner.
