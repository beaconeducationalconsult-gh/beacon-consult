# Project TODO

The live backlog, ordered by **dependency**. Rewritten 2026-09-17 after the NCOS kernel app
was folded out to `legacy/` — items about that app (module `validate()`, `schoolId` history,
`generated_materials`, `storage.rules`, the 36 TypeScript errors) are **retired**, not
pending. Nothing in `src/` imports `legacy/`.

> **Anchor:** the portal must produce at least what the books produce, and must not serve
> curriculum it cannot source. Everything below is scored against that.

**Verify state at any time with:**

```bash
make check     # lint + tests + validate-curriculum + inventory + production build
make audit     # dataset vs portal agreement -> data/inventory.json (warnings are honest)
yarn test      # vitest: src/lib, buildTree, and contracts over public/curriculum
```

`make check` is also run by CI (`.github/workflows/ci.yml`) on every push, which
additionally fails if `data/inventory.json` is stale.

---

## P0 — the portal cannot run for real users yet

| # | Item | Why | Size |
|---|------|-----|------|
| P0-1 | **Configure Firebase**: copy `.env.example` → `.env.local` with the six `VITE_FIREBASE_*` values, and set the same on Vercel (Production + Preview) | Vite embeds these at build time. Without them the build is green and every Firebase call fails at runtime — no login, no content | S |
| P0-2 | **Deploy rules + indexes**: `make deploy-rules` (or paste `firestore.rules` into the console). `.firebaserc` is committed and pins `beacon-educational-consu-8005e` | **Done** — the user published the ruleset and reported it working. Caveat: the copy in the console predates the list-query fix in `08b19ab` and needs re-pasting (see P2-7 and gotchas.md) | S |
| P0-3 | **Bootstrap the first admin**: create an account, then set `role: 'admin'` (and `status: 'approved'`) on its `users/{uid}` doc in the Firebase console | **Done** — confirmed by the user. This is the only way in: sign-up forces `status: 'pending'`/`role: 'member'`, self-edits cannot change `role`/`status`, and only an admin can approve — so the console is the bootstrap path, and it must be repeated for each new school's first admin | S |
| P0-4 | **Drive the real flows once deployed** (the code bible's Phase 7): sign up → approve → create → view → edit → delete for a scheme, a plan, a question, and a note; check offline behavior with `yarn build && yarn preview` | A green build proves nothing about rules, indexes, or the service worker | M |

## P1 — data integrity (what teachers actually read)

| # | Item | Why | Size |
|---|------|-----|------|
| P1-1 | ~~**Cross-check the 8 unaudited subject-grades against their NaCCA PDFs**, then promote them into `data/curriculum/` and add their counts to the `EXPECTED` table in `scripts/audit/audit_a_databases.py`~~ — **done 2026-09-18**: all 8 pass Audit B, their text fields are cleaned, and `scripts/promote_reference_subjects.py` moved them (and `english-language B5`) into `data/curriculum/` with counts-bearing summaries and rows in `EXPECTED`. Audit A now covers all 84 subject-grades | The portal served curriculum for 8 subject-grades (~714 indicators) that had never been checked against its source. It was real NaCCA curriculum with unverified extraction; the whole arc is in the progress notes below | M |
| P1-9 | ~~**`english-language B5` is audited but not reproducible**~~ — **done 2026-09-18**: promoted into `data/curriculum/`, where Audit A enumerates it and its `EXPECTED` row (133) holds. Audit A now reports 84 files / 84 PASS and reproduces every row it prints | Audit A's committed row could not be re-derived by anyone | S |
| P1-10 | **`B7.4.2.3.1` is a fabricated record in `data/reference/french_B7_...`** — its `cs_desc` reads `"French Content Standard B7.4.2.3"` and its `ind_desc` `"French Learning Indicator B7.4.2.3.1"`, and the only occurrence of that code in `french_CCP_B7-B9.pdf` is the worked example in the front matter (p. xxix) | The served copy (`data/curriculum/`) has 64 records and not this one, and Audit A's `EXPECTED` table says 64, so the record is an extraction artefact rather than curriculum. Left in place: deleting data is the user's call, and `scripts/fix_french_content_standards.py` reports it instead of inventing a standard for it | S |
| P1-2 | ~~**Fill the L1 provenance gaps**~~ — **done 2026-09-18**: `english-language B4`'s summary was in `data/reference/` and was promoted; `mathematics B1` had none and now has `math_curriculum_summary.json`, its `sourceTitle`/`sourceUrl` taken from the B2/B3 summary of the same document. (`science B1` already had one — the row was stale.) Every one of the 84 L1 pairs now has a summary with a `counts` block | 184 indicators had unverifiable provenance | S |
| P1-3 | ~~**Repair the 8 malformed reference summaries** (no `counts` block)~~ — **done 2026-09-18**: the eight were the promoted subject-grades, and their summaries now carry `counts` + a per-strand breakdown derived from their databases, with the vestigial `sourceVerified` flag dropped (nothing read it, and it said `false` about subject-grades Audit B passes) | Any code that reads `summary['counts']` raised on them | S |
| P1-4 | **Say what L2 is, then act on it** — `competencies`, `resources`, `keywords`, `assessment` have exactly one distinct value per subject-grade; `starter` 75% / `main` 41% distinct, `rpk`/`plenary`/`assessment` ≈ 1% | Marketing and authoring budget depend on this. Either enrich per indicator or label generated documents honestly as templated | S |
| P1-5 | **Question bank content**: zero questions exist in the bundle (`public/curriculum/questions/` does not exist); `data/questions/` holds one mathematics B4 file | The generators render an empty selection from an empty bank — the highest-value content the dataset lacks | L |
| P1-6 | **Clean the 58 L2 `ind_desc` records with a repeated trailing sentence** (0.4% of slots) at the extraction source | Visible artefact in generated documents | S |
| P1-7 | **`indicatorDocId` keys on the bare indicator code** (`src/hooks/useCollection.js`) | `B4.1.1.1.1` exists in all ten B4 subjects, so the id is not grade-unique. Currently exported but unused — scope it by subject (or use `id`) before anything adopts it. See `docs/curriculum-data.md` | S |
| P1-8 | **The book skeleton seeds only the first session of each indicator** — `seed/build_book_skeleton.py` reads `sessions[0]` for the title, RPK, starter, main, plenary and performance indicator | Its own docstring promises "everything the database knows is *seeded*". Measured on B4: 263 of 377 indicator slots carry more than one session, and for 134 of them the later sessions hold *different* main-activity text — so those sessions' teaching content never reaches the draft books. Either collapse the sessions into the one lesson deliberately (and say so), or emit them as lesson sessions/variants | M |

### P1-1 progress — kindergarten KG1/KG2 (2026-09-18)

The KG source PDF arrived (`data/sources/kindergarten_KG1-KG2.pdf`, 231pp, genuine NaCCA
*Kindergarten Curriculum (KG 1&2)*, September 2019). Checking it turned up the same class of
fault as computing/french, plus one of its own:

- **strand names were placeholders** — all 339 indicators read `"Strand 1"`…`"Strand 7"`. The
  curriculum is themed, and the PDF names each one: ALL ABOUT ME, MY FAMILY, VALUES AND
  BELIEFS, MY LOCAL COMMUNITY, MY NATION GHANA, ALL AROUND US, MY GLOBAL COMMUNITY — the same
  seven for both grades. `fix_reference_structure.py` now covers kindergarten and wrote them.
- **one indicator was a stub** — `K1.1.1.1.1`, the *first* KG1 indicator a teacher meets, had
  `ind_desc: "Kindergarten Learning Indicator K1.1.1.1.1"`: the code restated, no content. The
  script now refills descriptions that are stubs from the PDF text, and did.

**Codes match the source**: K1 169/169 exactly; K2 170/170 with one extra code in the PDF
(`K2.1.1.1.51`) that is a **misprint inside an exemplar cross-reference** — the same reference is
printed correctly as `K2.1.1.1.5` on the following line. Reported by the audit as informational.

Finding the KG strand names needed a rule the earlier pass did not have: the print labels its
strand-7 heading `SUB STRAND 7: MY GLOBAL COMMUNITY` (p135), while `SUB STRAND 7: GARDENING`
(p125) really is a sub-strand. The scan now reads a sub-strand heading as a strand heading only
when its number agrees with the codes beneath it *and* no strand heading for that number has been
seen yet.

**Then the same field gaps as computing/french** — `keywords` empty on all 339 and descriptions
carrying the PDF's footer text — plus the KG content standards; all three were closed on
2026-09-18 by `scripts/fix_reference_text.py`, and the two databases were promoted into
`data/curriculum/` the same day (see the promotion note below).

### P1-1 progress — computing + french B4–B6 (2026-09-18)

The two source PDFs arrived and were checked against the served data. **Both are genuine NaCCA
documents** (Computing 76pp, French 123pp, September 2019) and they now sit in `data/sources/`
as `computing_B4-B6.pdf` / `french_B4-B6.pdf`, giving both subjects B4–B9 source coverage
alongside the existing `*_CCP_B7-B9.pdf` files.

**The indicator sets match the source exactly** — computing 27/81/98 and french 88/90/89 for
B4/B5/B6, with zero codes missing and zero invented. That is the question the audit could not
answer before, and it is now answered: the *content* of these six subject-grades is complete and
correctly coded.

**What was wrong was the hierarchy labels.** Two distinct faults, both fixed by
`scripts/fix_reference_structure.py` (which re-reads the strand headings from the PDFs):

| | before | after |
|---|---|---|
| computing B4 | `strand: "Strand 1"` (placeholder) | `"1. WORD PROCESSING"` |
| french B4 | `strand: "Saluer et prendre congé"` — a **sub-strand** name, one level too low | `"1. L'IDENTITÉ"` |

473 indicators changed, and the change is exactly the two fields (verified: indicator key sets
identical, only `strand`/`sub_strand` differ). The strand names now match each PDF's table of
contents. `sub_strand` became `"Sub-strand B4.1.1"` — the generic form every audited subject
already uses, so the browse tree looks the same whichever copy a subject comes from. The real
sub-strand names are in the PDFs if the app ever wants to display them.

**Audited.** These six now pass Audit B (below), so `verified` is true for them and the app no
longer flags them. What remains is field completeness, not authenticity:

**The field gaps are closed** (2026-09-18). All three were settled against the prints in
`data/sources/`, never by rewriting:

- ~~**french: content standard empty** for 85/88 (B4), 89/90 (B5), 88/89 (B6)~~ — **done
  2026-09-18**, see the content-standards note below. All 266 records now carry the skill area
  the print names as the standard, and the eleven french B7–B9 standards that had the
  neighbouring column glued in front of them were repaired in the same pass (36 records).
- ~~**keywords empty** for all 473 (and for KG1/KG2, 169/170)~~ — **done 2026-09-18**: all 812
  records of the eight subject-grades carry the audited convention's tag
  (`computing, b5, upper-primary`, `kindergarten, kg1, kindergarten`). The six drifted reference
  copies of audited subjects (creative-arts B4–B6, social-studies B7–B9) were stamped with the
  tag their curriculum copy carries — their *records* are still a stale extraction and stay out
  of scope.
- ~~**Neighbouring columns and page footers bleed into indicator text**~~ — **done 2026-09-18**:
  397 `ind_desc` values were cleaned. The furniture was the page footer (118 records, e.g.
  `"… desktop 3 © NaCCA, Ministry of Education 2019"`), the reference codes (`LL2`, `(CC)`,
  `N3.1` — 166), the CORE COMPETENCIES list of the column next door (54, incl. the few that
  *opened* with it), the table's headings, the row markers the extractor read past, and one cell
  label. 383 of the 397 survivors are verbatim readings of the record's own row and 14 are
  word-by-word (the extraction braided the columns); nothing the print does not carry was
  written, and none is left over.
- ~~**KG1–KG2 content standards**~~ — **done 2026-09-18**: 13 records were filled (the print's
  standard column had been missed for `K1.3.1.1` and `K2.1.3.1`), 7 were completed, 21 trimmed of
  the heading next door, and 5 (`K2.5.1.1`) replaced — they held indicator-column text, and the
  displaced values are kept in `data/audit/reference_text_fixes.json`. `K1.3.2.1`'s cell is
  **blank in the print**, so its five records stay empty, and the audit's
  "the print has no sentence" verdict for it stands as a print defect.

The work and its trail are `scripts/fix_reference_text.py` (report by default, `--apply` writes)
and `data/audit/reference_text_fixes.json`; the rule and the residual check are in
`docs/curriculum-data.md`.

### P1-1 — the promotion (2026-09-18)

`scripts/promote_reference_subjects.py` (report by default, `--apply` moves files) finished the
item. Eighteen files moved into `data/curriculum/` — the databases and summaries of computing
B4–B6, french B4–B6 and kindergarten KG1/KG2 — plus `english-language B5` (the database, and the
summary that was already there) and `english-language B4`'s summary. Two summaries were written
from scratch: `english-language B4`'s (its file *was* the reference copy, which moved) and
`mathematics B1`'s, whose provenance came from the B2/B3 summary of the same document.

Three things had to be true for the move to be honest, and each was checked before the files went:

* **Audit A had to be able to audit them.** It enumerated `_B4_`-shaped file names and validated
  `^B(\d)\.` codes, so kindergarten's `_KG1_`/`K1.3.2.1.4` shape was invisible to it. It now
  enumerates `_KG1_`, accepts the `K`/`KG` mismatch in the grade column, and keeps the file-name
  form as the grade. Its `EXPECTED` table gained the rows: computing `B4 27 B5 81 B6 98`, french
  `B4 88 B5 90 B6 89`, kindergarten `KG1 169 KG2 170`.
* **The one empty field the move would expose had to be filled.** `computing B5.6.4.9.1` had no
  `cs_desc` although the print prints `Demonstrate proficiency in Digital Literacy.` on p48 — the
  computing print's own cell code reads `B5.6.4.9.1.` (a three-part standard keyed as
  `B5.6.4.9`), which the earlier scan could not match. `fix_reference_text.py` now reads the
  print's content-standard column for computing too, fills empty fields from it, and reports
  standards whose cell is blank. French B6's `B6.1.2.5.3` and kindergarten's five `K1.3.2.1`
  records are the two that stay empty, because the print's own cell is blank — now carried as
  named exemptions in Audit A's `BLANK_IN_PRINT` and printed as `blank-in-print=N`, so the audit
  still fails on every *other* empty field.
* **The tooling had to stop assuming the old layout.** `fix_reference_structure.py`,
  `fix_french_content_standards.py` and `fix_reference_text.py` now resolve their files through
  `find_data` instead of joining onto `data/reference/`, so they follow the served copy. All three
  re-run clean: 0 indicators would change.

Result: **Audit A 84 files / 84 PASS / 4,040 indicators** (it printed 75 PASS before), Audit B
unchanged at 83 PASS + 1 WARN, and the inventory's L1 reports 84 pairs / 84 summaries, its
"8 app-bundle subject-grades exist ONLY in `data/reference/`" warning gone. The bundle stamps
`source: 'curriculum'` for all 84, and the test that used to pin nine fallback-served
subject-grades now pins that *nothing* is served from the fallback.

What stays in `data/reference/`: the older extraction of the same subject-grades
(`english-language_B5_curriculum_db.json`, `english-language_B[2-6]_curriculum_db.json`), the
drifted creative-arts B4–B6 and social-studies B7–B9 copies (P1-6/P1-10 territory) and the french
B7–B9 copies, which is where `fix_french_content_standards.py` keeps its repair of the
neighbour-column bleed. They are inert: `find_data` prefers `data/curriculum/`, and nothing served
comes from there any more.

### P1-1 progress — the french content standards (2026-09-18)

`cs_desc` was empty for 262 of the 267 french B4–B6 records, and the five that were filled had
been harvested from *indicator* rows. The reason is not a lost field: **the french B4–B6 print
has no sentence-style content standards.** Its CONTENT STANDARDS column holds one of four skill
areas, and the SCOPE AND SEQUENCE table (pp. xviii–xx) lists exactly those four — in that order —
for every one of the document's 18 sub-strands. The front matter (p. xvii) defines the code, so
the fourth component *is* the content-standard number and therefore the skill:

```
B4.1.2.3.1   B4 = class   1 = strand   2 = sub-strand   3 = content standard   1 = indicator
                                                        ^ 1 CO  2 PO  3 CE  4 PE
```

`scripts/fix_french_content_standards.py` (report by default, `--apply` writes) cross-checks both
claims against the PDF before writing — 18 sub-strand blocks listing the four skills in order, and
240 CS cells in the body carrying those same four labels and nothing else — then writes the label.
**266 records filled**, one per line, nothing else touched. The five values it replaced, and the
rule itself, are recorded in `data/audit/french_content_standards.json`.

**The same pass repaired french B7–B9**, where the defect was the mirror image: eleven content
standards (37 records) in `data/reference/` carried the CORE COMPETENCIES column *in front of* the
statement, or a placeholder (`"French Content Standard B9.2.3.1"`). All eleven statements were
recovered from `french_CCP_B7-B9.pdf` and written (36 records); the statements agree with the tail
of the polluted values in 35 of the 36 cases, which is how we know the recovery is not inventing
anything. Note that the **served** copies (`data/curriculum/`) were already clean — this repaired
the unsent copy, so nothing a teacher sees changed for B7–B9.

Two print defects came out of it, both reported rather than guessed at:

- **`B6.1.2.5.3`** — the print numbers a *fifth* content standard (p93) in a sub-strand whose scope
  table lists four, so no skill can be named. Its `cs_desc` stays empty, and a test pins that it is
  the only one.
- **`B9.2.3.1`** — the print labels the content standard `B8/JHS2.2.3.1` inside the B9 section
  (p102). The statement ("Comprendre et s'exprimer sur son pays") was recovered by anchoring on the
  indicator row rather than on the code, and the discrepancy is in the audit artefact.

B4–B6 are served from `data/reference/`, so the fill reaches teachers: `public/curriculum` carries
all 266 descriptions, and four contract tests in `src/curriculumBundle.test.js` hold the rule, the
one deliberate blank, the bundle, and the absence of neighbour-column text.

## P2 — engineering debt that makes every future fix expensive

> **P2-2 (CI workflow) is done** — `.github/workflows/ci.yml` runs `make check` plus a
> stale-inventory guard on every push. Its number is left empty rather than renumbering,
> because other items reference these ids.

| # | Item | Why | Size |
|---|------|-----|------|
| P2-1 | **Firestore rules unit tests** with the emulator, and smoke tests for the exporters (`lessonPlanDocx`, `schemePdf`, …) | Rules are the real security surface (see `docs/analysis/FINAL ANALYSIS.md`). The **Word** exporters are no longer untested — `src/lib/docxExport.test.js` unzips the generated `.docx` and checks the parts Word obeys (styles resolve, fonts declared, A4, footer present); the PDF/PPTX exporters and the emulator half of this item remain open. `src/lib` helpers, `buildTree`, the `public/curriculum` bundle contracts **and the rules invariants** are now covered by `yarn test` — but those are static: they prove a guard was not deleted, not that a permission decision is right. Only the emulator can do that | M |
| P2-3 | **Bundle strategy**: chunk the 39.7 MB bundle per grade+subject and key the service-worker cache off a content hash (or automate the `CACHE_VERSION` bump) | `b9_schedules.json` alone is 4.85 MB; today a rebuilt bundle reaches returning users only after a manual `sw.js` edit | M |
| P2-4 | **Pagination** for the capped lists (`useCollection` max 100, `QuestionBank` 200, `Search` 100 per collection) with `startAfter` cursors | Silent truncation is indistinguishable from "no more data" | M |
| P2-5 | **Slides**: browse + PPTX export exist; there is no authoring form and no deck-view page | Half-built feature; either finish the authoring flow or remove the affordance (see `docs/gotchas.md`) | M |
| P2-7 | **Rework note/plan visibility into queries** — `visibility` and note `status` are saved but cannot gate reads while the list pages query un-filtered (gotchas.md). To bring back private drafts, split each list into "mine" (`where authorId == uid`) and "published" (`where status/visibility == …`), then re-add the field conditions to the rules | Restores per-document privacy without breaking list queries | M |
| P2-9 | **Audit C2 wants 8 generated `Basic1_*_Lesson_Plans_Full_Year.docx` files that are not in the repository** — `scripts/audit/audit_c_lessons.py` now resolves paths correctly and reports `DOCX missing` for all 8 | The committed `data/audit/audit_c_results.json` still records them as PASS (238 KB, 215 KB, …) from when they existed. Left intact rather than overwritten — the documents are build outputs, and regenerating them is a bigger job than the audit. Audit C1 (the enriched lesson JSONs) passes for all 8 subjects, 180 lessons each | S |
| P2-8 | **~150 legacy scripts still import `_compat` from a `tools/` directory that no longer exists** (`parents[2] / "tools"`, and a bare `Path` that was never imported) | The three `scripts/audit/` scripts were repaired on 2026-09-18 so the audits can run again — until then the audit tooling was dead and `audit_a_results.json` could not be regenerated. The remaining scripts are one-shot generators that already ran, so they are lower priority, but any that is needed again will hit the same wall | S |
| P2-6 | **Repo hygiene**: decide whether the 38 MB curriculum bundle stays in git (or moves to a release artefact) | Keeps clones and diffs manageable. **Partly done**: the 4 tracked `.pyc` files were untracked on 2026-09-18 (`.gitignore` already covered the pattern — they predated it, and gitignore never applies to already-tracked files). The bundle question is open | S |

## P3 — product bets, once the P0s are done

| # | Item | Notes |
|---|------|-------|
| P3-1 | **Publish the B1 Mathematics pilot books** and roll the generator out subject by subject | `make book-skeleton SUBJECT=mathematics GRADE=B1` works; `books/` is gitignored (regenerable, never overwritten) |
| P3-2 | **Offline packs** — per subject/class downloads for schools without reliable connectivity | Needs P2-3 first |
| P3-3 | **Store generated documents, not just metadata** — history has no re-download because nothing writes to Storage | Needs a `storage.rules` (see the paid-delivery work in `docs/deliveries-roadmap.md`) |
| P3-4 | **Visualisation engine** — 3–5 interactive models on one subject-grade as a pilot, not 50 | Needs P2-3 to be realistic in classrooms |
| P3-5 | **Study-notes export** (PDF/DOCX) | Notes are network-only today; the code bible lists exactly how to add an exporter |

---

## Deferred by decision

| Item | Why not | Revisit when |
|---|---|---|
| **Server-side hard gate** for paid downloads (moves final generation server-side so a clean file cannot exist before approval) | Needs Cloud Functions; Spark plan does not allow them | Agents are selling consistently, or bypassing the soft gate becomes a real risk |
| **Mobile Money automation** (gateway webhook → `paid`) | Same infrastructure blocker; manual "Mark as paid" collects MoMo today at ₵0 | Volume makes the manual loop a bottleneck |
| **Ad-hoc quiz/question-paper delivery** | They are generated from a selection with no stored doc, so the approve/regenerate flow has nothing to re-render; persist the artefact first | P1-5 gives the bank content worth gating |
| Building the Studio as a separate web app | One author; `scripts/` + git already is the Studio | A second content author joins |
| Selling printed books as the primary channel | The owner is replacing the consortium print model with a self-serve portal | — |
| Porting the Python generators to JavaScript | They work; the browser needs the *same content model*, not the same language | The pipeline becomes a runtime dependency |
| Regenerating the 73 books before every demo | The CI workflow exists, but does not build books yet: if the books matter, build them in the pipeline, not by hand | — |

---

## Numbers referenced by this file

All from `make audit` (`data/inventory.json`). If an item above disagrees with the
inventory, the inventory is right and the item is stale — fix the item.
