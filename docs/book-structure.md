# Beacon Textbook & Workbook Series — Structure Specification

Agreed structure for the publishing project. Every book is generated as a
Word (.docx) skeleton from the curriculum database, then completed and
polished by authors. Pilot: **B1 Mathematics**.

Decisions locked:

- Organizing principle: **Chapter = Strand · Unit = Sub-strand ·
  Topic = Content Standard · Lesson = Indicator**
- Book numbering mirrors the NaCCA code segments exactly:
  Chapter 1 · Unit 1 · Topic 1 · Lesson 1 ⇔ `B1.1.1.1.1`
- **Collapse rule:** when a Topic contains a single Lesson, the topic goal
  (content-standard description) prints inside the lesson header instead of
  as a separate heading; numbering stays four-deep
- Production: **generated skeleton → authors edit in Word**
- Granularity: **one lesson per indicator** (all subjects)

---

## 1. Textbook anatomy

### Front matter
| Page | Source |
|---|---|
| Title page (series name, subject, grade, Beacon branding) | generated |
| Copyright / acknowledgements | template text |
| How to use this book (explains lesson features & icons) | template text |
| **Curriculum coverage map** — table of Strand → Sub-strand → Content Standard → Indicator → Lesson/page | generated from db |
| Table of contents | generated |

### Chapter (one per strand)
- Chapter opener: strand name, full-page illustration prompt (author/artist),
  "In this chapter you will…" bullets (generated from the strand's indicators)
- Units in curriculum order

### Unit (one per sub-strand)
- Unit intro paragraph (author)
- Topics in code order
- **Unit review exercise** (seeded from Question Bank where available)

### Topic (one per content standard)
- Topic heading: number + **topic goal** — the content-standard description
  ("Demonstrate understanding of…") with its CS code chip
- Lessons in code order
- **Topic check-up** — 3–5 questions assessing the content standard as a
  whole (the level SBA and exams reference)
- *Collapse rule applies when the topic has one lesson (see above)*

### Lesson (one per indicator, 2–4 pages) — the core template
| # | Feature | Source |
|---|---|---|
| 1 | Lesson number + child-friendly title | title authored; number generated |
| 2 | Indicator code chip + "By the end of this lesson…" objective | db `code`, `description` / `performanceIndicator` |
| 3 | **Key words** box | db `keywords` |
| 4 | **Let's remember** — 2–3 RPK questions | db `rpk` (B1 maths/science); else author |
| 5 | **Main content** — explanation, worked examples, diagrams (Ghanaian contexts: cedis, local names, markets) | db `main` steps as seed (B1 maths/science); NaCCA exemplars as seed elsewhere; author completes |
| 6 | **Try it** (individual activity) | db `starter`/exemplar seed; author |
| 7 | **Work together** (pair/group activity) + core-competency tag | db `competencies`; author |
| 8 | **What I have learnt** — summary bullets | author (seeded from objective) |
| 9 | **Quick check** — 2–3 self-assessment questions | db `assessment` seed; author |

### End of chapter
- Strand revision exercise (mixed questions across the chapter)
- Project idea ("Do and show")

### Back matter
- Glossary (generated: keywords → author adds child-level definitions)
- Answers to Quick checks (or moved to Teacher's Guide)
- Index

---

## 2. Workbook anatomy (1:1 companion)

- Identical lesson numbering and codes to the textbook.
- **Per lesson — one worksheet (1–2 pages):**
  - **A. Remember** — recall: fill-in, matching, MCQ (3–5 items)
  - **B. Apply** — practice in context (3–5 items, working space)
  - **C. Challenge** — extension / reasoning (1–2 items)
  - *At home* task where natural (family/community connection)
- **Per topic (content standard):** check-up test with marks (SBA style —
  the CS is the unit of assessment in official blueprints)
- **Per term:** end-of-term assessment aligned to the scheme-of-learning
  weeks (B1 maths/science: generated from the schedule's term/week mapping)
- Pupil progress page per strand (tick each lesson completed)
- Answer key at the back (option: separate Teacher's Answer Booklet)

Question Bank integration: workbook exercises tagged with indicator codes can
be seeded from, and contributed back to, the `questions` collection.

---

## 3. Pilot: B1 Mathematics

Data available (all generated automatically into the skeleton):

- 24 indicators → 24 lessons; 4 chapters (NUMBER 16 lessons ·
  ALGEBRA 1 · GEOMETRY AND MEASUREMENT 5 · DATA 2); 9 units;
  **12 topics** (content standards), of which 6 are single-lesson topics
  (collapse rule applies); largest topic: 6 lessons (Counting)
- 180 daily schedule lessons carrying `rpk`, `starter`, `main` (step lists),
  `plenary`, `assessment`, `performanceIndicator`, `keywords` per session —
  seeds features 2–9 of nearly every lesson
- All 24 content-standard descriptions and keyword sets present

Estimated pilot extent: ~90–120 textbook pages + ~60 workbook pages.

## 3b. Subject flavours

The lesson anatomy, numbering and TODO system are identical across subjects;
each subject adds a flavour via a profile in the generator:

| Subject | Extra features |
|---|---|
| Science | `[FIGURE …]` art-brief per lesson (seeded from curriculum resources) · **Observe — Let's find out** practical with materials list · workbook **D. Draw and label** |
| Computing | screenshot-type figures · **On the computer** activity |
| Languages (English, Ghanaian, French) | **Reading passage / dialogue** placeholder with grade-band length target (B1–3: 40–80 words · B4–6: 80–150 · B7–9: 150–300) |
| Creative Arts / CAD | step-by-step photo-sequence figures · **Make it** activity · workbook draw section |
| Kindergarten | picture-first: full illustration brief per lesson · workbook draw section |
| Mathematics | diagram figures in Geometry/Data strands only |

Every figure placeholder is logged in a **Figure register** table at the back
of the textbook (figure id, type, suggested subject, artwork status) for the
illustrator workflow.

## 4. Production pipeline

1. `seed/build_book_skeleton.py <subject> <grade>` → generates
   `books/<grade>/<subject>-textbook-skeleton.docx` and
   `-workbook-skeleton.docx`, styled (Beacon branding, feature boxes,
   AUTHOR-TODO placeholders where content is needed)
2. Authors complete content in Word (tracked changes)
3. Editorial review → layout/illustration → GES/NaCCA submission format
4. Re-runs are safe: the generator never overwrites an existing book file —
   it writes a new `-vN` file for comparison

## 5. Naming & files

```
books/
  B1/
    mathematics-textbook-skeleton.docx
    mathematics-workbook-skeleton.docx
  ...
```

Series title, cover copy and pricing are business decisions — placeholders
in the generator until confirmed.
