# 4. Features (module reference)

One row per feature area: its routes, what it does, the Firestore collection(s) it touches,
and notable helpers. Page files live in `src/pages/`.

## Community & content

### Feed — `/portal`
`Feed.jsx`. The portal home. Real-time community `posts` (compose + like), plus header
widgets: academic-calendar status, **Quote of the Day**, **most-loved quotes** leaderboard,
a term-progress banner (from `progress`), and a weekly question-bank quota reminder (counts
`questions` where `weekKey == thisWeek`). Also surfaces recent `articles`.
Collections: `posts`, `progress`, `questions`, `articles`.

### Articles — `/portal/articles` (+ `/new`, `/:id`, `/:id/edit`); public `/articles`
`Articles.jsx` (list), `ArticleForm.jsx` (WYSIWYG create/edit via `RichEditor`),
`ArticleView.jsx`, `PublicArticles.jsx`, `PublicArticleView.jsx`. Longform posts with
`category`, optional `subjectId`, `visibility` (`public`/`members`), likes.
Content is **HTML** produced by Tiptap. Collection: `articles` (⚠️ no rule — [gotchas](gotchas.md)).

### Notes — `/portal/notes` (+ `/new`, `/:id`, `/:id/edit`)
`Notes.jsx`, `NoteForm.jsx`, `NoteView.jsx`. Study notes with a lifecycle
(`private`→`pending`→`published`), likes/dislikes, and a `comments` subcollection.
Collection: `notes`.

### My Wall — `/portal/wall`
`MyWall.jsx`. Aggregates the current member's own content (notes, etc.) for quick access.

### Author page — `/portal/authors/:authorId`
`AuthorPage.jsx`. A member's public profile + their published notes/slides.
Collections: `users`, `notes`, `lesson_slides`.

## Curriculum & planning

### Curriculum browser — `/portal/curriculum` (+ `/:subjectId`)
`Curriculum.jsx` (grade → subject grid), `SubjectBrowser.jsx` (strand → sub-strand →
content standard → indicators tree). Pure reads of static curriculum JSON via
`useCurriculum` — no Firestore. Offline-capable.

### Schemes of learning — `/portal/forecasts` (+ `/new`, `/:id`, `/:id/edit`)
`Forecasts.jsx`, `ForecastForm.jsx`, `ForecastView.jsx`. Per-term, per-week scheme rows
that can be **pre-filled from the curriculum schedule** or built with an indicator picker.
Clone another member's public scheme via `?from=<id>`. Export to PDF/DOCX.
Collection: `weekly_forecasts`. Exporters: `lib/schemePdf.js`, `lib/schemeDocx.js`.

### Lesson plans — `/portal/plans` (+ `/new`, `/:id`, `/:id/edit`)
`LessonPlans.jsx`, `LessonPlanForm.jsx`, `LessonPlanView.jsx`. Indicator-linked
(`indicatorIds[]`) plans; public/private. Export to PDF/DOCX.
Collection: `lesson_plans`. Exporters: `lib/lessonPlanPdf.js`, `lib/lessonPlanDocx.js`.

## Questions

### Question bank — `/portal/questions` (+ `/new`, `/:id/edit`)
`QuestionBank.jsx`, `QuestionForm.jsx`. Author MCQ/short/essay questions tagged by
subject/strand/sub-strand; carries `weekKey` for the weekly quota.
Collection: `questions`.

### Generators — `/portal/questions/generate` and `/quiz`
`QuestionGenerator.jsx` (builds a printable exam paper — PDF), `QuizMaker.jsx` (builds a
classroom quiz slideshow — PPTX). Both read the shared `questions` bank.
Exporters: `lib/questionPaper.js`, `lib/quizPptx.js`.

## Wisdom (Quote of the Day) — `/portal/wisdom`; public `/quotes`
`Wisdom.jsx`, `PublicQuotes.jsx`. Daily quote hero + browsable quotes/proverbs and teaching
theories, colour-coded cards, batched/infinite-scroll loading, search, and **shared likes**
(`quote_likes`). Data is static JSON via `useWisdom`. See [shared-code.md](shared-code.md).

## Vacancies — `/portal/vacancies` (+ `/new`, `/:id/edit`); public `/vacancies`
`Vacancies.jsx`, `VacancyForm.jsx`, `PublicVacancies.jsx`. Members post teaching vacancies;
`published` ones are readable publicly (no login). Collection: `vacancies`.

## Slides — `/portal/slides`
`SlideLessons.jsx` (browse). `SlideLessonForm/View` exist but their routes are **commented
out** in `App.jsx` — the authoring flow is not wired up. Collection: `lesson_slides`.

## Utility & admin

- **Search** `/portal/search` (`Search.jsx`) — searches the `questions` bank.
- **Progress** `/portal/progress` (`Progress.jsx`) — personal teaching tracker (`progress`).
- **Calendar** `/portal/calendar` (`Calendar.jsx`); public `/calendar` (`PublicCalendar.jsx`)
  — the Ghana academic calendar (`lib/academicCalendar.js`, pure/static).
- **Profile** `/portal/profile` (`Profile.jsx`) — edit own `users` doc.
- **Members** `/portal/members` (`Members.jsx`, **admin**) — approve/suspend members, set
  roles. Reads/writes `users`.

## Public pages (no login)

`/` Landing, `/vacancies`, `/quotes`, `/calendar`, `/articles` + `/articles/:id`,
`/login`, `/signup`. These read only public/published data (or static JSON), consistent
with `firestore.rules`.
