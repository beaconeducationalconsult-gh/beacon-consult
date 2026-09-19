# 10. Gotchas & known gaps

Things that will bite you. Verified against the code in this repository — each entry below
is an **open** issue; when one is fixed, delete it.

## 🔴 A read rule that inspects document fields breaks list queries

Firestore is not a filter. For a `list`, the rules must be provable for **every** document the
query could return, so a read rule that depends on document data denies the *whole query* — not
just the documents that fail it. The client then sees `permission-denied` on a page that should
simply show fewer rows.

This bit us in production. `isApprovedOrAdmin() && (status == 'published' || isOwner(...))` on
`notes`, `lesson_plans`, `weekly_forecasts` and `lesson_slides` broke every un-filtered list in
`src/pages/` — **for ordinary members only**. Admins pass every branch, so an admin testing the
portal sees it working.

A read rule needs one disjunct that holds regardless of the document, and is true for a member:
`isApprovedOrAdmin()`, `isApproved()` or `isSignedIn()`. `isAdmin()` is document-independent but
false for a member, so it does not rescue the query. Where a rule genuinely must gate on a field
(like `articles.visibility == 'public'` for the anonymous public page), the *query* has to carry
a matching `where(...)` — see `PublicArticles.jsx`.

**`notes`, `lesson_plans` and `weekly_forecasts` gate reads this way again (P2-7, 2026-09-19).**
Their rule is `isApprovedOrAdmin() && (isAdmin() || isOwner(resource.data.authorId) ||
resource.data.visibility in ['members', 'public'])`, so `visibility: 'private'` is a real draft.
That is only safe because every screen lists them through one of two provable queries —
`where('authorId','==',uid)` (the Mine tab) or `where('visibility','in',['members','public'])`
(Shared) — including the two queries `Search.jsx` runs per gated collection. Listing any of the
three un-filtered is denied for every ordinary member.

**Deploy order matters for this pair.** Publish the new rules only after the new build is live:
an old client whose list page still queries un-filtered will go from "shows everything" to
`permission-denied`. The composite indexes (`visibility + createdAt`, and the `authorId +
createdAt` ones the paged lists use) must be deployed too — `firebase deploy --only
firestore:indexes`, or the console's index page.

`src/firestoreRules.test.js` fails if a collection the client lists un-filtered loses its
document-independent branch, and if a gated collection stops being scoped — it scans for both
`useCollection` and `usePagedCollection`.

## 🟠 A Word style Word cannot resolve renders as body text, silently

`docx` never validates what you hand it. Give a paragraph a `pStyle` naming a style the document
does not define and Word drops the reference and falls back to Normal — no error, no warning, no
difference you can see in the `.docx` itself. That is how every section heading in the lesson-plan
export disappeared: `docxShared.js` exported `H2` as a paragraph *factory*, and callers passed it as
`heading: H2`, so the style name written into the XML was the source text
`(text) => new Paragraph({ text, heading: HeadingLevel.HEADING_2 })`.

Two rules, both now enforced by `src/lib/docxExport.test.js` (which unzips the generated file and
reads its parts):

- **A heading level is a constant, not a function.** `H1`/`H2`/`H3` in `docxShared.js` are
  `HeadingLevel` values; the section styling lives in `documentStyles()`.
- **Declare the document's own font and size.** Without `docDefaults` the body font is whatever
  the *reader's* Word Normal template happens to be, so the same export looks different on two
  machines.

While you are in there: a footer built as a paragraph at the end of the body prints once, at the
end — real page furniture belongs in `sections[].footers`. Cell widths need `tblLayout: fixed` or
Word re-fits the columns to their content and ignores the percentages.

## 🟠 An audit that silently checks nothing

`scripts/audit/*.py` were all written before the data restructure, and each one resolved its
inputs with `os.path.join(ROOT, name)`. That is an absolute path, so `_compat`'s redirect never
sees it — `open_compat()` only rewrites **bare** filenames through `find_data()`. The PDFs moved
to `data/sources/`, the databases to `data/curriculum/` and `data/reference/`, and the scripts
kept looking in the repository root. Audit B reported `SKIP` for all 76 rows and called it a day;
Audit A reported 8 "file not found" failures that look exactly like data corruption.

So: **an audit that finds nothing looks the same as an audit that is satisfied.** When a check
reports all-skip, all-missing or zero rows, suspect the path wiring before the data. All three
audits resolve through `find_data()` now, and they write into `data/audit/` rather than dropping
result files in the repository root.

## 🟠 A "content standard" is not always a sentence

P1-1 asked for the empty `cs_desc` fields to be filled *from the PDF*, which assumes the print
carries a standard to copy. For French B4–B6 it does not: the CONTENT STANDARDS column holds one
of four skill areas (Compréhension Orale, Production Orale, Compréhension Écrite, Production
Écrite), and those four are the standard — the SCOPE AND SEQUENCE table lists exactly them, in
that order, for every sub-strand. French B7–B9 and computing do print a sentence.

So before "filling a missing field from the source", read what the source actually puts in that
column. The French B4–B6 answer is derivable without touching the PDF geometry: the fourth
component of the indicator code is the content-standard number, so the number names the skill
(1→CO, 2→PO, 3→CE, 4→PE). Two traps sit in that document — its body's CS cells are vertically
aligned to nothing in particular, so geometry-based matching disagrees with the scope table about
a quarter of the time; and one sub-strand is numbered as if it had a fifth standard
(`B6.1.2.5.3`), which no rule can name, so the field stays empty rather than guessed.

## 🟠 The same database can exist in two copies, and they drift

`find_data()` searches `data/curriculum/` before `data/reference/`, so for the six subjects that
exist in both, the *curriculum* copy is what the portal serves and the *reference* copy is inert.
The copies are not kept in step by anything: the French B7–B9 reference copies carried the
CORE COMPETENCIES column in `cs_desc` and a fabricated `B7.4.2.3.1` stub record (the four the front
matter fabricated were deleted from these copies on 2026-09-19 — see the notation-example gotcha
above), while the served
copies were clean — so a fix written against the wrong copy changes nothing a teacher sees, and a
fix against the right one leaves a defect behind in the file someone may later promote.

Check which copy `find_data` resolves (and whether the subject is served from it) before editing,
then rebuild: `make build-curriculum` writes `public/curriculum/`, which is what the app reads.
The nine subject-grades that were served from the fallback were promoted into `data/curriculum/`
on 2026-09-18 (see *Two copies of the same database* below) — so what remains in
`data/reference/` is inert today, and the fixer scripts resolve their files through `find_data`
rather than assuming the directory.

## 🟠 A page read top to bottom glues the neighbouring columns onto the row

The eight reference-only subject-grades were extracted by reading each page in order, which is why
397 indicator descriptions carried the page footer, the competence list of the column beside the
row, and the table's headings. The tempting fix — a list of phrases to delete — is not a fix: the
same words appear legitimately inside indicator text (`… discuss and point to things that are safe
and unsafe to play with.` sits beside a `References / WP / Communication and collaboration`
panel), and a phrase list cannot tell the two apart.

What works is to read the *print's row* first: the x band of the indicator column comes from the
page's own vertical rules (`re` operators with `w < 2.5`), then a row runs from its indicator code
to the next code or the next table heading. A phrase is furniture only when the print sets it
**outside that row**, and the survivor is read back against the row before anything is written.
Four traps sit in that geometry, all of them found the hard way:

* **A heading can sit inside the indicator column's band.** `STRAND 4: Les activités` and
  `INDICATOR AND EXEMPLARS` are centred over the table between two of its rules, so a row-band
  check that stops only at the next indicator code swallows them — `B5.3.1.4.1` ended
  `… l'on n'aime pas. STRAND 4: Les activités INDICATOR AND EXEMPLARS`.
* **A label copied halfway is not a label.** Where the print's line ran out, the extractor left a
  stub the vocabulary cannot match: `- Creativity and innov`, `… Cultural ide`,
  `… - Critical thinking -`. Cut a stub only when the print never sets it as a word of its own
  *and* a label word starts with it — otherwise the rule eats the record's own truncations
  (`… according to a given att`, where `attribute` is the print's word).
* **Never delete the extraction's truncations.** The database's clean spelling is usually the
  better reading (`R ead , use and copy` against `Read, use and copy`), so de-kern the row before
  comparing and treat a word the extraction cut short as part of the record: report it, never
  write it away.
* **De-kerning must not invent words.** Rejoining `R` + `ead` is safe only when the page prints
  `read` somewhere and does *not* print `R` on its own; without that second half `a` + `long`
  becomes `along`, and the row stops being a yardstick — which fails silently, because the
  comparison is on folded text.

The rule, the ladder of reading strengths (`row`/`page` verbatim → `row-order`/`page-order`/
`document-order` word-by-word → report only) and the residual scan live in
`scripts/fix_reference_text.py`; the trail is `data/audit/reference_text_fixes.json`.

## 🟠 The print's exemplar rides inside the indicator cell

These prints set a row as `<indicator>` and then, in the same cell, an exemplar
column — a numbered list of teaching steps behind `1.`, or `Learners are to:`, or
history's `Enquiry route:`. An extractor that reads to the end of the cell returns
indicator *plus* exemplar, which is how the databases came to hold
`… used for Graphic Communication 1. Identify drawing materials, instruments and
equipment` and `… in Africa Learners are to`. Nothing fails: `ind_desc` is only ever
rendered, so the artefact reaches every scheme, lesson plan and book.

Two things follow. **`ind_desc` should end where the print's exemplar begins** —
`scripts/fix_ind_desc_exemplars.py` cuts at the marker, and only when the print's
own row carries the indicator that would be left behind. And **the lesson files are
copies, four times over**: `data/lessons/*_lessons_enriched.json` embeds the
indicator in `ind_desc`, in the `perf_indicator` built from it, and inside the
`starter` and `main` activity steps the template writes around it — and the
generated books read the lesson file, not the database. Fix only the database and
the artefact survives in the documents teachers actually print; the fixer therefore
carries the same substitution into all four fields (and matches slots by
`ind_code`, so one indicator's text is never read into another's).

The band is read off the page's own rules, and the rules' own guards can quietly
throw the right ones away: the career-technology print draws its content-standard
column edge at x≈59 and its indicator column at 215–577, but the reader's `60 <= x`
floor dropped that first edge, found only two rules, and fell back to a fixed window
wide enough to swallow the **core-competencies column** (x 582+) into the indicator
text. That is why some career-technology `ind_desc` values read
`… unsafe practices in school Communication and Collaboration (CC) 1. Discuss …`: not
a bad extraction of the right column, but a bad *band* that included the wrong one.
Check a band against the page's own text before blaming the extraction, and remember
that the same band bug can look like a dozen different data defects.

The trap in the other direction: a tail that *mentions* the indicator is not a
repeat. History's rows carry the whole cell — enquiry route, then a dozen steps that
naturally name the topic — and cutting at the first marker deletes the only copy of
that text. The script cuts a tail only when it is short and says the indicator back
(≥4-word run covering half the indicator); everything else is reported.

## 🟠 A print's heading is a block property, and the print breaks its own words

`scripts/fix_sub_strand_names.py` (P1-12) reads the name a curriculum print sets once per block,
above its table, and writes it where the record still said `Sub-strand B4.1.1`. Three traps, each
one measured on the prints:

* **A name is not a row's property.** The heading sits above the whole block, so a record is
  anchored on its own row when the print carries it, then on its content standard, then on the
  same block in its grade, and — one step weaker, reported as such — on the same block in another
  grade of the same print. The CCP prints repeat a block across B7–B9, which is where 14 of the
  3,642 readings come from.
* **The same code can be reprinted under a different heading pages later** (english
  `B6.2.3.1.1` is read under `Word Families` on p192 and `Diphthongs` on p193, five blocks on).
  A reading whose heading number agrees with the row's own components settles it; a print that
  numbers by another scheme has no agreeing readings and the whole set speaks. Conflicts that
  remain are refusals — never merge two names because they are *nearly* the same.
* **The print kerns words apart.** Headings arrive as `GENE RATION`, `Appreciati n g`,
  `Organi s ation` and `samaison`, and the page gate must compare *folded* text (`F.blob_in`) or
  the whole pass refuses itself (that mistake cost 1,353 refusals before the gate was folded).
  Repairing the words is a **curated table**, each pair applied only after that print's own
  vocabulary spells the joined word — a general "join the pieces when the print spells the joined
  word" rule is not safe: the prints also join words of their own (`PhonicsLetter`, `StoryTelling`),
  and a rule wide enough to fix `Appreciati n g` also invents `RolePlay` and `ceque`. What the
  print itself sets (`TECHNOLOGY INTHE COMMUNITY` in the computing CCP's own table of contents)
  stays verbatim.

## 🟠 A print's notation example parses as a record

Every CCP front matter explains the code with a worked example — `Example: B7/JHS1 .4.2.3.1
ANNOTATION` — and an extractor that walks the whole document turns it into a record whose only
text is the code restated (`"French Learning Indicator B7.4.2.3.1"`). Four such records were built
(this session: french B7, ghanaian-language B7, rme B7, science B4 — all inert `data/reference/`
copies, none served). Two things make them hard to see:

* **the year annotation hides the code.** The english print writes `B7/JHS1 .4.2.3.1`, so a plain
  code search finds nothing anywhere — and that absence of a body row *is* the evidence. A finder
  has to tolerate `/\s*JHS\s*\d` and blank space between the parts.
* **label form proves nothing by itself.** 302 other records are label-form too, and the prints
  *do* carry their text (the owop B4–B6 print at pp. 18/40/61) — those are a filling job, not a
  deletion. Dropping on the shape alone would delete real curriculum.

`scripts/drop_front_matter_records.py` (report by default, `--apply` deletes) therefore requires
all three: label form, **exactly one** occurrence of the code in the print, and that occurrence on
a page whose line says `Example:`/`ANNOTATION` — plus no body row. Everything else is recorded as a
placeholder with its reason, and the deleted records are kept verbatim in
`data/audit/front_matter_records.json`, so a deletion can be undone from the artifact alone.

## 🟠 A pypdf page has an empty ContentStream, and it is falsy

A page that draws no rectangles still has a `ContentStream` object, but `bool()` of it is
**False** while `len(contents.operations)` is in the hundreds — the object only becomes truthy
once something has iterated it. So the natural guard

```python
for op in (contents.operations if contents else []):   # silently reads nothing
```

skips every page and reports "this page draws no rules". `scripts/fill_label_form_text.py` (and
the probe that led to it) uses `if contents is not None`; the lesson cost six probing rounds of
"the rules are there in one script and gone in the next". The same trap waits in anything that
reads a page's graphics for the first time: assert the operation count, not the truthiness.

Related, for the same reader: **a page can set two tables whose columns are not the same width**
(the owop B4 print draws 66/228/390/552 in one block and 66/174/322/561 in the next). A column
band is only meaningful together with the y-span of the rules that drew it, or a line from the
narrower table below is read as a cell of the wider one above — which is how a read came back
holding the content standard and the indicator glued together.

## 🟠 Two copies of the same database, and only one of them is audited

`data/reference/` is searched **after** `data/curriculum/` and **silently**, so which copy a tool
reads depends on where the file happens to live — and nothing fails when they disagree. For a
year nine subject-grades (computing and french B4–B6, kindergarten KG1/KG2, `english-language B5`)
existed only in the fallback copy, which meant:

* the portal served them, and said `verified: true`, but **Audit A never looked at them** — it
  enumerates `data/curriculum/` by filename pattern, so they were invisible rather than failing;
* their summaries had no `counts` block, so any code assuming `summary["counts"]` raised on exactly
  those subjects;
* nothing established which copy a *fix* should write to: `fix_french_content_standards.py` wrote
  the reference copy of french B7–B9 (correct — that is where the polluted text was, while the
  served copy was already clean), and the fixer scripts had to be re-pointed through `find_data`
  when the promotion moved the files they own.

Promotion (`scripts/promote_reference_subjects.py`, 2026-09-18) is the way out: move the files,
give them summaries derived from their own databases, add their counts to `EXPECTED`, and pin with
a test that nothing is served from the fallback. Two traps sit in the move itself:

* **Audit A's filename pattern is the gate.** `_(B\d)_` and `^B(\d)\.` codes silently excluded
  kindergarten (`_KG1_`, `K1.3.2.1.4`): the files would have been "audited" by not being listed.
  Check the enumerator before trusting it with new data — and note the audit's exit code does not
  distinguish "no issues" from "no files".
* **Promotion exposes empty fields, it does not create them.** `B5.6.4.9.1` had carried an empty
  `cs_desc` since the extraction, and it only surfaced because the file moved under Audit A's nose;
  the print's own cell reads `B5.6.4.9.1.` (one level *longer* than the standard's code), which is
  why the earlier column scan could not match it. When a subject-grade becomes visible to an audit
  for the first time, run the audit *before* celebrating — and keep the print's real defects
  (blank cells) as named exemptions rather than blanking the rule.

## 🟠 Committed rules ≠ deployed rules
Vercel does **not** deploy Firestore rules/indexes. Editing `firestore.rules` and pushing
changes nothing in production until `firebase deploy --only firestore:rules,firestore:indexes`
runs. This is the most common "it works locally / on my emulator but 403s in prod" cause.
`.firebaserc` pins the project (`beacon-educational-consu-8005e`); `make deploy-rules`
runs it. Note that rules pasted into the Firebase console are **not** version-controlled:
the console and `firestore.rules` can silently disagree, and only the repo file is reviewed.

## 🟠 Env vars are required at build time
`VITE_FIREBASE_*` are embedded at build time. Without a `.env.local` (or the equivalent
Vercel env vars) the build **succeeds** and the app fails at the first Firebase call. Copy
`.env.example` → `.env.local`; see [build-deploy.md](build-deploy.md).

## 🟡 Service worker is production-only
`registerSW.js` registers only under `import.meta.env.PROD`. **PWA/offline behavior does not
exist in `yarn dev`** — always verify with `yarn build && yarn preview`.

## 🟡 Stale service worker on localhost
Running several production builds on the same `localhost` origin can leave an old SW serving
a blank shell. Unregister it + clear caches in DevTools, then reload. Harmless on the real
domain.

## 🟡 Slides are browse + export only
`SlideLessons.jsx` builds a deck from the selected week's scheduled lessons and exports PPTX
(`lib/lessonSlidesPptx.js`); it can also save decks to `lesson_slides`. There is **no
authoring form and no deck-view page** — `SlideLessonForm`/`SlideLessonView` do not exist in
this portal. Don't assume slide creation works end-to-end.

## 🟡 Note exports flatten rich text, and drop images
`src/lib/htmlBlocks.js` reads a note's HTML into headings, paragraphs, bullets and numbered
items for the Word/PDF exporters. Inline markup (`strong`, `em`, links) is **dropped, keeping
the text** — deliberate: mis-nested runs would corrupt a paragraph, a missing italic does not.
Inline images (`<img>` from the Tiptap image extension) have no text at all, so they are
**omitted from both exports**. If notes ever carry diagrams a teacher needs on paper, that is
the file to extend first.

## 🟡 The curriculum cache is permanent for the session
`useCurriculum`/`useSchedules` cache each JSON file in a module-level `Map` that never
expires. Curriculum only changes on deploy and the service worker revalidates in the
background, so this is intentional — but it means a hot-fix to a bundle file needs a reload,
and the service worker's cache is named after the bundle hash in
`curriculum/_BUILD_REPORT.json`, which is what makes existing installs pick up a rebuilt
bundle. Edit a bundle file by hand and nothing renames the cache — clear site data.

## ⚪ Minor
- **The retired NCOS app lives under `legacy/`** and is reference-only — nothing in `src/`
  imports it. `make audit` reports its module manifest in a separate `LEGACY` section; that
  output never fails the audit.
- **`make audit` is only about data.** Errors mean the portal cannot source part of the
  dataset; the 9 subject-grades backed only by `data/reference/` are warnings by design.
- **The dev server runs on port 5199**, and `vite.config.js` needs
  `allowedHosts: ['.e2b.app', 'localhost']` for cloud sandboxes (Vite answers 403
  "Blocked request" otherwise).
- **The curriculum bundle is committed and large** (39.7 MB in `public/curriculum/`). It is
  cached by the service worker, so the first load is the expensive one.
- **Tailwind v4 can't `@apply` classes from `@layer components`.** The design vocabulary in
  `src/index.css` is defined with `@utility` for this reason — see
  [conventions.md](conventions.md).
