#!/usr/bin/env python3
"""Generate Schemes of Learning from the enriched lesson-plan data.

This is the recurring product: every Ghanaian teacher must submit a Scheme of
Learning each term. We already know exactly what is taught in which week —
it's in the 13,140 enriched lesson records — so the scheme is derived, not
invented. That means the scheme and the lesson plans always agree.

Sources
-------
    {subject}[_b{grade}]_lessons_enriched.json    (73 files, 180 lessons each)

Outputs
-------
    dist/schemes/docx/Scheme_of_Learning_{Subject}_Basic{N}.docx
        One book per subject-grade (73 total), landscape, three term tables.

    dist/schemes/docx/terms/...   (with --per-term)
        One document per subject-grade-term (219 total) for individual submission.

    dist/schemes/json/{subject}_{grade}_scheme.json
        One file per subject-grade, holding all three terms. Every row is in
        the shape the app reads (`ForecastForm` writes it, `ForecastView` and
        `lib/schemeDocx.js` read it), so a term can be seeded straight into the
        `weekly_forecasts` collection: { week, kind?, label?, strandName,
        subStrandName, contentStandard, indicators, indicatorCodes, resources }.

    dist/schemes/QA_REPORT.md
        Coverage and anomaly report — read this before shipping.

Requires: python-docx  (pip install python-docx)

Usage
-----
    python3 scripts/generate_schemes.py                  # everything
    python3 scripts/generate_schemes.py --grade B4       # one grade
    python3 scripts/generate_schemes.py --subject math   # one subject (file key)
    python3 scripts/generate_schemes.py --subject mathematics  # ...or portal id
    python3 scripts/generate_schemes.py --per-term       # also emit 219 term docs
    python3 scripts/generate_schemes.py --with-descriptions

Notes
-----
A scheme row covers a whole week, so it lists **every indicator that week
covers** (5 teaching rows a week at one lesson a day), and one lesson may itself
carry several indicator codes. Reading only the first code of the first lesson
would drop the rest of the week silently.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    HAS_DOCX = True
except ImportError:  # data-only use (build_app_curriculum.py) still works
    HAS_DOCX = False

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "dist" / "schemes"
JSON_OUT = OUT / "json"
DOCX_OUT = OUT / "docx"

# Brand — matches scripts/build/build_*_word_document.py.
# Only meaningful when python-docx is present (document rendering).
if HAS_DOCX:
    NAVY = RGBColor(0, 32, 96)
    DARK_GRAY = RGBColor(64, 64, 64)
    BLACK = RGBColor(0, 0, 0)
else:
    NAVY = DARK_GRAY = BLACK = None
HEAD_FILL = "E2E8F0"
SPECIAL_FILL = "F8FAFC"

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# NaCCA bands. NOTE: the existing lesson-plan books mislabel B4-B6 as
# "Lower Primary"; that is a bug in those files, not reproduced here.
BANDS = {
    **{f"B{i}": "Lower Primary" for i in (1, 2, 3)},
    **{f"B{i}": "Upper Primary" for i in (4, 5, 6)},
    "B7": "JHS 1", "B8": "JHS 2", "B9": "JHS 3",
}

# enriched-file subject key -> (app subject id, display name)
SUBJECTS = {
    "math":                  ("mathematics",            "Mathematics"),
    "science":               ("science",                "Integrated Science"),
    "english":               ("english-language",       "English Language"),
    "ghanaian":              ("ghanaian-language",      "Ghanaian Language"),
    "ghanaian_language":     ("ghanaian-language",      "Ghanaian Language"),
    "history":               ("history",                "History"),
    "rme":                   ("rme",                    "Religious and Moral Education"),
    "creative_arts":         ("creative-arts",          "Creative Arts"),
    "creative_arts_design":  ("creative-arts-design",   "Creative Arts and Design"),
    "owop":                  ("owop",                   "Our World Our People"),
    "computing":             ("computing",              "Computing"),
    "career_technology":     ("career-technology",      "Career Technology"),
    "french":                ("french",                 "French"),
    "social_studies":        ("social-studies",         "Social Studies"),
}

FILE_RE = re.compile(r"^(?P<subj>.+?)(?:_b(?P<grade>\d))?_lessons_enriched\.json$")

# B1 database files predate the `<subject>_<GRADE>_` naming convention.
B1_DB_PREFIX = {
    "math": "math", "science": "science", "english": "english",
    "ghanaian_language": "ghanaian_language", "history": "history",
    "rme": "rme", "creative_arts": "creative_arts", "owop": "owop",
}


# Some curriculum DB files live only in the reference copy (e.g.
# english-language_B5), so it is searched as a fallback. The primary copy
# is searched first, which preserves the historical ordering (repo root
# before app/data/). See scripts/_paths.py — do not re-define this here.
from _paths import DB_SEARCH, LESSONS, REFERENCE  # noqa: E402,F401


def resolve_db(subj, grade):
    """Locate the curriculum database backing a subject-grade, if present."""
    if grade == "B1":
        prefix = B1_DB_PREFIX.get(subj)
        name = f"{prefix}_curriculum_db_clean.json" if prefix else None
    else:
        name = f"{SUBJECTS[subj][0]}_{grade}_curriculum_db_clean.json"
    if not name:
        return None
    for base in DB_SEARCH:
        candidate = base / name
        if candidate.exists():
            return candidate
    return None

# Column widths (inches) for landscape Letter with 1" margins -> 9" usable.
# Proportions mirror src/lib/schemeDocx.js (7/17/21/14/14/27).
COL_WIDTHS = [0.55, 1.60, 1.95, 1.35, 1.30, 2.25]
COL_HEADS = ["WEEKS", "STRAND", "SUB-STRANDS", "CONTENT STANDARD", "INDICATORS", "RESOURCES"]


# ---------------------------------------------------------------- discovery

def resolve_subject(requested):
    """Map a user-supplied --subject to the lesson-file keys it names.

    Accepts the lesson-file key (`math`) and the subject id the portal and the
    curriculum bundle use (`mathematics`), because asking for a subject by the
    name the app shows should not answer "no matching files". Returns [] when
    nothing matches, so the caller can print the valid names.
    """
    wanted = str(requested).strip().lower().replace("-", "_")
    if not wanted:
        return []
    return [k for k, (sid, _) in SUBJECTS.items()
            if k == wanted or sid.replace("-", "_") == wanted]


def discover():
    """Map enriched lesson files -> (subject_key, grade, path)."""
    found, unmapped = [], []
    for path in sorted(LESSONS.glob("*_lessons_enriched.json")):
        m = FILE_RE.match(path.name)
        if not m:
            unmapped.append(path.name)
            continue
        subj, grade = m.group("subj"), f"B{m.group('grade') or 1}"
        if subj not in SUBJECTS:
            unmapped.append(path.name)
            continue
        found.append((subj, grade, path))
    if unmapped:
        print(f"  ! skipping {len(unmapped)} unrecognised file(s): {unmapped}")
    return found


# ------------------------------------------------------------ row building

def uniq(seq):
    """De-duplicate, preserving first-seen order."""
    seen, out = set(), []
    for s in seq:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def special_rows(term, teaching_weeks):
    """REVISION / EXAMINATION / VACATION block.

    Term 1 ends with REVISION then a combined EXAMINATION week; terms 2 and 3
    add VACATION. `ForecastForm.jsx` has no equivalent of these rows — it seeds
    12 teaching weeks from the schedule — so they are carried in the JSON as
    `kind: "special"` with a `label` for the caller to render.
    """
    w = teaching_weeks
    if term == 1:
        return [
            {"week": str(w + 1), "kind": "special", "label": "REVISION"},
            {"week": f"{w + 2} & {w + 3}", "kind": "special", "label": "EXAMINATION"},
        ]
    return [
        {"week": str(w + 1), "kind": "special", "label": "REVISION"},
        {"week": str(w + 2), "kind": "special", "label": "EXAMINATION"},
        {"week": str(w + 3), "kind": "special", "label": "VACATION"},
    ]


# A lesson covers a *set* of indicators, not a single one: the app stores
# `indicatorCodes[]` on a plan (LessonPlanForm) and a scheme row lists every
# indicator the week covers. Lesson records carry that as `ind_code` today;
# accept a list (`ind_codes` / `indicatorCodes`) and a separated string too, so
# a lesson taught against several indicators is not silently reduced to its
# first. Splitting is on ; , and newline only — never on whitespace, because
# indicator codes are never space-separated.
INDICATOR_SPLIT_RE = re.compile(r"[;,\n]+")


def lesson_indicator_codes(lesson):
    """Every indicator code one lesson covers, in order, de-duplicated."""
    raw = (lesson.get("ind_codes") or lesson.get("indicatorCodes")
           or lesson.get("ind_code") or lesson.get("indicatorCode") or "")
    if isinstance(raw, (list, tuple, set)):
        parts = [str(p) for p in raw]
    else:
        parts = INDICATOR_SPLIT_RE.split(str(raw))
    return uniq(p.strip() for p in parts if str(p).strip())


def row_from_week(week, lessons, with_desc):
    """Build one scheme row from the lessons scheduled in that week."""
    lessons = sorted(lessons, key=lambda l: DAY_ORDER.index(l["day"])
                     if l.get("day") in DAY_ORDER else 99)
    if not lessons:
        return {"week": str(week), "kind": "lesson", "strand": "", "subStrand": "",
                "contentStandards": "", "indicators": "", "resources": "",
                "indicatorIds": [], "_empty": True}

    strands = uniq(l.get("strand_name", "") for l in lessons)
    substrands = uniq(l.get("sub_strand", "") for l in lessons)

    # content standards: code (+ optional description), de-duplicated by code
    cs, cs_seen = [], set()
    for l in lessons:
        code = l.get("cs_code", "")
        if not code or code in cs_seen:
            continue
        cs_seen.add(code)
        desc = (l.get("cs_desc") or "").strip()
        cs.append(f"{code} — {desc}" if with_desc and desc else code)

    inds, ind_ids = [], []
    for l in lessons:
        codes = lesson_indicator_codes(l)
        # `ind_desc` describes the lesson's indicator. When a lesson carries
        # several codes that text cannot be attributed to any one of them, so
        # print the codes alone rather than repeating one description under
        # every code.
        desc = (l.get("ind_desc") or "").strip() if len(codes) == 1 else ""
        for code in codes:
            if code in ind_ids:
                continue
            ind_ids.append(code)
            inds.append(f"{code} — {desc}" if with_desc and desc else code)

    resources = uniq((l.get("resources") or "").strip() for l in lessons)

    return {
        "week": str(week),
        "kind": "lesson",
        "strand": "\n".join(strands),
        "subStrand": "\n".join(substrands),
        "contentStandards": "\n".join(cs),
        "indicators": "\n".join(inds),
        "resources": "\n".join(resources),
        "indicatorIds": ind_ids,
        "_revision": sum(1 for l in lessons if l.get("is_revision")),
        "_lessons": len(lessons),
    }


def to_app_row(row):
    """One internal scheme row -> the `weekly_forecasts` row shape.

    Field-by-field this is what `ForecastForm.jsx` writes and what
    `ForecastView.jsx` / `src/lib/schemeDocx.js` read back. `kind` and `label`
    are carried through for the REVISION / EXAMINATION / VACATION rows, which
    the app has no equivalent of and renders as blank weeks.
    """
    week = str(row.get("week", "")).strip()
    return {
        "week": int(week) if week.isdigit() else week,
        "kind": row.get("kind", "lesson"),
        **({"label": row["label"]} if row.get("label") else {}),
        "strandName": row.get("strand", ""),
        "subStrandName": row.get("subStrand", ""),
        "contentStandard": row.get("contentStandards", ""),
        "indicators": row.get("indicators", ""),
        "indicatorCodes": list(row.get("indicatorIds", [])),
        "resources": row.get("resources", ""),
    }


def build_scheme(lessons, teaching_weeks, with_desc=False):
    """Return {term: [rows]} for one subject-grade."""
    by_week = defaultdict(lambda: defaultdict(list))
    for l in lessons:
        by_week[l["term"]][l["week"]].append(l)

    scheme = {}
    for term in sorted(by_week):
        weeks = by_week[term]
        span = teaching_weeks or max(weeks)
        rows = [row_from_week(w, weeks.get(w, []), with_desc) for w in range(1, span + 1)]
        rows += special_rows(term, span)
        scheme[term] = rows
    return scheme


# --------------------------------------------------------------- docx bits

def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def cell_text(cell, text, size=8, bold=False, align=None, italic=False,
              color=BLACK, space_after=0):
    """Fill a cell, one paragraph per line. `text` may contain newlines."""
    cell.paragraphs[0]._element.getparent().remove(cell.paragraphs[0]._element)
    for i, line in enumerate(str(text).split("\n")):
        p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        if align is not None:
            p.alignment = align
        run = p.add_run(line)
        run.font.name = "Calibri"
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.color.rgb = color
        if i == 0 and not line:
            p.paragraph_format.space_after = Pt(0)
    if not str(text).strip():
        p = cell.add_paragraph()
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run("")
        r.font.size = Pt(size)


def set_widths(table, widths):
    """Force fixed column widths.

    Setting cell.width alone is not enough — Word lays the table out from
    <w:tblGrid>, so the grid columns and the fixed layout flag must be set too.
    """
    table.autofit = False
    for row in table.rows:
        for i, w in enumerate(widths):
            if i < len(row.cells):
                row.cells[i].width = Inches(w)

    tbl = table._tbl
    tblPr = tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")

    tblGrid = tbl.find(qn("w:tblGrid"))
    if tblGrid is not None:
        for col, w in zip(tblGrid.findall(qn("w:gridCol")), widths):
            col.set(qn("w:w"), str(int(w * 1440)))


def add_rule(paragraph, color="D3D3D3", size="12"):
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), size)
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), color)
    pBdr.append(bottom)
    paragraph._p.get_or_add_pPr().append(pBdr)


def styled(paragraph, text, size=10, bold=False, italic=False, color=BLACK):
    r = paragraph.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    return r


def new_landscape_doc():
    doc = Document()
    s = doc.sections[0]
    s.orientation = WD_ORIENT.LANDSCAPE
    s.page_width, s.page_height = Inches(11), Inches(8.5)
    s.left_margin = s.right_margin = Inches(1)
    s.top_margin = s.bottom_margin = Inches(1)
    return doc


def term_table(doc, rows):
    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0]
    for i, head in enumerate(COL_HEADS):
        cell_text(hdr.cells[i], head, size=8, bold=True)
        shade(hdr.cells[i], HEAD_FILL)

    for row in rows:
        cells = table.add_row().cells
        if row["kind"] == "special":
            cell_text(cells[0], row["week"], size=8, bold=True)
            cell_text(cells[1], row["label"], size=8, bold=True,
                      align=WD_ALIGN_PARAGRAPH.CENTER)
            cells[1].merge(cells[5])
            shade(cells[1], SPECIAL_FILL)
        else:
            cell_text(cells[0], row["week"], size=8, bold=True)
            cell_text(cells[1], row["strand"], size=8)
            cell_text(cells[2], row["subStrand"], size=8)
            cell_text(cells[3], row["contentStandards"], size=8)
            cell_text(cells[4], row["indicators"], size=8)
            cell_text(cells[5], row["resources"], size=8)

    set_widths(table, COL_WIDTHS)
    return table


def field(label, value, width=22):
    """'School: Achimota' when the caller supplies one, 'School: ______' when not.

    Documents generated for a school are pre-printed with its details; every
    field falls back to a handwritten blank so plain CLI output is unchanged.
    """
    return f"{label}: {value}" if value else f"{label}: {'_' * width}"


def cover(doc, subject_name, grade, school=None, teacher=None,
          class_name=None, term=None, year=None, hod=None):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    styled(p, "\nSCHEME OF LEARNING", size=26, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    styled(p, f"{subject_name}\nBasic {grade[1:]}  ·  {BANDS.get(grade, '')}",
           size=14, bold=True, color=DARK_GRAY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    styled(p, "Aligned with the NaCCA Standards-Based Curriculum (2019)\n"
              "Derived from the Beacon full-year lesson plan library —\n"
              "every row matches the lessons taught that week.",
           size=10, color=DARK_GRAY)
    add_rule(p, "002060", "12")

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    styled(p, f"{field('School', school, 38)}      "
              f"{field('Term', term, 6)}      {field('Year', year, 10)}",
           size=10, bold=True)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    styled(p, f"{field('Class', class_name, 12)}      "
              f"{field('Teacher', teacher)}      {field('HoD', hod, 20)}",
           size=10, bold=True)
    p = doc.add_paragraph()
    styled(p, "Signature: ____________________      Date: ____________________",
           size=10, bold=True)


def build_docx(subject_name, grade, scheme, path, per_term=False, **branding):
    doc = new_landscape_doc()
    cover(doc, subject_name, grade, **branding)

    for term in sorted(scheme, key=lambda t: int(t)):
        doc.add_page_break()
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        styled(p, f"TERM {term}  ·  {subject_name.upper()}  ·  BASIC {grade[1:]}",
               size=13, bold=True, color=NAVY)
        add_rule(p, "002060", "12")
        term_table(doc, scheme[term])

    doc.save(path)
    return path


def build_term_docx(subject_name, grade, term, rows, path,
                    school=None, teacher=None, class_name=None, year=None,
                    hod=None):
    doc = new_landscape_doc()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    styled(p, "SCHEME OF LEARNING", size=18, bold=True, color=NAVY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    styled(p, f"{subject_name}  ·  Basic {grade[1:]}  ·  Term {term}",
           size=12, bold=True, color=DARK_GRAY)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    styled(p, f"{field('School', school, 30)}      {field('Class', class_name, 10)}      "
              f"{field('Year', year, 10)}      {field('Teacher', teacher, 22)}",
           size=9, bold=True)
    term_table(doc, rows)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    styled(p, f"{field('Prepared by', teacher, 20)}      "
              f"{field('HoD', hod, 20)}      Date: ____________", size=9, bold=True)
    doc.save(path)
    return path


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grade", help="e.g. B4")
    ap.add_argument("--subject", help="enriched-file subject key, e.g. math")
    ap.add_argument("--weeks", type=int, default=None,
                    help="teaching weeks per term (default: infer from data)")
    ap.add_argument("--per-term", action="store_true",
                    help="also emit one document per term (219 files)")
    ap.add_argument("--with-descriptions", action="store_true",
                    help="include content-standard / indicator text, not just codes")
    ap.add_argument("--out", default=None, help="output directory")
    # Branding — pre-print the cover for a specific school. Every field is
    # optional and falls back to a handwritten blank.
    ap.add_argument("--school", help="pre-print the school name on the cover")
    ap.add_argument("--teacher", help="pre-print the teacher's name")
    ap.add_argument("--class-name", dest="class_name",
                    help="pre-print the class, e.g. 'Basic 4'")
    ap.add_argument("--term", help="pre-print the term")
    ap.add_argument("--year", help="pre-print the academic year")
    ap.add_argument("--hod", help="pre-print the Head of Department")
    args = ap.parse_args()

    branding = {k: v for k, v in dict(
        school=args.school, teacher=args.teacher, class_name=args.class_name,
        term=args.term, year=args.year, hod=args.hod).items() if v}

    global OUT, JSON_OUT, DOCX_OUT
    if args.out:
        OUT = Path(args.out); JSON_OUT = OUT / "json"; DOCX_OUT = OUT / "docx"
    for d in (JSON_OUT, DOCX_OUT):
        d.mkdir(parents=True, exist_ok=True)
    if args.per_term:
        (DOCX_OUT / "terms").mkdir(parents=True, exist_ok=True)

    if not HAS_DOCX:
        sys.exit("python-docx is required to build .docx files:  pip install python-docx")

    entries = discover()
    if args.grade:
        entries = [e for e in entries if e[1] == args.grade]
    if args.subject:
        matching = resolve_subject(args.subject)
        if not matching:
            known = ", ".join(sorted(SUBJECTS))
            sys.exit(f"Unknown subject '{args.subject}'.\n"
                     f"  lesson-file keys: {known}\n"
                     f"  portal subject ids: "
                     + ", ".join(sorted({v[0] for v in SUBJECTS.values()})))
        entries = [e for e in entries if e[0] in matching]
    if not entries:
        sys.exit("No matching lesson files.")

    print(f"Building schemes for {len(entries)} subject-grade file(s)...\n")

    qa = []
    for subj, grade, path in entries:
        subject_id, subject_name = SUBJECTS[subj]
        lessons = json.loads(path.read_text(encoding="utf-8"))
        scheme = build_scheme(lessons, args.weeks, args.with_descriptions)

        # ---- DOCX (one book per subject-grade)
        safe = subject_name.replace(" ", "_").replace("&", "and")
        docx_path = DOCX_OUT / f"Scheme_of_Learning_{safe}_Basic{grade[1:]}.docx"
        build_docx(subject_name, grade, scheme, docx_path, **branding)

        # ---- optional per-term documents
        if args.per_term:
            for term, rows in scheme.items():
                build_term_docx(
                    subject_name, grade, term, rows,
                    DOCX_OUT / "terms" /
                    f"Scheme_of_Learning_{safe}_Basic{grade[1:]}_Term{term}.docx",
                    school=args.school, teacher=args.teacher,
                    class_name=args.class_name, year=args.year, hod=args.hod,
                )

        # ---- JSON for the app
        # Strip keys prefixed with "_" (internal QA counters) and emit every row
        # under the names the app reads, so the file can be seeded straight into
        # `weekly_forecasts`. This is not cosmetic: the app reads
        # strandName / subStrandName / contentStandard / indicatorCodes
        # (ForecastForm writes them; ForecastView and lib/schemeDocx.js read
        # them), so the internal names would render the strand, sub-strand and
        # content-standard columns blank.
        clean = {
            str(t): [to_app_row(r) for r in rows]
            for t, rows in sorted(scheme.items())
        }
        payload = {
            "subjectId": subject_id,
            "subject": subject_name,
            "grade": grade,
            "source": path.name,
            "teachingWeeksPerTerm": args.weeks or max(
                max(int(r["week"]) for r in rows if r["kind"] == "lesson")
                for rows in scheme.values()),
            "terms": clean,
        }
        (JSON_OUT / f"{subject_id}_{grade}_scheme.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # ---- cross-check against the curriculum database
        scheme_codes = {i for rows in scheme.values()
                        for r in rows for i in r.get("indicatorIds", [])}
        db_path = resolve_db(subj, grade)
        if db_path:
            db_codes = set(json.loads(db_path.read_text(encoding="utf-8")).keys())
            covered = len(scheme_codes & db_codes)
            db_n, pct = len(db_codes), round(100 * covered / len(db_codes), 1)
            uncovered = sorted(db_codes - scheme_codes)
            unexpected = sorted(scheme_codes - db_codes)
        else:
            db_n = pct = None
            uncovered = unexpected = []

        # ---- QA
        empty = [(t, r["week"]) for t, rows in scheme.items()
                 for r in rows if r.get("_empty")]
        lesson_rows = [r for rows in scheme.values() for r in rows if r["kind"] == "lesson"]
        scheduled = sum(r.get("_lessons", 0) for r in lesson_rows)
        total_ind = sum(len(r.get("indicatorIds", [])) for r in lesson_rows)
        qa.append({
            "grade": grade, "subject": subject_name, "file": path.name,
            "lessons_in": len(lessons), "lessons_scheduled": scheduled,
            "rows": len(lesson_rows), "empty_weeks": len(empty),
            "indicators_covered": total_ind,
            "unique_indicators": len(scheme_codes),
            "db_indicators": db_n,
            "coverage_pct": pct,
            "uncovered": uncovered,
            "unexpected": unexpected,
            "docx_kb": round(docx_path.stat().st_size / 1024),
            "status": "OK" if not empty and scheduled == len(lessons) else "CHECK",
        })
        cov = f"{pct}%" if pct is not None else "n/a"
        print(f"  {grade} {subject_name:32} "
              f"{len(lesson_rows)} rows · {len(scheme_codes)} ind · "
              f"coverage {cov:>6} · {qa[-1]['docx_kb']} KB  [{qa[-1]['status']}]")

    write_qa(qa, args)
    print(f"\nDone.\n  DOCX : {DOCX_OUT}\n  JSON : {JSON_OUT}\n  QA   : {OUT / 'QA_REPORT.md'}")


def write_qa(qa, args):
    bad = [r for r in qa if r["status"] != "OK"]
    lines = [
        "# Schemes of Learning — QA Report",
        "",
        f"Generated {len(qa)} subject-grade schemes "
        f"({sum(r['rows'] for r in qa):,} week rows across 3 terms).",
        f"Options: weeks={args.weeks or 'inferred'}, "
        f"with_descriptions={args.with_descriptions}, per_term={args.per_term}",
        "",
    ]
    if bad:
        lines += [f"> ⚠️ **{len(bad)} scheme(s) need attention** — "
                  "empty weeks or unscheduled lessons.\n"]
    else:
        lines += ["> ✅ Every lesson in the library is scheduled into a scheme row, "
                  "and no week is empty.\n"]

    scored = [r for r in qa if r["coverage_pct"] is not None]
    if scored:
        avg = sum(r["coverage_pct"] for r in scored) / len(scored)
        full = sum(1 for r in scored if r["coverage_pct"] >= 100.0)
        lines += [
            f"**Curriculum coverage:** {full}/{len(scored)} subject-grades reach 100% "
            f"of their curriculum database · mean {avg:.1f}%",
            "",
        ]

    lines += [
        "| Grade | Subject | Lessons in | Scheduled | Week rows | Unique indicators | DB indicators | Coverage | Empty weeks | DOCX | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(qa, key=lambda x: (int(x["grade"][1:]), x["subject"])):
        cov = f"{r['coverage_pct']}%" if r["coverage_pct"] is not None else "n/a"
        dbn = r["db_indicators"] if r["db_indicators"] is not None else "—"
        lines.append(
            f"| {r['grade']} | {r['subject']} | {r['lessons_in']} | "
            f"{r['lessons_scheduled']} | {r['rows']} | {r['unique_indicators']} | "
            f"{dbn} | {cov} | {r['empty_weeks']} | {r['docx_kb']} KB | "
            f"{r['status']} |"
        )

    gaps = [r for r in qa if r["uncovered"] or r["unexpected"]]
    if gaps:
        lines += ["", "## Coverage gaps", ""]
        lines += ["These schemes do not reach every indicator in the curriculum "
                  "database. Decide whether the indicator is genuinely out of scope "
                  "or the lesson schedule missed it.", ""]
        for r in sorted(gaps, key=lambda x: (int(x["grade"][1:]), x["subject"])):
            bits = []
            if r["uncovered"]:
                bits.append(f"not scheduled ({len(r['uncovered'])}): "
                            + ", ".join(r["uncovered"][:12])
                            + ("…" if len(r["uncovered"]) > 12 else ""))
            if r["unexpected"]:
                bits.append(f"in scheme but not in DB ({len(r['unexpected'])}): "
                            + ", ".join(r["unexpected"][:12])
                            + ("…" if len(r["unexpected"]) > 12 else ""))
            lines.append(f"- **{r['grade']} {r['subject']}** — " + "; ".join(bits))

    lines += [
        "",
        "## How to read this report",
        "",
        "- **Scheduled** must equal **Lessons in** — otherwise some lessons are not "
        "represented in any scheme row (status becomes `CHECK`).",
        "- **Unique indicators** is lower than 180 for some subjects because an "
        "indicator taught over two sessions in the same week appears once in the "
        "scheme row, not twice. That is correct — a week lists what is covered, not "
        "how many periods it takes.",
        "- **Coverage** compares the distinct indicators in the scheme against that "
        "subject-grade's `*_curriculum_db_clean.json`. 100% means every indicator in "
        "the curriculum is scheduled somewhere in the year.",
        "- Weeks spanning several strands are expected: the lesson library rotates "
        "strands by day of week (e.g. B4 Mathematics runs Number → Algebra → Geometry "
        "→ Data across Mon–Fri), so one week legitimately covers several strands.",
        "- Each term ends with the REVISION / EXAMINATION (/ VACATION) block, "
        "emitted as `kind: \"special\"` rows carrying a `label`.",
        "- Teaching weeks per term are **inferred from the lesson data (12)**, not the "
        "app's default of 12 rows (ForecastForm), so that the scheme and the "
        "lesson plans agree. "
        "Override with `--weeks`.",
    ]
    (OUT / "QA_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
