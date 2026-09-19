# 4. Features (module reference)

One row per feature area: its routes, what it does, the Firestore collection(s) it touches,
and notable helpers. Page files live in `src/pages/`.

## Community & content

### Workspace — `/portal`
`Workspace.jsx`. The portal home, and the merge of three former pages (the feed, `My wall`
and `Calendar`):

- **Feed** — real-time community `posts` (compose + like) in the main column.
- **Rail** — **Quote of the Day**, term-progress card (from `progress`), a weekly question-bank
  quota reminder (counts `questions` where `weekKey == thisWeek`), and the **most-loved quotes**
  leaderboard.
- **Your contributions** — the member's own `lesson_plans`, `weekly_forecasts`, `notes`,
  `questions` and `articles`, a card each (was `MyWall.jsx`).
- **Term calendar** — `components/TermCalendar.jsx`: one term's weeks and what is scheduled in
  them, per grade (was `Calendar.jsx`).

Collections: `posts`, `progress`, `questions`, `articles`, `lesson_plans`, `weekly_forecasts`,
`notes`. `/portal/wall` and `/portal/calendar` redirect here.

### Articles — `/portal/articles` (+ `/new`, `/:id`, `/:id/edit`); public `/articles`
`Articles.jsx` (list), `ArticleForm.jsx` (WYSIWYG create/edit via `RichEditor`),
`ArticleView.jsx`, `PublicArticles.jsx`, `PublicArticleView.jsx`. Longform posts with
`category`, optional `subjectId`, `visibility` (`public`/`members`), likes.
Content is **HTML** produced by Tiptap. Collection: `articles` — `public` reads are open,
`members` reads need approval; writes are owner/admin, likes use the narrow `likedBy`/
`likesCount` diff (see [security.md](security.md)).

### Notes — `/portal/notes` (+ `/new`, `/:id`, `/:id/edit`)
`Notes.jsx`, `NoteForm.jsx`, `NoteView.jsx`. Study notes with a `comments` subcollection.
Collection: `notes`.

The list has two tabs, and each one is a *scoped* Firestore query rather than a client-side
filter of one big read: **Mine** (`where('authorId','==',uid)`) and **Shared**
(`where('visibility','in',['members','public'])`). That shape is what lets the read rule gate on
the document: `visibility: 'private'` ("Only me (draft)") is readable only by its author and
admins, and the form also records `status: 'draft' | 'published'` for the same choice — which
cannot gate reads, because notes written before 2026-09-19 have no `status` field. The lists
paginate (`usePagedCollection`, 24 per page) so the cap never silently hides old notes. The
"like" fields are `likes`/`likesBy` but no note-like UI exists yet (P2-7 in
[TODO.md](TODO.md)).

*Exports (2026-09-19):* **Word** and **PDF**, from the buttons on the note page — the note's
rich text goes through `src/lib/htmlBlocks.js` into `noteDocx.js` / `notePdf.js`. Inline
formatting is flattened and inline images are omitted (see [gotchas.md](gotchas.md)).

### Slide lessons — `/portal/slides`, `/:deckId`, `/:deckId/edit`
`SlideLessons.jsx` builds a deck from a week's scheduled lessons and exports PPTX;
`SlideLessonView.jsx` shows a saved deck slide by slide with its comment thread and export;
`SlideLessonForm.jsx` edits the slides (add/remove/reorder). Hidden from the side panel, still
routed. Collection: `lesson_slides` (+ `comments`).

### Author page — `/portal/authors/:authorId`
`AuthorPage.jsx`. A member's public profile + their published notes/slides.
Collections: `users`, `notes`, `lesson_slides`.

## Curriculum & planning

### Curriculum browser — `/portal/curriculum` (+ `/:gradeId`, `/:gradeId/:subjectId`)
`Curriculum.jsx` (grade grid), `GradeSubjects.jsx` (one grade's subjects),
`SubjectBrowser.jsx` (strand → sub-strand → content standard → indicators tree). The grade id
is in the URL — both ids are, so a subject link is unambiguous. Pure reads of static curriculum
JSON via `useCurriculum` — no Firestore. Offline-capable.

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
`SlideLessons.jsx` — pick a grade/subject/term/week and the page builds a deck from that
week's scheduled lessons (`useSchedules`) and exports it as PPTX via
`lib/lessonSlidesPptx.js`; it can also save the deck to `lesson_slides`. There is **no
authoring form or deck-view page** — `SlideLessonForm`/`SlideLessonView` do not exist in the
portal. Collection: `lesson_slides`.

## Utility & admin

- **Search** `/portal/search` (`Search.jsx`) — searches the `questions` bank.
- **Progress** `/portal/progress` (`Progress.jsx`) — personal teaching tracker (`progress`).
- **Calendar** — the portal term calendar is a section of the Workspace
  (`components/TermCalendar.jsx`); public `/calendar` (`PublicCalendar.jsx`) is the Ghana
  academic calendar (`lib/academicCalendar.js`, pure/static).
- **Profile** `/portal/profile` (`Profile.jsx`) — edit own `users` doc.
- **Members** `/portal/members` (`Members.jsx`, **admin**) — approve/suspend members, set
  roles. Reads/writes `users`.

## Public pages (no login)

`/` Landing, `/vacancies`, `/quotes`, `/calendar`, `/articles` + `/articles/:id`,
`/login`, `/signup`. These read only public/published data (or static JSON), consistent
with `firestore.rules`.
