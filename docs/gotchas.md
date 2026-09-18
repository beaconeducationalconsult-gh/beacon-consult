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

`src/firestoreRules.test.js` fails if a collection the client lists un-filtered loses its
document-independent branch.

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
CORE COMPETENCIES column in `cs_desc` and a fabricated `B7.4.2.3.1` stub record, while the served
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

## 🟡 The curriculum cache is permanent for the session
`useCurriculum`/`useSchedules` cache each JSON file in a module-level `Map` that never
expires. Curriculum only changes on deploy and the service worker revalidates in the
background, so this is intentional — but it means a hot-fix to a bundle file needs a reload,
and **bumping `CACHE_VERSION` in `public/sw.js`** is what makes existing installs pick up new
curriculum, quotes, or shell files.

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
