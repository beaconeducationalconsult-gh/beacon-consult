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

### Exam paper builder — `/portal/questions/exam`
`ExamBuilder.jsx`. The bank's *Export exam paper* button prints whatever is ticked; this page
decides **what to tick**. It draws on two pools at once — the member's own `questions` and the
served starter bank for the chosen subject-grade (`loadStarterPack`, so the B7–B9 questions are
usable in a paper without importing anything) — and assembles a paper of a requested size
through `src/lib/examPaper.js`, whose two rules are the page's whole behaviour:

- **a section draws only on its own types** (objectives in A, short answers in B, essays in C);
- **coverage before depth** — while filling, every indicator's first question goes in before any
  indicator's second, so a class paper does not test one sub-strand six times.

**It is scoped to a term.** *Which work does it cover?* restricts the pool to the indicators the
chosen term actually schedules — read from `public/curriculum/schedules/<grade>-<subject>.json`,
because that is the only thing in the repo that knows what term 2 teaches (a term-2 paper built
from the whole grade tests the third term in the second). Under the picker it prints the honest
half: *"Term 2 schedules 56 indicators — the pool asks about 41 (73%). 15 indicators have no
question in the pool: 5 in Patterns and Relations, 4 in Data and Probability …"*, so a teacher can
see which work their paper will not test before they print it. A subject-grade with no schedule
(KG, or an unscheduled subject) says so and covers the whole year.

The composition is pure, which is what makes the preview honest. `targetMarks` is a promise to
the extent the pool can keep it: each section takes its share first, and **the marks a section
cannot spend go to the sections that can still print** — so a B2 paper, whose pool held no
long-answer items at all, no longer came out 12 marks shorter than it said; it reaches the marks
asked for from Sections A and B, and the page **names the section that could not appear** and
says which of the two reasons it was ("its shortest question is worth 8 marks, and a 20-mark
paper has no room for it after the other sections" / "the pool for this scope holds no questions
of the type it prints"). The section shares add up to the target exactly — rounding them one by
one is how a 50-mark paper used to come out at 51. The paper never prints more than the marks
asked for, and only when the pool itself runs out is the shortfall printed. A teacher can drop any
question and see the paper recompose. Two exports: the student copy (PDF) and the teacher copy
with the marking scheme, with the teacher copy offered to **My library**
(`<SaveToLibrary kind="question_paper">`). Nothing is written to Firestore — the paper is the
PDF, not a document. Every section now has something to print in every year: the bank carries
`essay` items for the lessons no rule can answer (construct an angle and bisect it, draw a locus,
construct an inscribed circle at JHS; describe a pattern, design a questionnaire, compare two
graphs of the same data at primary), with the steps or the expected reasoning in the marking
scheme — and the scope line reads **100%** for every term of every year, so a paper tests the
whole of the term it was set for, at its full length (a 50-mark B5 paper composes 50, five of
them essays in Section C).

### BECE mock — `/portal/questions/bece`
`BeceMockPage.jsx`. Where the exam builder composes *a* paper from whatever a teacher has,
this page composes **the** paper: WAEC's BECE mathematics format — **Paper 1**, 40 compulsory
objectives (1 hour, 40 marks), **Paper 2**, six structured questions of 15 marks, answer four
(1 hour, 60 marks) — drawn from the whole served JHS bank at once (B7–B9, the years the exam
examines), so a B9 teacher prints a full 100-mark mock without selecting anything.
`src/lib/becePaper.js` composes; nothing is selected and nothing is written to Firestore.

- **Paper 1** reads the three years round-robin, each year's MCQs ordered one-per-indicator
  first, so the paper is balanced across B7/B8/B9 and no indicator is asked twice before any is
  asked once (the real bank composes 40 with a 14/13/13 spread and 40 distinct indicators).
- **Paper 2's questions are composed the way the real ones are printed** — the bank's items are
  1–5 marks, so a 15-mark question is a small set of parts, (a), (b), (c)…, whose marks add to
  exactly 15, taken from one strand of one grade (spilling into a neighbouring sub-strand before
  anything else), chosen round-robin across the grades, easiest part first, no item used twice
  anywhere in the mock. What the sitting **counts** is kept apart from what the sheet prints:
  six × 15 = 90 printed, 4 × 15 = 60 counted — the difference between a paper and a total.
- **Honesty is the same shape as the exam builder's**: when the pool runs short, the page names
  it ("the JHS bank holds N objective questions — 30 short…", "composes 4 of the 6 structured
  questions…") rather than padding with the wrong type or printing a 13-mark question as if it
  were 15.
- `src/lib/becePdf.js` prints the sitting in the house style: rubrics, Paper 1's option tables,
  Paper 2's lettered parts with marks in the margin, and the teacher copy's marking scheme for
  both papers — student copy, teacher copy, and the teacher copy offered to My library
  (`<SaveToLibrary>`), like every other page that downloads a document.

**Starter bank (P1-5).** The bundle ships **1,081 practice questions for mathematics B2–B9 —
a question for every indicator the syllabus schedules, in every year, and 100% of every term's
scope** — see *The question bank* in
[curriculum-data.md](curriculum-data.md). The bank page has
a **Starter bank** panel: choose a subject-grade, see the count and the indicator coverage, then
import. Imported questions become ordinary `questions` documents (batched writes, `status:
published`, `source` kept, `starterBankId` for provenance) and are editable, printable and
deletable like any other. Nothing is fetched or imported until the panel is opened.

#**Templated sections are labelled (P1-4).** Filling a plan from the curriculum inherits the
subject's printed routine — RPK, plenary, assessment, competencies, resources and keywords are one
value across a subject-grade's whole year (see `scripts/audit/audit_d_l2_template.py`). The form
says so after a fill, and both exports mark those headings `(teaching template)` with a line
explaining the marker, so a printed plan never passes the syllabus' routine off as the teacher's
own writing. See `src/lib/lessonTemplate.js`.

## Teaching models — `/portal/models`
`Models.jsx` + `src/components/models/*`. **The pilot, not a library**: five interactive models
for mathematics B4, each named after the served indicators it teaches
(`src/lib/teachingModels.js`), so a teacher can see what the screen is for. Everything is local
state and inline SVG/CSS — no external service, no API key, and it works offline like the rest of
the portal.

| Model | Teaches |
|---|---|
| Place value frame | B4.1.1.1.1, B4.1.1.1.2 — digit columns, expanded form, number in words |
| Compare, order and round | B4.1.1.1.4, B4.1.1.1.5 — two markers, comparison sentence, roundings |
| Fraction strips | B4.1.3.1.2, B4.1.3.2.1 — equivalent fractions you can line up |
| Factor arrays | B4.1.1.3.1, B4.1.1.3.6 — factor pairs as rectangles, primes, squares |
| Perimeter and area | B4.3.3.1.3, B4.3.3.1.4, B4.3.3.2.1 — count, then the formula; every shape with the same fence |

The catalogue is data and the components are code, held together by
`src/teachingModels.test.js`: every model must name indicators that are really served for its own
subject and grade, every component it points at must exist, and the pilot must stay between three
and five models. A model for an indicator that is not served would be a demo, not teaching
material. More subject-grades get models once these have been used in a classroom.

## My library — `/portal/library`
`DocumentLibrary.jsx`. Every document the portal generates — lesson plans, schemes, exam papers,
quiz decks, study notes — can be kept instead of existing only as whatever landed in the
downloads folder: the file goes to Cloud Storage under `generated/{uid}/…` and a record goes to
`generated_documents`. **Open** re-downloads it, **Delete** removes both halves. The folder is
private to its owner (see `storage.rules` in [security.md](security.md)).

Pages offer it through `<SaveToLibrary>` (`src/components/SaveToLibrary.jsx`), which builds the
document lazily — a teacher who never presses the button never pays for the build.
`src/lib/generatedDocs.test.js` scans the pages and fails if one downloads a document without
offering to keep it.

## Generators — `/portal/questions/generate` and `/quiz`
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
