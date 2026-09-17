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
| `posts/{id}` | Community feed posts | `Feed` | ✅ |
| `articles/{id}` | Longform articles (WYSIWYG) | `ArticleForm` | ✅ |
| `notes/{id}` (+`comments`) | Study notes | `NoteForm`, `NoteView` | ✅ |
| `weekly_forecasts/{id}` | Schemes of learning | `ForecastForm` | ✅ |
| `lesson_plans/{id}` | Lesson plans | `LessonPlanForm` | ✅ |
| `questions/{id}` | Question bank | `QuestionForm` | ✅ |
| `lesson_slides/{id}` (+`comments`) | Slide lessons (exported from schedules) | `SlideLessons` | ✅ |
| `vacancies/{id}` | Teaching vacancies | `VacancyForm` | ✅ |
| `progress/{uid}` | Per-member teaching tracker | `Progress`, `Feed` | ✅ |
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
`status` (`'private' | 'pending' | 'published'`), `likes`, `dislikes`, content.
Private → visible to author/admin only; `published` → network-wide. Approved members may
like/dislike (rules restrict the diff to `likes` + `dislikes`). Has a `comments`
subcollection.

### `weekly_forecasts/{id}` — schemes of learning
`kind: 'scheme'`, `subjectId`, `grade`, `term`, `rows[]` (per-week strand/sub-strand/
content-standards/indicators/resources/indicatorIds), `notes`,
`visibility` (`'public' | 'private'`). Public schemes are a shared library; a member can
clone one as a template (`?from=<id>` in `ForecastForm`).

### `lesson_plans/{id}`
`visibility` (`'public' | 'private'`), `indicatorIds[]` (for curriculum-linked lookups —
indexed), plan phases/content. Indexed on `visibility+createdAt`, `authorId+createdAt`,
and `indicatorIds` (array-contains) combos.

### `questions/{id}` — question bank
`subjectId`, `grade`, `strandName`, `subStrandName`, `type` (`'mcq' | 'short' | 'essay'`),
question/options/answer/marks, and **`weekKey`** (ISO week — drives the weekly quota
reminder on the Feed; indexed `authorId+weekKey`). Consumed by the generators
(`QuestionGenerator`, `QuizMaker`) and `Search`.

### `lesson_slides/{id}` (+ `comments`)
`status` (`'published'` gates public-ish reads within the network). The browse/export page
exists; there is no authoring form (see [gotchas.md](gotchas.md)).

### `vacancies/{id}`
`status` (`'published'` is readable **without auth** — powers the public `/vacancies`
page), `deadline`, school/role details.

### `progress/{uid}`
Owner-only (`read,write: request.auth.uid == uid`). Shape: `{ weeks: { '<subjectKey>_T<term>': [...] } }`.
Feed summarises it into a "subject-weeks taught" banner; `Progress.jsx` is the full tracker.

### `quote_likes/{quoteId}`
`{ count, likedBy[] }`, created on first like. Members toggle only their own uid; the rule
enforces `count` moves ±1 in step. Read live across the collection by `useQuoteLikes()`
(feeds the Quotes page hearts + the Feed "most-loved" leaderboard). Quote ids come from the
static `quotes.json` — there is **no** `quotes` document collection.

## Static JSON (`public/`)

### Curriculum — `public/curriculum/`
Per grade **KG1, KG2, B1…B9** (`grades.json` lists them):
- `<grade>_subjects.json` — subjects for the grade (`id`, `name`, `hasSchedule`, …)
- `<grade>_indicators.json` — flat indicators (strand → sub-strand → content standard →
  indicator), grouped in memory by `buildTree()` in `useCurriculum.js`
- `<grade>_schedules.json` — optional day-by-day scheduled lessons (used to pre-fill
  schemes)

Loaded via `useCurriculum(grade)` / `useSchedules(grade)` / `useGrades()` with
module-level caches. Also **precached by the service worker** for offline use.

### Quotes — `public/quotes/`
- `quotes.json` — famous education quotes + Ghanaian/Adinkra proverbs
  (`id`, `type`, `text`, `author`, `source?`, `meaning?`, `tags[]`)
- `theories.json` — teaching theories (`id`, `title`, `theorist`, `definition`,
  `classroom` [Ghana application], `category`, `tags[]`)

Loaded by `useWisdom.js`. The daily quote / weekly theory are chosen **deterministically
by local date** (see [pwa-offline.md](pwa-offline.md)).

## Composite indexes (`firestore.indexes.json`)

Defined for `posts`, `lesson_plans` (4), `weekly_forecasts` (2), `questions`,
`lesson_slides` (2), `vacancies` (2), `notes` (2). `articles` needs **no composite index**:
its queries are single-field equality (`where('visibility'/'authorId','==',…)`) with
client-side sorting, which Firestore's automatic single-field indexes already cover.
