#!/usr/bin/env python3
"""Generate a textbook + workbook skeleton from the curriculum database.

    python3 seed/build_book_skeleton.py <subject> <grade> [--series "..."] [--quiet]

Structure (locked in docs/book-structure.md):

    Chapter = Strand · Unit = Sub-strand · Topic = Content Standard · Lesson = Indicator

Book numbering mirrors the NaCCA code segments: Chapter 1 · Unit 1 · Topic 1 ·
Lesson 1 ⇔ ``B1.1.1.1.1``. When a topic holds a single lesson the topic goal
prints inside the lesson header instead of as its own heading (the collapse
rule), but the numbering stays four-deep.

Output goes to ``books/<grade>/`` and the generator **never overwrites**: if a
file exists it writes ``…-skeleton-v2.docx`` so an author's edited copy is safe.

Everything the database knows is *seeded*; everything it does not is written as
an AUTHOR-TODO placeholder rather than invented prose.

**One lesson per indicator, and one session is the draft.** A lesson seeds from
the indicator's *first* scheduled session (so the header can say which one), and
every later session whose own `main` activity differs prints underneath it as
"Later sessions" — the book sets one lesson per indicator, and those sessions'
teaching content would otherwise never reach the draft.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor
except ModuleNotFoundError:  # pragma: no cover - guidance beats a traceback
    sys.exit(
        "python-docx is required:  pip install -r requirements.txt\n"
        "(the generator writes real .docx files, not markdown)"
    )

ROOT = Path(__file__).resolve().parent.parent
CURRICULUM = ROOT / "data" / "curriculum"
LESSONS = ROOT / "data" / "lessons"
REFERENCE = ROOT / "data" / "reference"
BOOKS = ROOT / "books"

BRAND = "Beacon Educational Consult"
INDIGO = RGBColor(0x4F, 0x46, 0xE5)
AMBER = RGBColor(0xB4, 0x53, 0x09)
MUTED = RGBColor(0x64, 0x74, 0x8B)

GRADE_LABELS = {
    "KG1": "KG 1", "KG2": "KG 2",
    **{f"B{n}": f"Basic {n}" for n in range(1, 10)},
}

# Subject flavours — docs/book-structure.md §3b.
FLAVOURS: dict[str, dict] = {
    "science": {
        "figure": "Observe and label a real object or a diagram from the school environment.",
        "extra_activity": ("Let's find out", "Practical: list the materials, the steps and the safety note."),
        "workbook_extra": "D. Draw and label",
    },
    "computing": {
        "figure": "Screenshot or screen sketch of the tool being taught.",
        "extra_activity": ("On the computer", "Describe the exact clicks on the school's device."),
        "workbook_extra": "D. On the computer",
    },
    "english-language": {
        "figure": "Illustration for the reading passage.",
        "extra_activity": ("Reading passage / dialogue", "Grade-band length: B1–3 40–80 words · B4–6 80–150 · B7–9 150–300."),
        "workbook_extra": "D. Write",
    },
    "ghanaian-language": {
        "figure": "Illustration for the passage; check the orthography with a first-language speaker.",
        "extra_activity": ("Reading passage / dialogue", "Grade-band length: B1–3 40–80 words · B4–6 80–150 · B7–9 150–300."),
        "workbook_extra": "D. Write",
    },
    "french": {
        "figure": "Illustration for the dialogue.",
        "extra_activity": ("Dialogue", "Grade-band length: B1–3 40–80 words · B4–6 80–150 · B7–9 150–300."),
        "workbook_extra": "D. Écrire",
    },
    "creative-arts": {
        "figure": "Step-by-step photo sequence of the making process.",
        "extra_activity": ("Make it", "List the local materials and the safety points."),
        "workbook_extra": "D. Draw and make",
    },
    "creative-arts-design": {
        "figure": "Step-by-step photo sequence of the making process.",
        "extra_activity": ("Make it", "List the local materials and the safety points."),
        "workbook_extra": "D. Draw and make",
    },
    "mathematics": {
        "figure": "Diagram for the Geometry and Data strands only.",
        "extra_activity": ("Worked example", "Model on the board with the same numbers, then change one number."),
        "workbook_extra": "D. Challenge",
    },
    "kindergarten": {
        "figure": "Full-page picture brief — children should be able to 'read' it before any text.",
        "extra_activity": ("Picture talk", "Ask what the children can see, then act it out."),
        "workbook_extra": "D. Draw and colour",
    },
    "_default": {
        "figure": "Diagram or photograph that carries the core idea of this lesson.",
        "extra_activity": ("Do and show", "Explain what learners make or demonstrate."),
        "workbook_extra": "D. Challenge",
    },
}

SUBJECT_ALIASES = {
    "mathematics": ["mathematics", "math", "maths"],
    "math": ["math", "mathematics", "maths"],
    "english": ["english", "english-language"],
    "english-language": ["english-language", "english"],
    "social-studies": ["social-studies", "social_studies"],
    "rme": ["rme", "religious-and-moral-education"],
    "owop": ["owop", "our-world-our-people"],
    "creative-arts": ["creative-arts", "creative_arts"],
}


# ── data loading ─────────────────────────────────────────────────────────────

def _candidates(subject: str, grade: str, kind: str) -> list[Path]:
    """Every filename this subject/grade might be stored under.

    Naming is inconsistent in the dataset: B1 files drop the grade, some
    subjects use a hyphen and some an underscore, and mathematics is stored as
    ``math`` while its module is called ``mathematics``.
    """
    names: list[str] = []
    for alias in SUBJECT_ALIASES.get(subject, [subject]):
        for variant in {alias, alias.replace("-", "_"), alias.replace("_", "-")}:
            if kind == "curriculum":
                if grade == "B1":
                    names.append(f"{variant}_curriculum_db_clean.json")
                names.append(f"{variant}_{grade}_curriculum_db_clean.json")
            else:
                if grade == "B1":
                    names.append(f"{variant}_lessons_enriched.json")
                names.append(f"{variant}_{grade.lower()}_lessons_enriched.json")
    folders = (CURRICULUM, REFERENCE) if kind == "curriculum" else (LESSONS, REFERENCE)
    seen, out = set(), []
    for name in names:
        for folder in folders:
            path = folder / name
            if name not in seen and path.exists():
                out.append(path)
                seen.add(name)
    return out


def load_indicators(subject: str, grade: str) -> dict:
    for path in _candidates(subject, grade, "curriculum"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data and all(isinstance(v, dict) for v in data.values()):
            print(f"  curriculum: {path.relative_to(ROOT)}  ({len(data)} indicators)")
            return data
    sys.exit(
        f"No curriculum database found for {subject} {grade}.\n"
        f"Looked in {CURRICULUM.parent.name}/curriculum and {REFERENCE.parent.name}/reference — "
        f"see docs/curriculum-data.md."
    )


def load_lessons(subject: str, grade: str) -> list[dict]:
    for path in _candidates(subject, grade, "lessons"):
        rows = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(rows, list) and rows:
            print(f"  schedule:   {path.relative_to(ROOT)}  ({len(rows)} lesson slots)")
            return rows
    print("  schedule:   none — lessons will be seeded from the indicator text only")
    return []


# ── structure ────────────────────────────────────────────────────────────────

@dataclass
class Lesson:
    number: str            # B1.1.1.1.1
    title: str
    objective: str
    seeds: dict = field(default_factory=dict)
    sessions: list[dict] = field(default_factory=list)
    # the scheduled sessions whose own `main` differs from the seeded one — the
    # lesson above drafts from the indicator's *first* session, so these print as
    # the sessions that follow it rather than being dropped
    later_main: list[dict] = field(default_factory=list)

    @property
    def code_parts(self) -> list[str]:
        return self.number.split(".")


@dataclass
class Topic:
    code: str              # B1.1.1.1
    goal: str
    lessons: list[Lesson] = field(default_factory=list)

    @property
    def collapsed(self) -> bool:
        return len(self.lessons) == 1


@dataclass
class Unit:
    name: str
    topics: list[Topic] = field(default_factory=list)


@dataclass
class Chapter:
    name: str
    units: list[Unit] = field(default_factory=list)

    @property
    def lesson_count(self) -> int:
        return sum(len(t.lessons) for u in self.units for t in u.topics)


def clean(value: str | None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def build_structure(indicators: dict, lessons: list[dict]) -> list[Chapter]:
    # A lesson slot is one *session*; several sessions can share an indicator.
    sessions_by_code: dict[str, list[dict]] = {}
    for row in lessons:
        code = clean(row.get("ind_code"))
        if code:
            sessions_by_code.setdefault(code, []).append(row)

    chapters: dict[str, Chapter] = {}
    units: dict[tuple[str, str], Unit] = {}
    topics: dict[str, Topic] = {}

    for code, row in sorted(indicators.items(), key=lambda kv: _sort_key(kv[0])):
        parts = code.split(".")
        if len(parts) < 5:
            continue
        strand = clean(row.get("strand")) or f"Strand {parts[1]}"
        sub_strand = clean(row.get("sub_strand")) or "Sub-strand"
        cs_code = clean(row.get("cs_code")) or ".".join(parts[:4])

        chapter = chapters.setdefault(strand, Chapter(strand))
        unit = units.get((strand, sub_strand))
        if unit is None:
            unit = Unit(sub_strand)
            units[(strand, sub_strand)] = unit
            chapter.units.append(unit)

        topic = topics.get(cs_code)
        if topic is None:
            topic = Topic(cs_code, clean(row.get("cs_desc")))
            topics[cs_code] = topic
            unit.topics.append(topic)

        sessions = sessions_by_code.get(code, [])
        first = sessions[0] if sessions else {}
        # The book sets one lesson per indicator, so the lesson *is* one draft:
        # it seeds from the first scheduled session, and every later session whose
        # own main-activity text differs is carried underneath rather than lost.
        later = [s for s in sessions[1:]
                 if _steps(s.get("main")) and _steps(s.get("main")) != _steps(first.get("main"))]
        title = clean(first.get("session_title")) if sessions else ""
        if title.lower().startswith("session"):
            title = ""  # "Session 1 of 2 — …" is a schedule label, not a lesson title
        if not title:
            # Provisional title from the indicator, so authors start from the
            # right idea. The spec says lesson titles are authored, so it is
            # flagged for polish rather than presented as final.
            words = re.findall(r"[A-Za-z][A-Za-z'\u2019-]*", clean(row.get("ind_desc")))
            if words:
                title = " ".join(words[:6]) + " (provisional - polish this title)"
        topic.lessons.append(
            Lesson(
                number=code,
                title=title or "AUTHOR-TODO lesson title",
                objective=clean(row.get("ind_desc")),
                seeds={
                    "keywords": clean(row.get("keywords")),
                    "resources": clean(row.get("resources")),
                    "competencies": clean(row.get("competencies")),
                    "assessment": clean(row.get("assessment")),
                    "rpk": clean(first.get("rpk")),
                    "main": first.get("main") or [],
                    "starter": first.get("starter") or [],
                    "plenary": first.get("plenary") or [],
                    "performance": clean(first.get("perf_indicator")),
                    "session": _session_label(first),
                },
                sessions=sessions,
                later_main=later,
            )
        )

    return list(chapters.values())


def _steps(value) -> list[str]:
    """A session field as a list of steps (`main`/`starter`/`plenary` are lists,
    but the templates hold a bare string in some records)."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [clean(v) for v in value or [] if clean(v)]


def _session_label(session: dict) -> str:
    """`Term 1 · week 2 · Monday`, the way the schedule names a session."""
    parts = []
    for key, word in (("term", "Term"), ("week", "week")):
        if session.get(key) is not None:
            parts.append(f"{word} {session[key]}")
    if session.get("day"):
        parts.append(str(session["day"]))
    return " · ".join(parts)


def _sort_key(code: str):
    return [int(p) if p.isdigit() else 0 for p in re.findall(r"\d+", code)] or [0]


# ── docx helpers ─────────────────────────────────────────────────────────────

def shade(paragraph, fill: str) -> None:
    """Light background on a paragraph — used for feature boxes."""
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    p_pr.append(shd)


def box(document: Document, heading: str, lines: list[str], fill: str = "EEF2FF", todo: bool = False):
    title = document.add_paragraph()
    run = title.add_run(f"{heading}")
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = AMBER if todo else INDIGO
    shade(title, fill)

    for line in lines:
        if not clean(line):
            continue
        paragraph = document.add_paragraph()
        text = paragraph.add_run(f"• {clean(line)}" if len(lines) > 1 else clean(line))
        text.font.size = Pt(11)
        shade(paragraph, fill)
    document.add_paragraph()


def todo_box(document: Document, label: str, hint: str = ""):
    box(document, f"AUTHOR-TODO — {label}", [hint or "To be written by the author."], fill="FEF3C7", todo=True)


def heading(document: Document, text: str, level: int):
    paragraph = document.add_heading(text, level=level)
    for run in paragraph.runs:
        run.font.color.rgb = INDIGO
    return paragraph


def page_break(document: Document):
    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def coverage_table(document: Document, chapters: list[Chapter]):
    table = document.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header = table.rows[0].cells
    for index, label in enumerate(("Strand", "Sub-strand", "Content standard", "Indicator → Lesson")):
        header[index].text = label
        for run in header[index].paragraphs[0].runs:
            run.bold = True
    for chapter in chapters:
        for unit in chapter.units:
            for topic in unit.topics:
                for lesson in topic.lessons:
                    cells = table.add_row().cells
                    cells[0].text = chapter.name
                    cells[1].text = unit.name
                    cells[2].text = f"{topic.code} — {topic.goal}"
                    cells[3].text = f"{lesson.number} — {lesson.title}"
    document.add_paragraph()


def figure_register(document: Document, chapters: list[Chapter], flavour: dict):
    table = document.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    for index, label in enumerate(("Figure id", "Lesson", "Type / brief", "Artwork status")):
        table.rows[0].cells[index].text = label
    for chapter in chapters:
        for unit in chapter.units:
            for topic in unit.topics:
                for lesson in topic.lessons:
                    cells = table.add_row().cells
                    cells[0].text = f"FIG-{lesson.number}"
                    cells[1].text = lesson.number
                    cells[2].text = flavour["figure"]
                    cells[3].text = "TODO"
    document.add_paragraph()


def setup_styles(document: Document, subject_label: str, grade: str):
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    for section in document.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)


def title_page(document: Document, subject_label: str, grade: str, series: str):
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(series)
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = MUTED

    heading = document.add_paragraph()
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    big = heading.add_run(f"{subject_label} — {GRADE_LABELS.get(grade, grade)}")
    big.bold = True
    big.font.size = Pt(34)
    big.font.color.rgb = INDIGO

    subtitle = document.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note = subtitle.add_run("Skeleton generated from the NaCCA Standards-Based Curriculum\nfor authors to complete")
    note.font.size = Pt(12)
    note.font.color.rgb = MUTED

    document.add_paragraph()
    credit = document.add_paragraph()
    credit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    credit.add_run(BRAND).bold = True
    page_break(document)


# ── textbook ────────────────────────────────────────────────────────────────

def build_textbook(subject_label: str, grade: str, chapters: list[Chapter], flavour: dict, series: str, out: Path):
    document = Document()
    setup_styles(document, subject_label, grade)
    title_page(document, subject_label, grade, series)

    heading(document, "Copyright and acknowledgements", 1)
    document.add_paragraph(
        f"© {BRAND}. Curriculum content derived from the NaCCA Standards-Based Curriculum "
        f"for {GRADE_LABELS.get(grade, grade)}. Illustrated and written by the named contributors."
    )
    document.add_paragraph()
    heading(document, "How to use this book", 1)
    for line in (
        "Every lesson follows the same shape: what you will learn, key words, what you already know, "
        "the main work, practice, a summary and a quick check.",
        "Work together activities are for pairs or groups; Try it activities are for individual work.",
        "Boxes marked AUTHOR-TODO are production placeholders and must be removed before print.",
    ):
        document.add_paragraph(line, style="List Bullet")
    page_break(document)

    heading(document, "Curriculum coverage map", 1)
    document.add_paragraph(
        "Every indicator in this book, mapped to its content standard. Use it to show GES "
        "officers and head teachers that the book is complete."
    )
    coverage_table(document, chapters)
    page_break(document)

    heading(document, "Table of contents", 1)
    for chapter_index, chapter in enumerate(chapters, start=1):
        document.add_paragraph(f"Chapter {chapter_index}: {chapter.name}  ({chapter.lesson_count} lessons)").bold = True
        for unit_index, unit in enumerate(chapter.units, start=1):
            document.add_paragraph(f"    Unit {unit_index}: {unit.name}", style="List Bullet")
    page_break(document)

    for chapter_index, chapter in enumerate(chapters, start=1):
        heading(document, f"Chapter {chapter_index} · {chapter.name}", 1)
        document.add_paragraph(flavour["figure"]).italic = True
        document.add_paragraph("In this chapter you will:")
        for unit in chapter.units:
            for topic in unit.topics:
                if topic.goal:
                    document.add_paragraph(clean(topic.goal), style="List Bullet")
        page_break(document)

        for unit_index, unit in enumerate(chapter.units, start=1):
            heading(document, f"Unit {unit_index} · {unit.name}", 2)
            todo_box(document, "unit introduction", "One short paragraph that sets up the unit in local context.")

            for topic_index, topic in enumerate(unit.topics, start=1):
                if not topic.collapsed:
                    heading(document, f"Topic {topic_index} · {topic.goal}  [{topic.code}]", 3)

                for lesson_index, lesson in enumerate(topic.lessons, start=1):
                    heading(
                        document,
                        f"Lesson {chapter_index}.{unit_index}.{topic_index}.{lesson_index} · {lesson.title}  [{lesson.number}]",
                        4,
                    )
                    if topic.collapsed and topic.goal:
                        # Collapse rule: the topic goal prints inside the lesson header.
                        paragraph = document.add_paragraph()
                        run = paragraph.add_run(f"Topic goal: {clean(topic.goal)}")
                        run.italic = True
                        run.font.color.rgb = MUTED

                    box(document, "By the end of this lesson…", [lesson.objective], fill="EEF2FF")
                    if lesson.seeds.get("keywords"):
                        box(document, "Key words", [lesson.seeds["keywords"]], fill="F1F5F9")

                    if lesson.seeds.get("rpk"):
                        box(document, "Let's remember", [lesson.seeds["rpk"]], fill="F0FDF4")
                    else:
                        todo_box(document, "Let's remember", "Write 2–3 recall questions that link to the previous lesson.")

                    main = lesson.seeds.get("main") or []
                    if main:
                        heading(document, "Main content", 5)
                        where = lesson.seeds.get("session")
                        if where:
                            paragraph = document.add_paragraph()
                            run = paragraph.add_run(
                                f"Drafted from the first scheduled session ({where}).")
                            run.italic = True
                            run.font.color.rgb = MUTED
                        for step in main:
                            document.add_paragraph(clean(step))
                    else:
                        todo_box(
                            document,
                            "main content",
                            "Explain the idea in Ghanaian contexts (cedis, markets, local names) with a worked example.",
                        )

                    heading(document, flavour["extra_activity"][0], 5)
                    if lesson.seeds.get("starter"):
                        for step in lesson.seeds["starter"]:
                            document.add_paragraph(clean(step), style="List Bullet")
                    document.add_paragraph(flavour["extra_activity"][1]).italic = True

                    todo_box(document, "Work together", "Pair or group activity, with the competency it develops.")
                    if lesson.seeds.get("competencies"):
                        box(document, "Core competencies", [lesson.seeds["competencies"]], fill="FFF7ED")
                    if lesson.seeds.get("resources"):
                        box(document, "Materials", [lesson.seeds["resources"]], fill="F8FAFC")

                    todo_box(document, "What I have learnt", "Three summary bullets written for the learner's reading level.")
                    if lesson.seeds.get("assessment"):
                        box(document, "Quick check", [lesson.seeds["assessment"]], fill="FEF2F2")
                    else:
                        todo_box(document, "quick check", "2–3 self-assessment questions with answers at the back.")

                    if lesson.seeds.get("plenary"):
                        box(document, "Plenary", [clean(s) for s in lesson.seeds["plenary"]], fill="EFF6FF")

                    if lesson.later_main:
                        # each later session's own activity text, verbatim: the
                        # lesson above covers the first session, and dropping these
                        # would lose teaching content the database holds
                        heading(document, "Later sessions", 5)
                        box(
                            document,
                            f"The other {len(lesson.later_main)} scheduled session(s) for this indicator",
                            [f"{_session_label(s)} — " + "; ".join(_steps(s.get("main")))
                             for s in lesson.later_main],
                            fill="F8FAFC",
                        )
                    elif lesson.sessions and len(lesson.sessions) > 1:
                        document.add_paragraph(
                            f"{len(lesson.sessions)} scheduled sessions cover this indicator "
                            f"(term {lesson.sessions[0].get('term')}, week {lesson.sessions[0].get('week')}); "
                            "the later ones repeat the same activity, so this lesson covers them all."
                        ).italic = True

                    figure = document.add_paragraph()
                    figure.add_run(f"[FIGURE — {flavour['figure']}]").italic = True
                    document.add_paragraph()

            heading(document, f"Unit {unit_index} review", 3)
            todo_box(document, "unit review exercise", "6–10 questions covering this sub-strand, with marks.")

        heading(document, f"Chapter {chapter_index} revision", 2)
        todo_box(document, "strand revision exercise", "Mixed questions across the chapter, exam style.")
        todo_box(document, "project idea (Do and show)", "One project that uses the chapter's ideas at home or in school.")
        page_break(document)

    heading(document, "Glossary", 1)
    document.add_paragraph("Generated from the lesson keywords; the author adds child-level definitions.").italic = True
    glossary = document.add_table(rows=1, cols=2)
    glossary.style = "Light Grid Accent 1"
    glossary.rows[0].cells[0].text = "Word"
    glossary.rows[0].cells[1].text = "Definition (AUTHOR-TODO)"
    seen = set()
    for chapter in chapters:
        for unit in chapter.units:
            for topic in unit.topics:
                for lesson in topic.lessons:
                    for word in re.split(r"[,;]", lesson.seeds.get("keywords") or ""):
                        word = clean(word)
                        if word and word.lower() not in seen:
                            seen.add(word.lower())
                            glossary.add_row().cells[0].text = word
    document.add_paragraph()

    heading(document, "Figure register", 1)
    document.add_paragraph("For the illustrator: every figure this book needs, and where it goes.").italic = True
    figure_register(document, chapters, flavour)

    document.save(out)
    return document


# ── workbook ────────────────────────────────────────────────────────────────

def build_workbook(subject_label: str, grade: str, chapters: list[Chapter], flavour: dict, series: str, out: Path):
    document = Document()
    setup_styles(document, subject_label, grade)
    title_page(document, f"{subject_label} Workbook", grade, series)

    document.add_paragraph(
        "Companion to the textbook: identical lesson numbering and codes. Every lesson has "
        "A. Remember, B. Apply and C. Challenge."
    )
    page_break(document)

    for chapter_index, chapter in enumerate(chapters, start=1):
        heading(document, f"Chapter {chapter_index} · {chapter.name}", 1)

        for unit_index, unit in enumerate(chapter.units, start=1):
            heading(document, f"Unit {unit_index} · {unit.name}", 2)

            for topic_index, topic in enumerate(unit.topics, start=1):
                if not topic.collapsed:
                    heading(document, f"Topic {topic_index} · {topic.goal}", 3)

                for lesson_index, lesson in enumerate(topic.lessons, start=1):
                    heading(
                        document,
                        f"{chapter_index}.{unit_index}.{topic_index}.{lesson_index} · {lesson.title}  [{lesson.number}]",
                        4,
                    )
                    box(document, "Remember", ["3–5 items: fill-in, matching or multiple choice."], fill="EEF2FF")
                    todo_box(document, "A. Remember")
                    box(document, "Apply", ["3–5 practice items in context, with working space."], fill="F0FDF4")
                    todo_box(document, "B. Apply")
                    box(document, flavour["workbook_extra"], ["1–2 extension or reasoning items."], fill="FFF7ED")
                    todo_box(document, flavour["workbook_extra"])
                    document.add_paragraph("At home: ").add_run(
                        "connect the lesson to family or community life (optional)."
                    ).italic = True
                    page_break(document)

                heading(document, f"Topic {topic_index} check-up", 3)
                document.add_paragraph(f"Covers content standard {topic.code} — {clean(topic.goal)}").italic = True
                todo_box(document, "topic check-up", "SBA-style test with marks (the content standard is the unit of assessment).")
                page_break(document)

            heading(document, f"Pupil progress — {unit.name}", 3)
            progress = document.add_table(rows=1, cols=4)
            progress.style = "Light Grid Accent 1"
            for index, label in enumerate(("Lesson", "Date started", "Date completed", "Teacher's initials")):
                progress.rows[0].cells[index].text = label
            for topic in unit.topics:
                for lesson in topic.lessons:
                    progress.add_row().cells[0].text = f"{lesson.number} — {lesson.title}"
            document.add_paragraph()
            page_break(document)

    heading(document, "End-of-term assessment", 1)
    document.add_paragraph(
        "Aligned to the scheme of learning weeks for this term. Generate the paper from the portal's "
        "question bank once questions are tagged with indicator codes."
    ).italic = True
    todo_box(document, "end-of-term paper", "Sections A (objective), B (short answer) and C (essay), with a marking scheme.")

    heading(document, "Answer key", 1)
    document.add_paragraph(
        "Answers to every Quick check and check-up. Consider a separate Teacher's Answer Booklet "
        "if the workbook is sold to pupils."
    ).italic = True

    document.save(out)
    return document


# ── entry point ─────────────────────────────────────────────────────────────

def unique_path(path: Path) -> Path:
    """Never overwrite: books/…-skeleton.docx → …-skeleton-v2.docx → -v3 …"""
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    version = 2
    while True:
        candidate = path.with_name(f"{stem}-v{version}{suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("subject", help="subject id or name, e.g. mathematics")
    parser.add_argument("grade", help="grade id, e.g. B1")
    parser.add_argument("--series", default="Beacon Curriculum Series", help="series title on the cover")
    parser.add_argument("--textbook-only", action="store_true")
    parser.add_argument("--workbook-only", action="store_true")
    args = parser.parse_args(argv)

    subject = args.subject.strip().lower()
    grade = args.grade.strip().upper()

    print(f"Building book skeleton — {subject} {grade}")
    indicators = load_indicators(subject, grade)
    lessons = load_lessons(subject, grade)
    chapters = build_structure(indicators, lessons)

    lesson_total = sum(chapter.lesson_count for chapter in chapters)
    topic_total = sum(len(unit.topics) for chapter in chapters for unit in chapter.units)
    print(
        f"  structure:  {len(chapters)} chapters · "
        f"{sum(len(c.units) for c in chapters)} units · {topic_total} topics · {lesson_total} lessons"
    )

    flavour = FLAVOURS.get(subject, FLAVOURS["_default"])
    subject_label = subject.replace("-", " ").replace("_", " ").title()
    out_dir = BOOKS / grade
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.workbook_only:
        textbook = unique_path(out_dir / f"{subject}-textbook-skeleton.docx")
        build_textbook(subject_label, grade, chapters, flavour, args.series, textbook)
        print(f"  textbook:   {textbook.relative_to(ROOT)}")
    if not args.textbook_only:
        workbook = unique_path(out_dir / f"{subject}-workbook-skeleton.docx")
        build_workbook(subject_label, grade, chapters, flavour, args.series, workbook)
        print(f"  workbook:   {workbook.relative_to(ROOT)}")

    print("Done. Authors complete the AUTHOR-TODO boxes in Word; re-runs never overwrite.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
