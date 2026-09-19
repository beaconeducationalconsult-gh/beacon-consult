#!/usr/bin/env python3
"""Name the sub-strands the databases still call `Sub-strand B4.1.1` (P1-12).

3,679 of the 4,040 served indicators carry a *code* where the curriculum prints a name:

    "sub_strand": "Sub-strand B4.1.1"    ->  the browser, the scheme, the lesson plan

The prints set that name once per block, as a heading above the table:

    SUB - STRAND 2: INTRODUCTION TO ELECTRONIC SPREADSHEET
    Sub - Strand 13: Persuasive/Argumentative Writing
    SUB-STRAND 3: B7.1.3 THE CLAN SYSTEM

`scripts/fill_label_form_text.py` (P1-11) already reads these headings, but only for the
302 records whose descriptions are labels too, and `build_app_curriculum.split_num_name()`
passes a code-shaped `sub_strand` straight through into `subStrandName`, so the code is
what the app shows.  This script widens that read to every code-shaped sub-strand in the
served databases — and *only* to the code-shaped ones: a record that already carries a
name is Audit B's business, not this pass's.

What the wider read needs, each measured against the prints.  (P1-11's reader is left
as it was, because it was verified against its own records; this script reads the same
block headings, with the forms the other prints use.)

* the two prints the registry did not carry — kindergarten and social studies — are now
  in `fix_ind_desc_exemplars.PRINTS`;
* the heading forms: `SUB - STRAND` / `SUB STRAND` (kindergarten, ghanaian language
  B4-B6, rme, science B1-B6), `SUB-STRAND`, a heading whose number the print left out
  (`SUB - STRAND : Parler de son école`), a heading whose *name* comes first
  (`THE PARTS OF THE HUMAN BODY AND THEIR FUNCTIONS SUB - STRAND 2`), and a name that
  carries its own code (`SUB-STRAND 3: B7.1.3 THE CLAN SYSTEM`);
* the printed code is not the recorded one: the CCP prints write the grade inside it
  (`B7/JHS1 .1.1.1.1`), the creative-arts print writes it without the dot
  (`B1 1.1.1.2`), and the page's own column rules do not always bracket the row, so
  codes are folded and the band is read with a small tolerance;
* a heading is a *block* property, not a row's: a record is named from its own row when
  the print carries that row, from its own content standard when it carries that, from
  the print's own rows of the same grade + strand + sub-strand number, and — one step
  weaker, reported as such — from the same block in another grade of the same print
  (the CCP prints repeat a block across B7-B9).

Nothing is written on a hunch.  A name is accepted only when

* it comes from the print's own heading, de-kerned against the page's vocabulary (the
  prints set `GENE RATION OF COMPUTERS`), and is a name — not a code, a label, a
  table's column heading, or a table-of-contents line with dot leaders;
* the heading's number matches the record's own components, *unless* the record's own
  row is the anchor — the print itself then says which block that row sits in;
* the heading's page carries the phrase again, folded, so a name assembled out of two
  tables cannot pass;
* the block is named one way: readings that disagree by more than a shortened spelling
  refuse the record rather than pick between them.

The served schedules carry the code too — 11,700 of their 13,140 rows — because a lesson
whose indicator the database has no row for falls back to `data/lessons/*.json`, where
the same `sub_strand` placeholder sits.  Those files are filled from the same reads, so
the scheme, the lesson plan and the exports lose the code as well.

Report only by default; `--apply` writes the databases (a sub-strand is written in the
databases' own form, `<number>. <NAME>`, which `split_num_name()` turns back into
`subStrandName`) and the lesson files.  Every write and every refusal goes to
`data/audit/sub_strand_names.json`.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fix_reference_text as F                                     # noqa: E402
import fix_ind_desc_exemplars as X                                 # noqa: E402
import fill_label_form_text as L                                   # noqa: E402
from _paths import APP_CURRICULUM, AUDIT, CURRICULUM, LESSONS        # noqa: E402

# --------------------------------------------------------------------------- #
# the heading forms
# --------------------------------------------------------------------------- #

DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015-"
# `SUB - STRAND 2: NAME` / `SUB STRAND 3 : NAME` / `SUB-STRAND 3: NAME` / `SUB - STRAND 1 NAME`
SUB_HEAD = re.compile(
    rf"^SUB\s*[{DASHES}]?\s*STRAND\b\s*:?\s*(\d+(?:\s*[.]\s*\d+)*)?\s*[.:]?\s*(.*)$", re.I)
# `THE PARTS OF THE HUMAN BODY AND THEIR FUNCTIONS SUB - STRAND 2` — the name comes first
SUB_TAIL = re.compile(
    rf"^(?P<name>.+?)\s+SUB\s*[{DASHES}]?\s*STRAND\s*:?\s*(?P<num>\d+(?:\s*[.]\s*\d+)*)\s*[.:]?\s*$",
    re.I)
# `STRAND 1: NAME` / `STRAND (OR THEMATIC UNIT) 2:` (the kindergarten print's own form)
STRAND_HEAD = re.compile(
    r"^STRAND\b(?:\s*\(\s*OR\s+THEMATIC\s+UNIT\s*\))?\s*:?\s*"
    r"(\d+(?:\s*[.]\s*\d+)*)?\s*[.:]?\s*(.*)$", re.I)

# a line that is a heading of some other kind, or a table's furniture, never a name
NOT_A_NAME = re.compile(
    r"strand|content standard|indicators?\s+and\s+exemplars|core\s+competen|references"
    r"|^term\b|^table\b|\.\s*\.\s*\.", re.I)
# the print's codes: `B6.5.3.1.1`, `B 7 .1.1.1.1`, `B7/JHS1 .1.1.1.1`, `B1 1.1.1.2`
CODE_TOKEN = re.compile(
    r"[BK]\s*\d(?:\s*/?\s*(?:JHS|SHS|BASIC|PRIMARY)?\s*\d*)?[\d\s.]*\d", re.I)
LEAD_CODE = re.compile(r"^\s*[BK]\s*\d[\d\s.]*\d\s*", re.I)
# a heading that prints its own block in front of the name: `(K2.1.1): I AM A …`
LEAD_BRACKET = re.compile(r"^\s*\(\s*[BK]?\s*\d[\d.\s]*\)\s*:?\s*")

CODE_SHAPED = re.compile(r"^(Sub-?strand)\s+[BK]?\s*\d", re.I)

# the indicator column is the page's own rule pair widened by this much: career
# technology's code starts 7pt left of the rule its page draws
BAND_TOLERANCE = 14.0


def fold_code(text: str) -> str:
    """A printed code with the print's own dressing taken off, folded to `B7.1.1.1.1`.

    The CCP prints put the class inside the grade (`B7/JHS1 .1.1.1.1`), the creative-arts
    print drops the dot after the grade (`B1 1.1.1.2`), and every print may space the
    digits out of the line's flow.
    """
    text = re.sub(r"\s+", "", text or "")
    text = re.sub(r"/?(?:JHS|SHS|BASIC|PRIMARY)\d*", "", text, flags=re.I)
    return re.sub(r"^([BK]\d)(\d)", r"\1.\2", text)


def comps(text: str) -> list[str]:
    """A code as its components: `B7.1.1.1.1` -> ['B7', '1', '1', '1', '1']."""
    return [p for p in re.split(r"[.\s]+", (text or "").strip()) if p]


def tidy_name(name: str) -> str:
    """The heading's own words, without the code some prints put in front of them."""
    name = LEAD_BRACKET.sub("", name or "")
    name = LEAD_CODE.sub("", name)
    return re.sub(r"\s+", " ", name).strip(" .;:,\u2013\u2014-")


def is_name(text: str) -> bool:
    """Whether the heading says a name at all (never a code, a label, or a caption)."""
    if not text or NOT_A_NAME.search(text):
        return False
    if re.fullmatch(r"[BK]?\s*\d[\d.\s]*", text):       # a code, not a name
        return False
    return len(re.sub(r"[^A-Za-z]", "", text)) >= 3


# --------------------------------------------------------------------------- #
# the print's block headings, top to bottom
# --------------------------------------------------------------------------- #

_HEADS: dict = {}
_TIMELINE: dict = {}
# --------------------------------------------------------------------------- #
# the prints split a word now and then, and the repairs are curated
# --------------------------------------------------------------------------- #

# Each pair is a reading the print's own typesetting broke — kerning puts the pieces in
# separate text chunks — and the word the print spells elsewhere.  A pair is added only
# after looking at the print: `INTHE` is *not* here, because the computing CCP print
# really does set `TECHNOLOGY INTHE COMMUNITY`.  Every repaired word is checked against
# that print's own vocabulary before the repair is applied, and every application is
# recorded in the audit artifact.
REPAIRS = (
    ("Appreciati n g", "Appreciating"), ("Appreciat ing", "Appreciating"),
    ("Apprais ing", "Appraising"), ("Shar ing", "Sharing"),
    ("a nd", "and"), ("Organi s ation", "Organisation"),
    ("Capitali s ation", "Capitalisation"), ("Request s", "Requests"),
    ("Role s", "Roles"), ("Relationship s", "Relationships"),
    ("Individual s", "Individuals"), ("Usin g", "Using"),
    ("Senten ces", "Sentences"), ("Readin g", "Reading"),
    ("Vocabul ary", "Vocabulary"), ("Festiva ls", "Festivals"),
    ("Leade rs", "Leaders"), ("Republi cs", "Republics"),
    ("Academ ic", "Academic"), ("T he", "The"), ("M OVEMENT", "MOVEMENT"),
    ("O NLINE", "ONLINE"), ("GENE RATION", "GENERATION"), ("samaison", "sa maison"),
    ("l'onaime", "l'on aime"), ("VALUE S", "VALUES"), ("BELI E FS", "BELIEFS"),
    ("C apacity", "Capacity"), ("SCIENC E", "SCIENCE"), ("AN D", "AND"),
    ("HUMA N", "HUMAN"),
)

WORD_RX = re.compile(r"[A-Za-z][A-Za-z'’\-]*")


def repair_pattern(broken: str) -> re.Pattern:
    """`a nd` -> a pattern matching the pieces with any space between them."""
    parts = [re.escape(part).replace("'", "['’]") for part in broken.split()]
    return re.compile(r"\b" + r"\s+".join(parts) + r"\b")


REPAIR_RX = tuple((repair_pattern(broken), broken, good) for broken, good in REPAIRS)

_VOCAB: dict = {}


def fold_apostrophe(word: str) -> str:
    """The prints set both apostrophes; vocabulary and repairs compare on one."""
    return word.lower().replace("\u2019", "'")


def vocabulary(pdf: str) -> collections.Counter:
    """Every word the print sets, lower-cased — the evidence a repair is checked on."""
    if pdf not in _VOCAB:
        counts: collections.Counter = collections.Counter()
        for page in range(F.npages(pdf)):
            for _y, _x, text in L.visual_lines(pdf, page):
                counts.update(fold_apostrophe(word) for word in WORD_RX.findall(text))
        _VOCAB[pdf] = counts
    return _VOCAB[pdf]


def repair(name: str, pdf: str) -> tuple[str, list[tuple[str, str]]]:
    """(name, [(broken, repaired)]) — joins the pieces the print broke, where it can."""
    applied: list[tuple[str, str]] = []
    for pattern, broken, good in REPAIR_RX:
        if not pattern.search(name):
            continue
        words = vocabulary(pdf)
        if any(fold_apostrophe(word) not in words for word in WORD_RX.findall(good)):
            continue                    # the print never spells it whole; leave it be
        name = pattern.sub(good, name)
        applied.append((broken, good))
    return name, applied


_ROWS: dict = {}


def page_heads(pdf: str, page: int) -> list[tuple[float, str, str, str]]:
    """[(y, kind, number, name)] of the block headings this page prints, top-down.

    A heading is a visual line — `visual_lines` has already put the print's chunks back
    together — and it may wrap: `SUB - STRAND 2: INTRODUCTION TO ELECTRONIC SPREADSHEET`
    is followed by `(TABS AND RIBBONS MANIPULATION)` on the next line, and the name is
    only complete with it.  The next line is taken when the heading clearly stops short
    (ends on a conjunction, a comma), never when it is another heading, a code row, or
    one of the table's own column labels.
    """
    if (pdf, page) in _HEADS:
        return _HEADS[(pdf, page)]
    lines = L.visual_lines(pdf, page)
    out: list[tuple[float, str, str, str]] = []
    for i, (y, x, text) in enumerate(lines):
        match = SUB_HEAD.match(text)
        kind = "sub"
        if match:
            number, raw = (match.group(1) or ""), match.group(2)
        else:
            match = SUB_TAIL.match(text)
            if match:
                number, raw = (match.group("num") or ""), match.group("name")
            else:
                match = STRAND_HEAD.match(text)
                if not match:
                    continue
                kind, number, raw = "strand", (match.group(1) or ""), match.group(2)
        name = re.sub(r"\s+", " ", raw).strip()
        for j in range(i + 1, min(i + 3, len(lines))):
            _ny, nx, following = lines[j]
            if SUB_HEAD.match(following) or SUB_TAIL.match(following) \
                    or STRAND_HEAD.match(following):
                break
            if NOT_A_NAME.search(following) or F.line_code(following) \
                    or CODE_TOKEN.match(following):
                break
            if nx < x - 40 or nx > x + 400:
                break
            if re.search(r"(,|&|/|\band\b|\bof\b|\bthe\b|\bto\b|\bin\b|\bfor\b|\bwith\b)\s*$",
                         name, re.I):
                name = name + " " + following
            else:
                break
        out.append((y, kind, number, name))
    _HEADS[(pdf, page)] = out
    return out


def timeline(pdf: str) -> list[tuple[int, float, str, str, str]]:
    """Every heading of the print in reading order: (page, y, kind, number, name)."""
    if pdf not in _TIMELINE:
        out = []
        for page in range(F.npages(pdf)):
            for y, kind, number, name in page_heads(pdf, page):
                out.append((page, y, kind, number, name))
        # within a page the print reads top-down, and a PDF's y grows upwards
        out.sort(key=lambda head: (head[0], -head[1]))
        _TIMELINE[pdf] = out
    return _TIMELINE[pdf]


def in_force(pdf: str, page: int, y: float) -> tuple[str, tuple[str, str, int] | None]:
    """(strand number, (number, name, page) of the sub-strand heading) at the row `y`.

    A heading governs from where the print sets it until the next heading of its kind —
    across a page break as much as within a page, which is how a block that continues on
    the next table is still named.  A heading below the row (a smaller y) never governs
    it, so the last heading *above* the row is the one that does, and it carries the page
    it was printed on.
    """
    strand = ""
    sub: tuple[str, str, int] | None = None
    for hpage, hy, kind, number, name in timeline(pdf):
        if hpage > page or (hpage == page and hy <= y - 1.0):
            break
        if kind == "strand":
            strand = number
        else:
            sub = (number, name, hpage)
    return strand, sub


def row_y(pdf: str, page: int, code: str) -> float | None:
    """The y of the line that carries this code, wherever in the line the print set it."""
    want = fold_code(code)
    for y, _x, text in L.visual_lines(pdf, page):
        if want in fold_code(text):
            return y
    return None


def print_rows(pdf: str) -> list[dict]:
    """Every code-bearing row of the print, with the block heading read at its own y."""
    if pdf in _ROWS:
        return _ROWS[pdf]
    rows: list[dict] = []
    for page in range(F.npages(pdf)):
        lo, hi = F.column_edges(pdf, page)
        for y, text in F.page_lines(pdf, page, lo - BAND_TOLERANCE, hi + BAND_TOLERANCE):
            for match in CODE_TOKEN.finditer(text):
                code = fold_code(match.group(0))
                parts = comps(code)
                if not 4 <= len(parts) <= 6:
                    continue
                grade, strand, sub = parts[0], parts[1], parts[2]
                heading, head = in_force(pdf, page, y)
                name: str | None = None
                note = ""
                head_page: int | None = None
                agrees = True
                if not head:
                    note = "no sub-strand heading is in force above the row"
                else:
                    number, raw, head_page = head
                    tidy = tidy_name(raw)
                    if not is_name(tidy):
                        note = f"the heading is not a name: {raw[:40]!r}"
                        head_page = None
                    else:
                        name = F.dekerning(tidy, F.page_words(pdf, head_page))
                        # the numbers are a check on the *block* read, not on the row: a
                        # print may number its sub-strands by a scheme the record does not
                        # use (computing heads `B6.5.3.1.1` under `SUB - STRAND 2`), and a
                        # row the print itself carries is proof of its own block
                        if comps(heading) and comps(heading)[0] != strand:
                            note = f"the strand heading says {heading}, the row {strand}"
                            agrees = False
                        if comps(number) and (comps(number)[-1] != sub
                                              or (len(comps(number)) > 1
                                                  and comps(number)[-2] != strand)):
                            note = (note + "; " if note else "") + \
                                f"the sub-strand heading says {number}, the row {strand}.{sub}"
                            agrees = False
                rows.append({"page": page, "y": y, "code": code, "grade": grade,
                             "strand": strand, "sub": sub, "name": name, "note": note,
                             "head_page": head_page, "agrees": agrees})
    _ROWS[pdf] = rows
    return rows


def one_name(readings: collections.Counter) -> str | None:
    """The block's one name, or None when the print names it two ways.

    The prints set the same heading twice with the typesetting tightened (`GENE RATION`
    against `GENERATION` — the caller de-kerns, so only real differences survive) and
    once short against once long (`TECHNOLOGY IN THE COMMUNITY` /
    `… (COMMUNICATION)`).  A family of readings where one is the longest and the rest
    are its prefixes is one name; anything else is a disagreement and is refused.
    """
    if not readings:
        return None
    if len(readings) == 1:
        return next(iter(readings))
    variants = sorted(readings, key=lambda name: -len(name))
    best = variants[0]
    for other in variants[1:]:
        if F.blob(best).startswith(F.blob(other)) or F.similar(F.blob(best), F.blob(other)):
            continue
        return None
    return best


class Bucket:
    """The names a key was read under, and the page each was read on.

    A row is read under a heading the print may not have set for it: the same code is
    printed again on a later page under another block's heading (english B6.2.3.1.1
    appears under `Diphthongs` five blocks on).  Readings whose heading number agrees
    with the row's own components are therefore kept apart, and they settle the name
    whenever there are any — a print that numbers its sub-strands by another scheme
    (computing) simply has none, and the whole set speaks instead.
    """

    def __init__(self) -> None:
        self.readings: collections.Counter = collections.Counter()
        self.agreeing: collections.Counter = collections.Counter()
        self.pages: dict[str, int] = {}

    def add(self, name: str, page: int | None, agrees: bool) -> None:
        self.readings[name] += 1
        if agrees:
            self.agreeing[name] += 1
        if page is not None:
            self.pages.setdefault(name, page)

    def settle(self) -> tuple[str | None, collections.Counter]:
        name = one_name(self.agreeing) or one_name(self.readings)
        return name, self.readings

    def page(self, name: str) -> int | None:
        return self.pages.get(name)


class Print:
    """What one print says, indexed the four ways a record can be anchored."""

    def __init__(self, pdf: str):
        self.pdf = pdf
        self.by_code: dict[str, Bucket] = collections.defaultdict(Bucket)
        self.by_standard: dict[str, Bucket] = collections.defaultdict(Bucket)
        self.by_pair_grade: dict[tuple, Bucket] = collections.defaultdict(Bucket)
        self.by_pair: dict[tuple, Bucket] = collections.defaultdict(Bucket)
        for row in print_rows(pdf):
            if not row["name"]:
                continue
            name, page, agrees = row["name"], row["head_page"], row["agrees"]
            self.by_code[row["code"]].add(name, page, agrees)
            for length in range(3, 6):                     # `B6.5.3`, `B6.5.3.1`, …
                standard = ".".join(comps(row["code"])[:length])
                if standard != row["code"]:
                    self.by_standard[standard].add(name, page, agrees)
            self.by_pair_grade[(row["grade"], row["strand"], row["sub"])].add(name, page, agrees)
            self.by_pair[(row["strand"], row["sub"])].add(name, page, agrees)

    def read(self, code: str, cs_code: str) -> tuple[str | None, str, int | None, str]:
        """(name, evidence, page, reason) for one record, strongest evidence first."""
        if fold_code(code) in self.by_code:
            bucket = self.by_code[fold_code(code)]
            name, readings = bucket.settle()
            if name:
                return name, "row", bucket.page(name), "ok"
            return None, "row", None, f"the print names this row two ways: {sorted(readings)}"
        if cs_code and fold_code(cs_code) in self.by_standard:
            bucket = self.by_standard[fold_code(cs_code)]
            name, readings = bucket.settle()
            if name:
                return name, "standard", bucket.page(name), "ok"
            return None, "standard", None, \
                f"the print names this standard two ways: {sorted(readings)}"
        parts = comps(code)
        if len(parts) < 3:
            return None, "", None, "the code is too short to name a sub-strand"
        grade, strand, sub = parts[0], parts[1], parts[2]
        for key, evidence in (((grade, strand, sub), "pair"),
                              ((strand, sub), "cross-grade")):
            table = self.by_pair_grade if evidence == "pair" else self.by_pair
            bucket = table.get(key)
            if bucket is None:
                continue
            name, readings = bucket.settle()
            if name:
                return name, evidence, bucket.page(name), "ok"
            return None, evidence, None, f"the print names {key} two ways: {sorted(readings)}"
        return None, "", None, "no heading of this block is read in the print"


# --------------------------------------------------------------------------- #
# the records this pass owns
# --------------------------------------------------------------------------- #

def served() -> dict[tuple[str, str], dict[str, str]]:
    """(subject, grade) -> {indicator code: content-standard code}, from the bundle.

    The bundle is the definition of "served": 84 subject-grades, four per grade file.
    """
    out: dict[tuple[str, str], dict[str, str]] = {}
    for path in sorted(APP_CURRICULUM.glob("*_indicators.json")):
        for record in json.loads(path.read_text()):
            out.setdefault((record["subjectId"], record["grade"]), {})[record["code"]] = \
                record.get("contentStandardCode") or ""
    return out


def db_files() -> dict[tuple[str, str], Path]:
    """(subject, grade) -> the database file that carries it."""
    out: dict[tuple[str, str], Path] = {}
    for path in sorted(CURRICULUM.glob("*_curriculum_db_clean.json")):
        parsed = X.subject_grade(path.name)
        if parsed:
            out[parsed] = path
    return out


# `data/lessons/` names its files its own way (`math_b2`, `ghanaian_b2`, `english`)
LESSON_SUBJECT = {
    "math": "mathematics", "english": "english-language", "creative_arts": "creative-arts",
    "ghanaian": "ghanaian-language", "ghanaian_language": "ghanaian-language",
    "social_studies": "social-studies", "career_technology": "career-technology",
    "creative_arts_design": "creative-arts-design",
}


def lesson_subject_grade(stem: str) -> tuple[str, str]:
    """('math_b2') -> ('mathematics', 'B2'); ('owop') -> ('owop', 'B1')."""
    base, sep, tail = stem.rpartition("_")
    if sep and re.fullmatch(r"[Bb][1-9]", tail):
        subject, grade = base, tail.upper()
    else:
        subject, grade = stem, "B1"
    return LESSON_SUBJECT.get(subject, subject), grade


def lesson_files() -> list[tuple[Path, str, str]]:
    """[(path, subject, grade)] of the enriched lesson files, in reading order."""
    out = []
    for path in sorted(LESSONS.glob("*_lessons_enriched.json")):
        subject, grade = lesson_subject_grade(path.name[: -len("_lessons_enriched.json")])
        out.append((path, subject, grade))
    return out


def page_text(pdf: str, page: int) -> str:
    """The page's own words, folded-free, for the phrase check."""
    return " ".join(text for _y, _x, text in L.visual_lines(pdf, page))


def scan(apply: bool) -> dict:
    """Read every code-shaped sub-strand of the served databases against its print."""
    bundle = served()
    files = db_files()
    writes: list[dict] = []
    refused: list[dict] = []
    prints: dict[str, Print] = {}
    tally: collections.Counter = collections.Counter()
    repairs: collections.Counter = collections.Counter()
    per_file: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for (subject, grade), codes in sorted(bundle.items()):
        path = files.get((subject, grade))
        if path is None:
            refused.extend({"file": "", "code": code, "strand": "",
                            "reason": "no database file for this subject-grade"}
                           for code in codes)
            tally["no database file"] += len(codes)
            continue
        data = json.loads(path.read_text())
        pdf = X.print_for(subject, grade)
        if not pdf:
            refused.extend({"file": path.name, "code": code, "strand": "",
                            "reason": "no print is registered for this subject-grade"}
                           for code in codes)
            tally["no print"] += len(codes)
            continue
        if pdf not in prints:
            prints[pdf] = Print(pdf)
        source = prints[pdf]
        changed = False
        for code, cs_code in sorted(codes.items()):
            record = data.get(code)
            if not isinstance(record, dict):
                continue
            before = str(record.get("sub_strand", ""))
            if not CODE_SHAPED.match(before.strip()):
                continue                    # a name already; not this pass's business
            name, evidence, page, reason = source.read(code, cs_code)
            parts = comps(code)
            if name and page is not None and not F.blob_in(page_text(pdf, page), name):
                name, reason = None, f"page {page} does not print {name!r}"
            if not name:
                refused.append({"file": path.name, "code": code,
                                "strand": "/".join(parts[1:3]), "sub": before,
                                "reason": reason})
                tally["refused"] += 1
                continue
            name, repaired = repair(name, pdf)
            for broken, good in repaired:
                repairs[f"{broken} -> {good}"] += 1
            after = f"{parts[2]}. {name}" if len(parts) > 2 else name
            writes.append({"file": path.name, "code": code, "before": before,
                           "after": after, "source": evidence, "page": page,
                           "print": pdf})
            tally[evidence] += 1
            per_file[path.name][evidence] += 1
            if after != before:
                changed = True
                if apply:
                    record["sub_strand"] = after
        if apply and changed:
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")

    # the lesson files: the served schedules read these where the database has no row
    lessons: list[dict] = []
    lessons_refused: list[dict] = []
    for path, subject, grade in lesson_files():
        pdf = X.print_for(subject, grade)
        if not pdf:
            continue                        # a subject-grade with no print has no read
        if pdf not in prints:
            prints[pdf] = Print(pdf)
        source = prints[pdf]
        data = json.loads(path.read_text())
        changed = False
        for index, lesson in enumerate(data):
            before = str(lesson.get("sub_strand", ""))
            if not CODE_SHAPED.match(before.strip()):
                continue
            code = str(lesson.get("ind_code") or "")
            name, evidence, page, reason = source.read(code, str(lesson.get("cs_code") or ""))
            parts = comps(code)
            where = {"file": path.name, "lesson": index + 1, "term": lesson.get("term"),
                     "week": lesson.get("week"), "day": lesson.get("day"),
                     "lesson_num": lesson.get("lesson_num")}
            if name and page is not None and not F.blob_in(page_text(pdf, page), name):
                name, reason = None, f"page {page} does not print {name!r}"
            if not name:
                lessons_refused.append({**where, "code": code, "reason": reason})
                continue
            name, repaired = repair(name, pdf)
            for broken, good in repaired:
                repairs[f"{broken} -> {good}"] += 1
            after = f"{parts[2]}. {name}" if len(parts) > 2 else name
            lessons.append({**where, "code": code, "before": before, "after": after,
                            "source": evidence, "page": page, "print": pdf})
            if after != before:
                changed = True
                if apply:
                    lesson["sub_strand"] = after
        if apply and changed:
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")

    return {"writes": writes, "refused": refused, "lessons": lessons,
            "lessons_refused": lessons_refused, "tally": tally,
            "repairs": dict(repairs),
            "per_file": {name: dict(counts) for name, counts in per_file.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="write the databases (default: report only)")
    args = parser.parse_args()

    result = scan(apply=args.apply)
    writes, refused = result["writes"], result["refused"]
    lessons, lessons_refused = result["lessons"], result["lessons_refused"]
    by_source = collections.Counter(write["source"] for write in writes)
    by_source_lessons = collections.Counter(lesson["source"] for lesson in lessons)
    print(f"sub-strands read from the prints: {len(writes)}")
    for source, count in by_source.most_common():
        print(f"   {source:11s} {count}")
    print(f"refused: {len(refused)}")
    for reason, count in collections.Counter(
            entry["reason"].split(":")[0] for entry in refused).most_common(10):
        print(f"   {count:5d}  {reason}")
    for entry in refused[:5]:
        print(f"      {entry['file']} {entry['code']}: {entry['reason'][:90]}")
    print(f"files: {len(result['per_file'])}")
    print(f"repairs: {sum(result['repairs'].values())} in {len(result['repairs'])} kinds")
    for case, count in sorted(result["repairs"].items(), key=lambda kv: -kv[1]):
        print(f"   {count:5d}  {case}")
    print(f"lesson records named: {len(lessons)} (refused {len(lessons_refused)})")
    for source, count in by_source_lessons.most_common():
        print(f"   {source:11s} {count}")

    # the lesson rows repeat one indicator many times, so they are recorded per file —
    # every row's own entry would triple the artifact for no new information.
    lesson_files_tally: dict[str, int] = collections.Counter(
        lesson["file"] for lesson in lessons)
    named = {write["code"] for write in writes}
    only_lessons = sorted({(lesson["code"], lesson["after"]) for lesson in lessons
                           if lesson["code"] not in named})

    artifact = {"applied": bool(args.apply), "written": writes, "refused": refused,
                "written_lessons": {"records": len(lessons),
                                    "files": dict(sorted(lesson_files_tally.items())),
                                    "sources": dict(by_source_lessons),
                                    "codes_absent_from_the_databases": only_lessons},
                "refused_lessons": lessons_refused,
                "repairs": result["repairs"],
                "totals": {"written": len(writes), "refused": len(refused),
                           "lesson_records": len(lessons),
                           "lesson_refused": len(lessons_refused),
                           **{source: count for source, count in by_source.items()}},
                "per_file": result["per_file"]}
    (AUDIT / "sub_strand_names.json").write_text(
        json.dumps(artifact, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
