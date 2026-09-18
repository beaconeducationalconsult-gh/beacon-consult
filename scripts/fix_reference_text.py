#!/usr/bin/env python3
"""Clean up the text fields of the reference-only subject-grades against their prints.

The eight subject-grades that no quality-assured database covers (computing B4-B6,
french B4-B6, kindergarten KG1-KG2) were extracted from the NaCCA PDFs by reading
the page, which glued the neighbouring columns onto the indicator description:

    "... discuss and point to things that are safe and unsafe to play with.
     References WP LL1 Core Competencies Communication and collaboration (CC)"

Three things are wrong in them, and every one is fixed against the print, never by
rewriting:

  keywords   empty in all 812 records.  No print carries keywords, so the tag the
             audited subject-grades use is applied: "<subject>, <grade>, <band>".
  ind_desc   the print's furniture — the footer, the column headings the print sets
             over the table (even where they fall inside the indicator column's own
             x band), the core-competence labels, the reference codes, the row
             markers the extractor read past — is deleted from the indicator
             description.  A span is only deleted when the print sets it *outside*
             the record's own row, so a description that legitimately mentions, say,
             "communication and collaboration" as part of its activity keeps it; a
             label the extractor copied only halfway (`… - Creativity and innov`),
             and text the print sets in a *different* record's row, are cut too —
             each one only as far as the print itself says so.  What survives is
             then read back against the print and graded: `row`/`page` mean the
             print sets it verbatim, `row-order`/`page-order`/`document-order` mean
             every word of it is printed in the order the record carries them, and a
             record whose survivor the print does not carry is left alone.
  cs_desc    the kindergarten content standards: 13 records hold no sentence at
             all, and many others carry the sentence plus the heading of the column
             next door (21 standards) or stop short of it (7).  All three are
             settled against the sentence the content-standard column prints for the
             standard, and every tag is spelled as the print's own cell reads.
             Five records of K2.5.1.1 hold *indicator*-column text instead: the
             print's sentence replaces it and the displaced value is kept in the
             audit trail.  K1.3.2.1's cell is blank in the print, so those five
             records keep what they have — as the audit already reports.

Reference copies of subjects the audits already cover (creative-arts B4-B6 and
social-studies B7-B9) also have empty keywords, but their records are a stale
extraction and do not match the curriculum copies.  The tag is read off the
audited copy of the same name and written — it is the field's convention, not
anything the file says — and reported apart from the eight subject-grades above.

Report only by default; pass --apply to write.  The audit trail goes to
data/audit/reference_text_fixes.json.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import pickle
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from _paths import AUDIT, CURRICULUM, REFERENCE, SOURCES  # noqa: E402

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - the tooling venv carries pypdf
    sys.exit("pypdf is required: run this with /tmp/pdfvenv/bin/python")

# --------------------------------------------------------------------------- #
# what is read, and where
# --------------------------------------------------------------------------- #

SUBJECTS = {
    # subject: (print, grades) — the subject-grades this script owns
    "computing": ("computing_B4-B6.pdf", ("B4", "B5", "B6")),
    "french": ("french_B4-B6.pdf", ("B4", "B5", "B6")),
    "kindergarten": ("kindergarten_KG1-KG2.pdf", ("KG1", "KG2")),
}

BAND = {"B4": "upper-primary", "B5": "upper-primary", "B6": "upper-primary",
        "KG1": "kindergarten", "KG2": "kindergarten"}

# x band of the indicator column, measured per print: the geometry is not shared,
# and a single band for all three either swallows a side column or cuts the
# indicator text (french runs to 603, computing stops at 531)
WINDOW = {
    "computing_B4-B6.pdf": (190.0, 545.0),
    "french_B4-B6.pdf": (140.0, 560.0),
    "kindergarten_KG1-KG2.pdf": (185.0, 545.0),
}

# x band of the content-standard column, kindergarten only (its body tables set
# that column at 93.6-103.1 and the indicator column starts at 214)
CS_BAND = {"kindergarten_KG1-KG2.pdf": (85.0, 190.0)}

# Column headings the extractor copied along with the row it was reading.
HEADINGS = ("indicators and exemplars", "indicator and exemplars",
            "indicators and examples", "indicator and examples", "core competencies",
            "core competences", "content standard", "content standards",
            "subject specific practices", "subject specific practice", "references",
            "keywords", "assessment", "resources", "strand", "sub-strand",
            "cont'd", "continued", "exemplar", "exemplars")

# The core-competence column: the labels NaCCA prints there (the skills the
# curriculum is built on) plus the ones these prints abbreviate.
CC_LABELS = ("communication and collaboration", "critical thinking and problem solving",
             "creativity and innovation", "cultural identity and global citizenship",
             "personal development and leadership", "digital literacy",
             "communication and digital literacy", "creativity and problem solving",
             "problem solving and critical thinking", "skill development",
             "data collection skill", "health and safety in using ict tools",
             "subject specific practices", "leadership", "innovation",
             "creativity", "communication", "collaboration", "critical thinking",
             "literacy", "competencies", "competences", "youtube")

# The french print heads its content-standard column with the skill area, and the
# extractor copied those labels into the indicator descriptions too.
FRENCH_CS_LABELS = ("compréhension orale", "production orale",
                    "compréhension écrite", "production écrite",
                    "compréhension", "production", "orale", "écrite")

EXTRA = {"french": FRENCH_CS_LABELS, "computing": (), "kindergarten": ()}

FOOTER = re.compile(r"©\s*NaCCA", re.I)
# A line of the table's own furniture: the block headings a row can run into when
# the print starts its next table on the same page (`… de ce que l'on n'aime pas.
# STRAND 4: Les activités INDICATOR AND EXEMPLARS`).  A row ends there.
BLOCK_HEADING = re.compile(
    r"^\s*(?:strand|sub\s*-\s*strand)\b"
    r"|^\s*(?:indicators? and (?:exemplars|examples)|core\s+competen\w*|"
    r"content\s+standards?|references|subject\s+specific\s+practice\w*)"
    r"\s*[.:\-]?\s*$", re.I)
INDICATOR = re.compile(r"([BK])\s*(\d)\s*(?:/\s*JHS\s*\d)?(?:\s*\.\s*\d+){2,6}")
# An orphan marker the extraction left at the end of a row: a list number, an
# initial, or a table's continuation label.  The alternatives carry punctuation
# or the label's capitals on purpose — a bare word could just as well be the end
# of the sentence, and a marker the row itself carries is the row's.
MARKER_TOKEN = re.compile(r"^(?:\d{1,3}[.)]|[A-Za-z]{1,2}[.)]"
                          r"|[Cc][Oo][Nn][Tt][’']?[Dd]|[Cc]ontinued)\.?$")
# an unpunctuated number is a marker only as part of a run (`… etc. 1 2 3`)
MARKER_RUN = re.compile(r"^\d{1,3}$")
CC_TAG = re.compile(r"\s*\(\s*(?:CC|CP|PL|CI|DL|PC|CGC|CSE|CG|OL|OWOP)\s*\)")
# Fragments of the side columns' vocabulary: the extractor kept half a label where
# the column's edge cut it (`- Communication and collabora`, `Cultural id`,
# `Creativity and innov`), so the stems are furniture too.
STEMS = ("collabora", "communicat", "creativ", "innovat", "leadersh", "literac",
         "competen", "personal development", "development and", "cultural",
         "critical", "proble msolv", "proble solving", "youtube", "documents aux cref")
KG_CODE = re.compile(r"(?<![A-Za-z(])(?:LL|WP|CA|PD|CP|CC|CI|DL|CGC|CSE|OWOP|N)"
                     r"\s*[.,]?\s*\d+(?:\s*[.,]\s*\d+)*")
# the same codes where the print dropped the number altogether ("the various WP
# ways new connect with the outside")
BARE_CODE = re.compile(r"(?<![A-Za-z(])(?:LL|WP|CA|PD|CP|CC|CI|DL|CGC|CSE|OWOP|CG|N)"
                       r"(?![A-Za-z0-9])")

# Stems of words that only the columns beside the indicator use.  The extractor
# sometimes kept half a label (`- Personal development and ex`, `Production cr`),
# so the whole phrase never matches and the tail is trimmed from the stem instead.
FRAGMENT = re.compile(r"(?:personal development|development and|developmen|leadersh"
                      r"|critical thinking|cultural identity|global citizensh"
                      r"|digital literac|innovation|literac|competen"
                      r"|references|subject specific|youtube|production \w"
                      r"|compréhension \w|production \w)", re.I)

# What can only be the print's furniture when it sits at the very end of a
# sentence: the heading of the next column or a reference code.  The competence
# labels are deliberately *not* here — "digital literacy" and "innovation" are
# ordinary words in a French or computing sentence, and a cleanup must never cut
# a sentence that reads on.
TAIL_JUNK = re.compile(r"[\s·]*(?:" + "|".join(
    [re.escape(h) for h in HEADINGS + FRENCH_CS_LABELS + STEMS]
    + [CC_TAG.pattern, KG_CODE.pattern, BARE_CODE.pattern]) + r")\s*$", re.I)

# Furniture that can follow a sentence inside one cell: the heading of the next
# column or a reference code — never a sentence of its own.
JUNK = re.compile("|".join([re.escape(h) for h in HEADINGS + FRENCH_CS_LABELS + STEMS]
                           + [KG_CODE.pattern, BARE_CODE.pattern, CC_TAG.pattern]),
                  re.I)

CACHE = AUDIT / "pdf_chunk_cache"
ARTIFACT = AUDIT / "reference_text_fixes.json"


# --------------------------------------------------------------------------- #
# reading the prints
# --------------------------------------------------------------------------- #

_READERS: dict = {}
_CHUNKS: dict = {}
_ROWS: dict = {}
_RULES: dict = {}
_PAGE_WORDS: dict = {}


def _reader(pdf: str):
    if pdf not in _READERS:
        _READERS[pdf] = PdfReader(str(SOURCES / pdf))
    return _READERS[pdf]


def npages(pdf: str) -> int:
    return len(_reader(pdf).pages)


def _cache_path(pdf: str) -> Path:
    digest = hashlib.md5((SOURCES / pdf).read_bytes()).hexdigest()[:8]
    return CACHE / f"{Path(pdf).stem}-{digest}-v2.pkl"


def _extract_pages(pdf: str, pages: list[int]) -> list[list[tuple[float, float, str]]]:
    """[(x, y, text)] per page — one entry per text-showing operation."""
    reader = _reader(pdf)
    out = []
    for n in pages:
        page = reader.pages[n]
        rows: list[tuple[float, float, str]] = []

        def visit(text, cm, tm, font_dict, size, rows=rows):
            if not text.strip():
                return
            x = tm[4] if tm else 0.0
            y = tm[5] if tm else 0.0
            if cm:
                x += cm[4]
                y += cm[5]
            rows.append((round(x, 1), round(y, 1), text))

        page.extract_text(visitor_text=visit)
        out.append(rows)
    return out


def chunks(pdf: str, pages=None) -> list[tuple[int, float, float, str]]:
    """[(page, x, y, text)] — cached in memory and on disk (the dir is ignored)."""
    if pdf not in _CHUNKS:
        _CHUNKS[pdf] = {}
    have = _CHUNKS[pdf]
    want = range(npages(pdf)) if pages is None else list(pages)
    todo = [n for n in want if n not in have]
    if todo:
        disk = None
        if len(have) == 0 and _cache_path(pdf).exists():
            try:
                disk = pickle.loads(_cache_path(pdf).read_bytes())
            except Exception:                                   # a stale schema
                disk = None
        if disk and npages(pdf) == len(disk):
            have.update({n: disk[n] for n in range(len(disk))})
            todo = [n for n in want if n not in have]
        if todo:
            for n, rows in zip(todo, _extract_pages(pdf, todo)):
                have[n] = rows
            CACHE.mkdir(parents=True, exist_ok=True)
            _cache_path(pdf).write_bytes(
                pickle.dumps([have[n] for n in range(npages(pdf))]))
    return [(n, x, y, t) for n in want for x, y, t in have[n]]


def page_rules(pdf: str, page: int) -> list[float]:
    """x of the page's vertical column rules (thin, tall rectangles)."""
    key = (pdf, page)
    if key not in _RULES:
        out = set()
        contents = _reader(pdf).pages[page].get_contents()
        operations = contents.operations if contents is not None else []
        for op in operations:
            try:
                operands, operator = op
            except (TypeError, ValueError):
                continue
            if operator != b"re":
                continue
            x, _y, w, h = (float(v) for v in operands)
            if w < 2.5 and h > 5:
                out.add(round(x, 1))
        _RULES[key] = sorted(out)
    return _RULES[key]


def column_edges(pdf: str, page: int) -> tuple[float, float]:
    """(lo, hi) x band of the indicator column on this page.

    Every page of these prints draws its own table, and the tables are not the same
    width (the computing print sets its indicator column at 214-562 on one page and
    204-527 on the next), so the band is read off the page's own rules: the first
    rule inside the page is the content-standard column's left edge, the second
    separates that column from the indicator column, and the third closes the
    indicator column.
    """
    rules = [x for x in page_rules(pdf, page) if 60 <= x <= 760]
    if len(rules) >= 3 and 100 <= rules[1] <= 300 and rules[2] - rules[1] >= 150:
        return rules[1] + 1, rules[2] - 1
    return WINDOW[pdf]


def page_lines(pdf: str, page: int, lo: float, hi: float) -> list[tuple[float, str]]:
    """The page's text in one x band, as visual lines, top to bottom.

    A line's chunks are joined left to right; a chunk with no horizontal neighbour
    starts a new line.
    """
    rows = chunks(pdf, [page])
    band = sorted(((x, y, t) for _p, x, y, t in rows if lo <= x <= hi),
                  key=lambda r: (-r[1], r[0]))
    out: list[tuple[float, str]] = []
    for x, y, text in band:
        if out and abs(y - out[-1][0]) <= 2.0:
            out[-1] = (out[-1][0], out[-1][1] + " " + text)
        else:
            out.append((y, text))
    return [(y, re.sub(r"\s+", " ", t).strip()) for y, t in out]


def ind_lines(pdf: str, page: int) -> list[tuple[float, str]]:
    return page_lines(pdf, page, *column_edges(pdf, page))


def side_lines(pdf: str, page: int, side: str) -> list[tuple[float, str]]:
    """The page's lines in the columns beside the indicator column, in reading order."""
    lo, hi = column_edges(pdf, page)
    if side == "left":
        return [(y, t) for y, t in page_lines(pdf, page, 0.0, lo) if t]
    return page_lines(pdf, page, hi, 1_000.0)


def blob(text: str) -> str:
    """Letters and digits only, lowercased — how the print and the database are
    compared (the two disagree about spaces and punctuation constantly)."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def tidy(text: str) -> str:
    """Re-space what removing the furniture left behind — and nothing else.

    Punctuation is left as the print sets it: the french pages space their `:`
    and `?`, the english ones do not, and a cleanup is no place to restyle.
    """
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    text = re.sub(r"\s+([’'])", r"\1", text)
    text = re.sub(r"(?:\s*[-–—]\s*){2,}", " ", text)     # bullets whose text is gone
    text = re.sub(r"\s+", " ", text)
    return text.strip(" -;:,")


def strip_code_prefix(text: str) -> str:
    m = re.match(r"^\s*[BK]\s*\d(?:[\d\s.]*\d)?", text)
    rest = text[m.end():] if m else text
    return re.sub(r"^[\s.:;-]+", "", rest)


def cut_at_blob(text: str, n: int) -> tuple[str, str]:
    """(head, rest) of `text` split after its n-th letter or digit."""
    k, at = 0, len(text)
    for i, ch in enumerate(text):
        if ch.isalnum():
            k += 1
        if k == n:
            at = i + 1
            break
    return text[:at], text[at:]


def backed_prefix(want: str, have: str) -> int:
    """How many characters of `want` `have` carries, from `want`'s own start."""
    n = 0
    while n < len(want) and want[:n + 1] in have:
        n += 1
    return n


# --------------------------------------------------------------------------- #
# the codes, the rows, the columns
# --------------------------------------------------------------------------- #

def code_aliases(code: str) -> list[str]:
    """The record's code and the shallower codes the print may number it with."""
    parts = [p for p in re.split(r"[.\s]+", code) if p]
    out = [".".join(parts)]
    while len(parts) > 3:
        parts = parts[:-1]
        out.append(".".join(parts))
    return out


def comps(text: str) -> tuple[str, ...]:
    """A code as its components (`B5.6.4.9.1` -> ('B','5','6','4','9','1'))."""
    return tuple(re.findall(r"[A-Za-z]+|\d+", text))


def code_pages(pdf: str) -> dict[str, list[int]]:
    """printed code -> the pages whose indicator column carries it.

    These prints repeat a row on every page of its block (kindergarten does, with
    different exemplars each time), so a record's text may come from any of them.
    """
    key = f"_codes_all::{pdf}"
    if key in _CHUNKS:
        return _CHUNKS[key]
    out: dict[str, list[int]] = defaultdict(list)
    for page in range(npages(pdf)):
        for _y, text in ind_lines(pdf, page):
            found = {re.sub(r"\s+", "", m.group(0)) for m in INDICATOR.finditer(text)}
            m = re.match(r"^\s*([BK]\s*\d[\d\s.]*\d)\s*$", text)   # one code per line
            if m:
                found.add(re.sub(r"\s+", "", m.group(1)))
            for code in found:
                if page not in out[blob(code)]:
                    out[blob(code)].append(page)
    _CHUNKS[key] = out
    return out


def code_index(pdf: str) -> list[tuple[tuple[str, ...], int]]:
    """Every indicator code the print sets in its indicator column, per page."""
    key = f"_index::{pdf}"
    if key not in _CHUNKS:
        found = []
        seen = set()
        for page in range(npages(pdf)):
            for _y, text in ind_lines(pdf, page):
                m = re.match(r"^\s*([BK][\d\s.]*[\d])", text)
                if not m:
                    continue
                parts = comps(m.group(1))
                if len(parts) >= 5 and (parts, page) not in seen:
                    seen.add((parts, page))
                    found.append((parts, page))
        _CHUNKS[key] = found
    return _CHUNKS[key]


def pages_of(pdf: str, code: str) -> list[int]:
    """The pages whose indicator column sets this record's code.

    A few records lost or gained a level in extraction (`B5.6.4.9.1` for the
    print's `B5.6.4.9.1.1`), so codes are matched on component boundaries, never
    on characters: `…4.9.1` must not pick up `…4.9.11`.
    """
    pages = code_pages(pdf)
    for alias in code_aliases(code):
        if blob(alias) in pages:
            return pages[blob(alias)]
    mine = comps(code)
    hits = []
    for theirs, page in code_index(pdf):
        n = 0
        while n < min(len(mine), len(theirs)) and mine[n] == theirs[n]:
            n += 1
        if n >= 4 and n in (len(mine), len(theirs)):
            hits.append((-n, page))
    return sorted({page for _n, page in sorted(hits)})


def line_code(text: str) -> str:
    """The indicator code a line starts with, folded ('' when it starts with none)."""
    m = re.match(r"^\s*([BK]\s*\d[\d\s.]*[\d])", text)
    return blob(m.group(1)) if m else ""


def page_rows(pdf: str, page: int) -> list[tuple[str, str]]:
    """The page's indicator column split into rows: (code, text).

    A row starts at a line that leads with an indicator code, or at one of the
    table's block headings — which is where a row ends when the print starts its
    next table on the same page and the row below has no code of its own.
    """
    key = (pdf, page)
    if key not in _ROWS:
        rows: list[list] = []
        for _y, text in ind_lines(pdf, page):
            code = line_code(text)
            if code or BLOCK_HEADING.match(text) or not rows:
                rows.append([code, text])
            else:
                rows[-1][1] += " " + text
        _ROWS[key] = [(code, dekerning(text, page_words(pdf, page)))
                      for code, text in rows]
    return _ROWS[key]


def other_rows(pdf: str, code: str) -> str:
    """What the record's pages print in the indicator column *beside* its own row."""
    wanted = {blob(a) for a in code_aliases(code)}
    return " ".join(text for page in pages_of(pdf, code)
                    for row_code, text in page_rows(pdf, page)
                    if row_code not in wanted)


def row_text(pdf: str, page: int, code: str) -> str:
    """The record's own row: the indicator column from its code down to the next.

    The print breaks words where its typesetting tightens (`R ead , use and copy`),
    and the database holds the clean reading, so the row is de-kerned before it is
    used as the yardstick for what the record may say.
    """
    wanted = {blob(a) for a in code_aliases(code)}
    return " ".join(text for row_code, text in page_rows(pdf, page)
                    if row_code in wanted)


def row_text_all(pdf: str, code: str) -> str:
    """Every page's reading of the record's row, joined.

    The row's own code is taken off: the print's numbering is full of the same
    digits and dots as the markers the extraction left behind (`… checklists, etc.
    1. 2. 3.` against a row numbered `B6.1.3. 1.7.`), and leaving it in would say
    that every marker is part of the row.
    """
    return " ".join(strip_code_prefix(row_text(pdf, page, code))
                    for page in pages_of(pdf, code)
                    if row_text(pdf, page, code))


def column_text(pdf: str, pages: list[int]) -> str:
    """The indicator column of `pages`, in reading order."""
    return " ".join(strip_code_prefix(" ".join(t for _y, t in ind_lines(pdf, p)))
                    for p in pages)


def document_text(pdf: str) -> str:
    """The whole print's indicator column, page by page (the weakest reading of
    'the print sets this text' that a deletion-only cleanup can stand on)."""
    key = f"_doc::{pdf}"
    if key not in _CHUNKS:
        _CHUNKS[key] = column_text(pdf, list(range(npages(pdf))))
    return _CHUNKS[key]


def outside_text(pdf: str, page: int) -> str:
    """Everything the page prints outside the indicator column."""
    lo, hi = column_edges(pdf, page)
    parts = []
    for _p, x, _y, t in chunks(pdf, [page]):
        if x < lo or x > hi:
            parts.append(t)
    return re.sub(r"\s+", " ", " ".join(parts))


# --------------------------------------------------------------------------- #
# the print's furniture, and what the database picked up from it
# --------------------------------------------------------------------------- #

def vocabulary(subject: str) -> list[tuple[str, str]]:
    """The furniture to delete, longest phrase first.

    Every entry is checked against the prints and against the data by `evidence()`
    before it is used: the headings and competence labels NaCCA sets in the columns
    either side of the indicator column, plus the reference codes those columns
    print (`WP`, `LL2`, `(CC)`, `N3.1`).
    """
    items = [(text, blob(text)) for text in HEADINGS + CC_LABELS + EXTRA[subject]]
    items.sort(key=lambda r: -len(r[1]))
    return items


def side_items(pdf: str, page: int) -> list[tuple[str, str]]:
    """Word-runs the print sets in the columns beside this page's indicator rows.

    The chunks of each side column are read in visual order first, because the
    phrases that end up in the database run on past the end of one printed line
    (`eating good food and visiting the hospital when sick` is set over two); a run
    is a candidate only as a verbatim slice of that reading.  The columns carry
    phrases the indicator column never sets, such as the competence list on the
    right and the content standard on the left.
    """
    key = (pdf, page)
    if key not in _CHUNKS:
        runs: list[str] = []
        for side in ("left", "right"):
            words: list[str] = []
            for _y, line in side_lines(pdf, page, side):
                words += line.split()
            for span in range(min(8, len(words)), 2, -1):
                for i in range(len(words) - span + 1):
                    runs.append(" ".join(words[i:i + span]))
        out, seen = [], set()
        for frag in runs:
            b = blob(frag)
            if len(b) >= 15 and b not in seen:
                seen.add(b)
                out.append((frag, b))
        _CHUNKS[key] = out
    return _CHUNKS[key]


def side_vocabulary(pdf: str, subject: str, haystack: str) -> list[dict]:
    """For each piece of furniture: where it is printed, and where it is used."""
    printed: dict[str, int] = Counter()
    for page in range(npages(pdf)):
        outside = blob(outside_text(pdf, page))
        for item, b in vocabulary(subject):
            if b and b in outside:
                printed[b] += 1
    out = []
    for item, b in vocabulary(subject):
        out.append({"item": item, "printed_on_pages": printed.get(b, 0),
                    "in_the_data": bool(b) and b in haystack})
    return out


def page_words(pdf: str, page: int) -> set[str]:
    """Every word the page prints, folded — the yardstick for a split word.

    The print breaks words across chunks where the typesetting tightened (`by e
    ating`, `per sonal`, `Dem onstrate`).  The same word usually appears unbroken
    somewhere on the page, so a split is repaired only when the page itself shows
    the joined spelling.
    """
    key = (pdf, page)
    if key not in _PAGE_WORDS:
        words = set()
        for _p, _x, _y, text in chunks(pdf, [page]):
            words.update(blob(w) for w in text.split() if blob(w))
        _PAGE_WORDS[key] = words
    return _PAGE_WORDS[key]


def dekerning(text: str, words: set[str]) -> str:
    """Rejoin a word the print split across two chunks."""
    out: list[str] = []
    for token in text.split():
        if not out:
            out.append(token)
            continue
        head = out[-1].rstrip(",;:.")
        piece = blob(head)
        if re.fullmatch(r"[A-Za-z]{1,3}", head) and piece not in words \
                and len(token) > 2 and blob(head + token) in words:
            out[-1] = head + token                # `R ead , use` -> `Read, use`
        else:
            out.append(token)
    return " ".join(out)


def similar(one: str, two: str, floor: float = 0.95) -> bool:
    """Whether two folded strings are the same text bar a letter or two.

    The print's own typesetting splits words and drops letters (`Demonstra
    understanding`, `commun it ies`), and the extraction kept the clean form — the
    one the database holds is the better of the two, not something to replace.
    """
    if not one or not two:
        return False
    return difflib.SequenceMatcher(None, one, two).ratio() >= floor


APOSTROPHE = "[\u2019']"


def words_pattern(item: str) -> str:
    """`item` as a whole-word pattern, tolerating the print's spacing and quotes.

    The prints set an apostrophe as often as the typographic one (`CONT'D` /
    `CONT’D`), and the extractor copied whichever it found, so both spellings have
    to match the same item.
    """
    parts = [re.escape(word).replace("'", APOSTROPHE) for word in item.split()]
    return r"(?<![A-Za-z0-9])" + r"[\s\u00ad-]*".join(parts) + r"(?![A-Za-z0-9])"


def phrase_in(text: str, item: str) -> bool:
    """Whether `item` is in `text` as whole words.

    Plain containment would say that the tag `(PL)` is "in" a row that happens to
    spell `Exemplars`, and that a code is "in" a row full of digits.
    """
    if not text or not item:
        return False
    return re.search(words_pattern(item), text, re.I) is not None


def blob_in(row: str, item: str) -> bool:
    """Whether the print's own row carries `item`, folded.

    Folding is what makes this usable on these prints: the typesetting splits
    words as it tightens a line, so the row prints `the important r oles and
    responsibilit ies` where the database reads `roles and responsibilities`, and
    only the folded comparison sees that the row carries the phrase.
    """
    b = blob(item)
    return bool(b) and b in blob(row)


def find_spans(text: str, item: str) -> list[tuple[int, int]]:
    """Where `item` sits in `text`, tolerating the print's hyphen/space variants."""
    return [(m.start(), m.end())
            for m in re.finditer(words_pattern(item), text, re.I)]


def extend_spans(text: str, spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    """Grow each span over the bullet or list number that introduced it.

    The extractor copies the marker along with the label (`- Communication and
    collaboration`), so the marker goes with it: a leftover `- -` is debris the
    reader has to skip past.  A *number* is never absorbed — `… le 5 mai 1966.
    - Communication and collaboration` is a sentence and its furniture, and eating
    the `1966.` would eat the print's own words.
    """
    out = []
    for start, end, kind in spans:
        if kind in ("column text", "column header", "competence label"):
            while True:
                m = re.search(r"(?:\s*(?:[-–—])\s*)$", text[:start])
                if not m or not m.group():
                    break
                start = m.start()
            m = re.match(r"\s*\.", text[end:])                  # the item's own stop
            if m:
                end += m.end()
        out.append((start, end, kind))
    return out


def cut_spans(text: str, spans: list[tuple[int, int, str]]) -> tuple[str, list[int]]:
    """`text` without `spans`, plus the original index of every surviving character."""
    gone = bytearray(len(text))
    for start, end, _kind in spans:
        for i in range(max(0, start), min(len(text), end)):
            gone[i] = 1
    kept, index = [], []
    for i, ch in enumerate(text):
        if not gone[i]:
            kept.append(ch)
            index.append(i)
    return "".join(kept), index


def strip_footer_span(text: str) -> tuple[int, int] | None:
    """[start, end) of the print's footer, its page number, and all that follows.

    The extractor read the footer on its way down the page and kept going, so the
    whole tail of the field is furniture: the next page's headings, the subject
    panel list, whatever the reading order picked up next.
    """
    m = FOOTER.search(text)
    if not m:
        return None
    start = m.start()
    page_no = re.search(r"\s*\d{1,3}\s*$", text[:start])       # `… desktop 3 © NaCCA`
    if page_no:
        start = page_no.start()
    return start, len(text)


def marker_span(text: str, row: str) -> tuple[int, int] | None:
    """[start, end) of a run of row markers left dangling at the very end.

    `… checklists, etc. 1. 2. 3.` is the numbering of the list the extractor was
    reading past, not the end of the sentence.  A run the row's own text ends with
    is the row's (`… up to 5.` keeps its 5) and is left alone.
    """
    if not text.strip() or not row.strip():
        return None                          # no row read: nothing to judge it against
    toks = list(re.finditer(r"\S+", text))
    i = len(toks)
    while i and MARKER_TOKEN.match(toks[i - 1].group()):
        i -= 1
    if i == len(toks):                       # no punctuated marker: allow `1 2 3`
        i = len(toks)
        while i and MARKER_RUN.match(toks[i - 1].group()) \
                and not phrase_in(row, toks[i - 1].group()):
            i -= 1
        if i == len(toks):                    # a number the row never prints
            return None
    if i == 0 or i == len(toks):
        return None
    run = text[toks[i].start():].strip()
    if phrase_in(row, run) or blob(row).endswith(blob(run)):
        return None
    return toks[i].start(), len(text)


# Labels the prints set on a line of their own *inside* the indicator cell, in
# front of the exemplar text that follows (`… weather condition.` / `Exemplars:`).
CELL_LABELS = ("exemplars", "exemplar", "references", "assessment", "keywords",
               "competencies", "competences", "resources", "cont'd")


def cell_label_span(pdf: str, pages: list[int], text: str) -> tuple[int, int] | None:
    """[start, end) of a trailing label the print sets on a line of its own.

    The extractor read the cell down to the label and stopped, so the description
    ends with the heading of the block it was about to read.  The label is only
    cut when the record keeps a sentence of its own in front of it and the print
    really does set it as a line of its own — never when it is part of a sentence.
    """
    pattern = (r"(?<=[.:;!?])\s+(" + "|".join(re.escape(t) for t in CELL_LABELS)
               + r")\s*[:.]?\s*$")
    m = re.search(pattern, text, re.I)
    if not m:
        return None
    token = re.sub(r"\s+", " ", m.group(1)).strip().lower().rstrip(":.")
    lines = {re.sub(r"\s+", " ", line).strip().lower().rstrip(":.")
             for page in pages for _y, line in ind_lines(pdf, page)}
    if token in lines and len(blob(text[:m.start(1)])) >= 20:
        return m.start(1), len(text)
    return None


def strip_tail_junk(text: str) -> tuple[str, bool]:
    """Take the print's furniture off the end of a sentence, however many pieces.

    `… domestic and wild animals. Indicators and Exemplars References` is the
    sentence plus the two headings the extractor read next; the sentence is left
    exactly as the database spells it.
    """
    out = text.strip()
    gone = False
    while True:
        m = TAIL_JUNK.search(out)
        if not m:
            break
        cut = out[:m.start()].strip()
        if len(blob(cut)) < 40:            # the whole value is furniture: leave it
            break
        out, gone = cut, True
    return out, gone


def trim_fragment_tail(cleaned: str, row: str) -> tuple[str, str, int] | None:
    """Cut a trailing piece of a label the extraction truncated.

    Unlike the whole-phrase removals this one cannot be anchored on the print's
    text — the piece is half a label — so it fires only when the print's own row
    carries the head and the tail starts at words that only the side columns use.
    """
    rb = blob(row)
    if not rb or not cleaned or blob(cleaned) in rb:
        return None
    hb = blob(cleaned)
    n = backed_prefix(hb, rb)
    if n < max(30, 0.6 * len(hb)):
        return None
    head, tail = cut_at_blob(cleaned, n)
    if not FRAGMENT.search(tail):
        return None
    return head.rstrip(" -;:,."), tail, len(head)


def truncated_label_tail(text: str, items, row: str):
    """(head, tail, start) for a side-column label the extraction copied halfway.

    The extractor stopped mid-label wherever the print's line ran out — `… - Critical
    thinking - Creativity and innov` — so the last label is not there to be matched
    whole.  The tail is cut only as a *prefix* of a label the print sets outside this
    row, and only while the head is left substantial.
    """
    toks = list(re.finditer(r"\S+", text))
    for i in range(max(0, len(toks) - 6), len(toks)):
        head, tail = text[:toks[i].start()], text[toks[i].start():]
        tb = blob(tail)
        if len(tb) < 6 or len(blob(head)) < 20:
            continue
        if tb in blob(row):
            continue
        for _item, b in items:
            if len(b) > len(tb) and b.startswith(tb):
                return head, tail, toks[i].start()
    return None


def foreign_tail(pdf: str, code: str, text: str, row: str):
    """(head, tail, start) for a tail the print sets in a *different* record's row.

    The extraction read past the end of a row and kept the next table's first
    exemplars, or the previous row's — text that belongs to another record.  It is
    cut only as a whole-word run the print's other rows carry and this row does not.
    """
    toks = list(re.finditer(r"\S+", text))
    others = other_rows(pdf, code)
    rb = blob(row)
    for i in range(2, len(toks)):
        head, tail = text[:toks[i].start()], text[toks[i].start():]
        tb, hb = blob(tail), blob(head)
        if len(tb) < 10 or len(hb) < 20 or tb in rb:
            continue
        if len([w for w in words(tail) if len(w) >= 4]) < 2:
            continue
        if phrase_in(others, tail):
            return head, tail, toks[i].start()
    return None


def label_words(items) -> list[str]:
    """Every word of the labels the print sets beside the indicator column."""
    out = set()
    for item, _b in items:
        for word in item.split():
            b = blob(word)
            if len(b) >= 4:
                out.add(b)
    return sorted(out)


def orphan_fragment_spans(text: str, items, row: str,
                          printed: set[str]) -> list[tuple[int, int, str]]:
    """Spans of a label the extraction copied halfway.

    The extractor stopped mid-label wherever the print's line ran out, and left
    the stub behind after the label's own words were cut (`… - Creativity and
    innov`, `… Cultural ide`).  A token is that stub only when the print never
    sets it as a word of its own, a label word starts with it, and the record's
    own row carries no word that starts with it either — so a content word the
    extraction itself cut short (`… according to a given att`) stays.
    """
    out = []
    row_words = words(row)
    for m in re.finditer(r"\S+", text):
        tb = blob(m.group())
        if len(tb) < 2 or tb in printed:
            continue
        if any(w.startswith(tb) for w in row_words):
            continue
        if any(w.startswith(tb) and w != tb for w in label_words(items)):
            out.append((m.start(), m.end(), m.group()))
    return out


def printed_words(pdf: str) -> set[str]:
    """Every word the print sets anywhere, both columns, folded.

    The yardstick for a truncated word: the extraction stopped mid-word wherever
    the print's line broke (`… Creativity and innov`, `… Cultural ide`, `…
    according to a given att`), so a word the print never sets as a word, but does
    start a word with, is a truncation and not something the record made up.
    """
    key = f"_printed::{pdf}"
    if key not in _CHUNKS:
        ws: set[str] = set()
        for _p, _x, _y, text in chunks(pdf):
            ws.update(w for w in (blob(t) for t in text.split()) if w)
        _CHUNKS[key] = ws
    return _CHUNKS[key]


def words(text: str) -> list[str]:
    """The text's words, folded (`blob`), empties dropped."""
    return [w for w in (blob(t) for t in text.split()) if w]


def word_order(want: str, have: str, truncated: list[str] | None = None,
               printed: set[str] | None = None) -> bool:
    """Whether `want`'s words appear in `have` in order, gaps allowed.

    The extractor braided the columns, so a record's text can be a *reading* of
    the print that skips what it skipped; the check is that every word it carries
    is printed in the order it carries them, which is as much as a deletion-only
    cleanup can claim.  The print breaks words where its typesetting tightened
    (`by e ating`, `balance d`), so a wanted word may also be matched by two or
    three neighbouring printed words — and a word the extraction cut short is
    matched by the full word it starts, which is noted in `truncated` rather than
    written away: the truncation is the extraction's, not furniture.
    """
    w, h = words(want), words(have)
    if not w or not h:
        return False
    i = 0
    for n, token in enumerate(w):
        # a word the extraction cut short is only ever the tail of the value — the
        # page's text ran out there — so the tolerance is for the last two words and
        # no others: `Faire ment des calculs` must never pass itself off as a reading
        last = n >= len(w) - 2
        while i < len(h):
            window, j = h[i], i
            if window == token:
                i = j + 1
                break
            if token.startswith(window) and len(window) < len(token):
                while j + 1 < len(h) and len(window) < len(token):
                    j += 1
                    window = blob("".join(h[i:j + 1]))
                if window == token:
                    i = j + 1
                    break
            if last and len(token) >= 2 and window.startswith(token) \
                    and len(window) >= 5 and printed is not None \
                    and token not in printed:
                if truncated is not None:
                    truncated.append(f"{token}…{window}")
                i += 1
                break
            i += 1
        else:
            return False
    return True


def verify(pdf: str, code: str, page: int | None, cleaned: str,
           truncated: list[str] | None = None) -> str:
    """How the print backs the survivor, strongest first.

    `row` / `page` mean the print sets it verbatim (spacing and punctuation
    folded); `row-order` / `page-order` / `document-order` mean every word is
    there, in the order the record carries them, but the extraction skipped or
    copied around something between them; `unverified` means the print does not
    carry the survivor and nothing is written.
    """
    want = blob(cleaned)
    if not want or page is None:
        return "unverified"
    row = row_text_all(pdf, code)
    if want in blob(row):
        return "row"
    pages = [page] + ([page + 1] if page + 1 < npages(pdf) else [])
    page_text = column_text(pdf, pages)
    if want in blob(page_text):
        return "page"
    printed = printed_words(pdf)
    if word_order(cleaned, row, truncated, printed):
        return "row-order"
    if word_order(cleaned, page_text, truncated, printed):
        return "page-order"
    doc = document_text(pdf)
    if want in blob(doc):
        return "document"
    if word_order(cleaned, doc, truncated, printed):
        return "document-order"
    return "unverified"


def plan_ind_desc(pdf: str, code: str, text: str, items, headings=None,
                  pages: list[int] | None = None,
                  cache: dict | None = None) -> tuple[str, list[dict], list[str], str]:
    """(cleaned, removed, kept, note) for one indicator description.

    Nothing is cut on a guess: a span is marked for removal only when the print
    sets it outside the record's own row (it is furniture there), and the record is
    written only when the print backs the survivor and the marked spans account
    for every character that disappeared.
    """
    headings, pages, cache = headings or [], pages or [], cache if cache is not None else {}
    if code not in cache:
        row = row_text_all(pdf, code) if pages else ""
        # every page the record is printed on: a row runs over a page break, and the
        # furniture it picks up (`… les activités INDICATOR AND EXEMPLARS`) is set
        # beside the row on whichever page the print starts its next table
        outside = " ".join(outside_text(pdf, p) for p in pages)
        cache[code] = (row, outside)
    row, outside = cache[code]
    page = pages[0] if pages else None

    spans: list[tuple[int, int, str]] = []
    removed: list[dict] = []
    kept: list[str] = []

    foot = strip_footer_span(text)
    if foot:
        spans.append((*foot, "footer"))
        removed.append({"text": text[foot[0]:], "kind": "footer"})

    # the side columns' vocabulary, and the headings the print centres over the
    # table: the latter are set inside the indicator column's own x band, so they
    # are furniture by their own reading, not by where the page sets them
    for item, b in list(items) + list(headings):
        if len(b) < 3 or b not in blob(text):
            continue
        if blob_in(row, item) or (item in dict(items) and b not in blob(outside)):
            kept.append(item)                # the row itself says it: leave it be
            continue
        found = find_spans(text, item)
        if not found:
            continue
        for one, two in found:
            spans.append((one, two, "column text"))
        removed.append({"text": item, "kind": "column text"})

    for rx, kind in ((CC_TAG, "competence tag"), (KG_CODE, "reference code"),
                     (BARE_CODE, "reference code")):
        for m in rx.finditer(text):
            token = m.group().strip()
            if not blob(token):
                continue
            if phrase_in(row, token):
                kept.append(token)
                continue
            spans.append((m.start(), m.end(), kind))
            removed.append({"text": token, "kind": kind})

    spans = extend_spans(text, spans)

    def recut() -> tuple[str, list[int]]:
        out, idx = cut_spans(text, spans)
        return re.sub(r"\(\s*\)", " ", out), idx

    cleaned, index = recut()

    mk = marker_span(cleaned, row)
    if mk:
        one, two = mk
        spans.append((index[one], index[two - 1] + 1, "row marker"))
        removed.append({"text": cleaned[one:two], "kind": "row marker"})
        cleaned, index = recut()

    lab = cell_label_span(pdf, pages, cleaned)
    if lab:
        one, two = lab
        spans.append((index[one], index[two - 1] + 1, "cell label"))
        removed.append({"text": cleaned[one:two], "kind": "cell label"})
        cleaned, index = recut()

    # the print is the only authority for what stays, and it has three ways of
    # saying that a tail is not this record's: the row itself (a fragment the
    # extraction cut), a label set outside the row, another row's own text
    for _round in range(4):
        if verify(pdf, code, page, tidy(cleaned)) != "unverified":
            break
        cut = (trim_fragment_tail(cleaned, row)
               or truncated_label_tail(cleaned, items, row)
               or foreign_tail(pdf, code, cleaned, row))
        if not cut:
            break
        head, tail, at = cut
        spans.append((index[at] if at < len(index) else len(text), len(text),
                      "label fragment"))
        removed.append({"text": tail.strip(), "kind": "label fragment"})
        cleaned, index = recut()

    # the stub of a label the extraction copied halfway (`… - Creativity and
    # innov`): removed wherever it sits, because the print never sets it as a word
    # and a label does — the record's own row has no such word, so the record's own
    # truncations are left alone
    for one, two, token in orphan_fragment_spans(cleaned, items, row,
                                                 printed_words(pdf)):
        spans.append((index[one], index[two - 1] + 1, "label fragment"))
        removed.append({"text": token, "kind": "label fragment"})
    if spans:
        cleaned, index = recut()

    # `tidy` only re-spaces what is left, so the spanned text has to read the
    # same as the survivor once punctuation and spacing are folded away
    note = "" if blob(cut_spans(text, spans)[0]) == blob(cleaned) else "unattributable"
    return tidy(cleaned), removed, kept, note


# --------------------------------------------------------------------------- #
# the three plans
# --------------------------------------------------------------------------- #

def db_path(subject: str, grade: str) -> Path:
    return REFERENCE / f"{subject}_{grade}_curriculum_db_clean.json"


def keyword_value(subject: str, grade: str) -> str:
    return f"{subject}, {grade.lower()}, {BAND[grade]}"


def keywords_plan() -> list[dict]:
    plan = []
    for subject, (_pdf, grades) in SUBJECTS.items():
        for grade in grades:
            path = db_path(subject, grade)
            data = json.loads(path.read_text())
            empty = [k for k, v in data.items() if not (v.get("keywords") or "").strip()]
            if empty:
                plan.append({"file": path.name, "value": keyword_value(subject, grade),
                             "records": empty})
    return plan


def drift_plan(in_scope: set[str]) -> list[dict]:
    """Empty keywords in the reference copies of subjects audited elsewhere.

    These files are not this script's subject-grades — the records in them do not
    match the curriculum copies' (they are stale extractions) — but the field's
    convention is not in doubt: one `subject, grade, level` tag per file, the tag
    the curriculum copy of the same name already carries.  The value is taken from
    that copy, never invented, and only when the copy agrees with itself.
    """
    plan = []
    for path in sorted(REFERENCE.glob("*_curriculum_db_clean.json")):
        if path.name in in_scope:
            continue                     # the eight subject-grades above own these
        data = json.loads(path.read_text())
        empty = [k for k, v in data.items()
                 if isinstance(v, dict) and not (v.get("keywords") or "").strip()]
        if not empty:
            continue
        twin = CURRICULUM / path.name
        values = {(v.get("keywords") or "").strip()
                  for v in json.loads(twin.read_text()).values()} if twin.exists() else set()
        values.discard("")
        entry = {"file": path.name, "records": empty}
        if len(values) == 1:
            entry.update({"value": values.pop(), "source": twin.name})
        else:
            entry.update({"value": "", "source": "",
                          "note": "no curriculum copy to take the tag from"
                                  if not values else
                                  "the curriculum copy's tags disagree"})
        plan.append(entry)
    return plan


def ind_desc_plan(pdf: str, subject: str, grade: str,
                  items, cache: dict) -> list[dict]:
    data = json.loads(db_path(subject, grade).read_text())
    plan = []
    for code, rec in data.items():
        text = (rec.get("ind_desc") or "").strip()
        if not text:
            continue
        pages = pages_of(pdf, code)
        page = pages[0] if pages else None
        # the block headings the print centres over the table (`STRAND 4: Les
        # activités`, `INDICATOR AND EXEMPLARS`) sit inside the indicator column's x
        # band, so they are not found by the side-column reading — but they are the
        # table's furniture all the same, and the row they were read into ends there
        headings = [(line, blob(line)) for p in pages for _y, line in ind_lines(pdf, p)
                    if BLOCK_HEADING.match(line)]
        extra = items + [i for p in pages for i in side_items(pdf, p)]
        cleaned, removed, kept, note = plan_ind_desc(pdf, code, text, extra,
                                                     headings, pages, cache)
        truncated: list[str] = []
        where = note or (verify(pdf, code, page, cleaned, truncated) if cleaned
                         else "emptied")
        if cleaned == text:
            # nothing to clean: worth reporting only when the print does not back
            # the record at all — that is the extraction's own defect, not furniture
            if where != "unverified":
                continue
            where = "differs"
        plan.append({"file": db_path(subject, grade).name, "code": code, "page": page,
                     "before": text, "after": cleaned, "removed": removed, "kept": kept,
                     "truncated": sorted(set(truncated)), "where": where})
    return plan


def cs_band(pdf: str, page: int) -> tuple[float, float]:
    """(lo, hi) x band of the content-standard column of `page`."""
    rules = [x for x in page_rules(pdf, page) if 60 <= x <= 760]
    if len(rules) >= 2 and 60 <= rules[0] <= 160 and rules[1] - rules[0] >= 50:
        return rules[0] + 1, rules[1] - 1
    return CS_BAND[pdf]


def cs_candidates(pdf: str) -> dict[str, list[tuple[int, str]]]:
    """printed code -> [(page, sentence)] from the content-standard column.

    The front matter's scope-and-sequence pages list the sub-strand titles in the
    same column and shape (`K1.3.2 Our cultural and family values`), so the scan
    starts at the first page whose column carries the table's own heading.
    """
    start = next((p for p in range(npages(pdf))
                  if any(t.lower().startswith("content standard")
                         for _y, t in page_lines(pdf, p, *cs_band(pdf, p)))), 0)
    out: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for page in range(start, npages(pdf)):
        gl = page_lines(pdf, page, *cs_band(pdf, page))
        i = 0
        while i < len(gl):
            text = gl[i][1].strip()
            if not re.match(r"^[BK]\s*\d", text):
                i += 1
                continue
            head, j = text, i
            if not re.search(r"[A-Za-z]", text) and i + 1 < len(gl) \
                    and re.match(r"^\s*\d", gl[i + 1][1]):
                head, j = f"{text} {gl[i + 1][1]}", i + 1      # code split over lines
            m = re.match(r"^\s*([BK][\d\s.]*[\d])", head)
            if not m:
                i += 1
                continue
            code = re.sub(r"\s+", "", m.group(1))
            buf, k = [head], j + 1
            while k < len(gl):
                nxt = gl[k][1].strip()
                if re.match(r"^[BK]\s*\d", nxt) or nxt.lower().rstrip(":") in HEADINGS \
                        or nxt.upper().startswith("SUB -"):
                    break
                buf.append(nxt)
                k += 1
                if nxt.endswith(".") or len(buf) > 16:
                    break
            sentence = tidy(strip_code_prefix(" ".join(buf)))
            sentence = dekerning(sentence, page_words(pdf, page))
            if len(blob(sentence)) > 15:
                out[blob(code)].append((page + 1, sentence))
            i = max(k, i + 1)
    return out


def print_cell(cells: dict, cs_code: str):
    """The print's readings of this standard's cell.

    A standard's code is the row's own (`K1.3.1.1`) while the cell may be numbered
    one level shorter (`K2.1.3`), so the lookup prefers the code itself and then the
    code it sits under.
    """
    b = blob(cs_code)
    if b in cells:
        return cells[b]
    mine = comps(cs_code)
    for n in range(len(mine) - 1, 2, -1):
        key = blob("".join(mine[:n]))
        if key in cells:
            return cells[key]
    return []


def best_cell(cands: list[tuple[int, str]]) -> tuple[int, str]:
    """One sentence out of the pages that print it.

    A cell is re-set on every page of its block and the pages disagree about both
    the wording and the word-splitting (`per sonal` against `personal`), so the
    fullest reading wins, then the one with the fewest split words, then the one
    the print set in the fewest pieces.
    """
    def rank(c):
        text = c[1]
        split = sum(1 for w in text.split() if len(blob(w)) <= 2)
        return (-len(blob(text)), split, len(text.split()), c[0])

    return min(cands, key=rank)


def cs_desc_plan(pdf: str) -> list[dict]:
    """Every kindergarten content standard, against the print's own sentence.

    The field holds one thing: the sentence the print sets in the standard's own
    column.  So the database's value is measured against the print's sentence —
    with the print's word-splitting folded away — and kept, trimmed, completed or
    reported:

      filled     the record holds nothing; the print's sentence goes in
      unchanged  the record already holds a reading of that sentence
      trimmed    it holds a reading and then text from the cell beside it
      completed  it holds a truncated reading of that sentence
      displaced  it holds indicator-column text; the print's sentence goes in and
                 the displaced value is kept in the artifact
      differs    it holds something else; reported only, never replaced
    """
    cells = cs_candidates(pdf)
    by_code: dict[str, list[dict]] = defaultdict(list)
    for grade in SUBJECTS["kindergarten"][1]:
        path = db_path("kindergarten", grade)
        for code, rec in json.loads(path.read_text()).items():
            by_code[rec["cs_code"]].append({"file": path.name, "code": code, "rec": rec})
    plan = []
    for cs_code, records in sorted(by_code.items()):
        found = print_cell(cells, cs_code)
        entry = {"cs_code": cs_code, "records": [r["code"] for r in records],
                 "files": sorted({r["file"] for r in records}), "changes": []}
        if not found:
            entry["action"] = "no-print-cell"
            entry["note"] = ("the content-standard cell is blank in the print "
                             "(the record keeps what it has)")
            plan.append(entry)
            continue
        page, cell = best_cell(found)
        readings = sorted({c[1] for c in found}, key=lambda t: -len(blob(t)))
        entry.update({"page": page, "cell": cell,
                      "printed_on": sorted({p for p, _t in found})})
        actions = Counter()
        for r in records:
            current = (r["rec"].get("cs_desc") or "").strip()
            hb = blob(current)
            row = row_text_all(pdf, r["code"])
            action, after = "differs", current
            trimmed, trimmed_ok = strip_tail_junk(current)
            if not current:
                action, after = "filled", cell
            elif hb == blob(cell) or hb in {blob(t) for t in readings}:
                action, after = "unchanged", current
            elif trimmed_ok and (blob(trimmed) == blob(cell)
                                 or blob(trimmed) in {blob(t) for t in readings}):
                # the sentence, and then the heading of the column beside it
                action, after = "trimmed", trimmed
            elif similar(hb, blob(cell)):
                action, after = "unchanged", current     # the print's own typo
            else:
                # the database's own reading of this sentence, when it carries one
                pick = next((t for t in readings
                             if blob(t) and hb.startswith(blob(t)) and len(blob(t)) < len(hb)),
                            None)
                if pick is not None:
                    piece, rest = cut_at_blob(current, len(blob(pick)))
                    rest, cut_ok = rest.strip(), False
                    if not blob(rest):
                        cut_ok = True
                    elif JUNK.search(rest) or len(blob(rest)) < 40:
                        cut_ok = True          # the cell next door, or its beginning
                    elif blob(rest) in blob(row) \
                            or blob(rest) in blob(document_text(pdf)):
                        cut_ok = True          # it is the indicator column's text
                    # only cut where the print ends a word, never inside one
                    edge = current[len(piece):len(piece) + 1]
                    if cut_ok and not (edge and edge.isalnum()):
                        after = piece.strip(" -;:,")
                        if rest[:1] in (".", "!", "?") and after[-1:] not in (".", "!", "?"):
                            after += rest[0]       # the sentence's own full stop
                        action = "trimmed"
                elif blob(cell).startswith(hb) and len(blob(cell)) - len(hb) >= 10:
                    # a truncated reading of the very sentence: the print has more
                    action, after = "completed", cell
                elif hb[:80] and hb[:80] in blob(document_text(pdf)):
                    # the field holds the *indicator* column's text — a misplaced
                    # extraction, not a reading of the standard.  The print's own
                    # sentence goes in and the displaced value is kept in the
                    # artifact for the trail
                    action, after = "displaced", cell
            actions[action] += 1
            entry["changes"].append({"file": r["file"], "code": r["code"],
                                     "action": action, "before": current, "after": after})
        entry["action"] = "+".join(sorted(a for a in actions if a != "unchanged")) \
            or "unchanged"
        plan.append(entry)
    return plan


# --------------------------------------------------------------------------- #
# apply + audit trail
# --------------------------------------------------------------------------- #

def apply(plan: dict) -> dict:
    """Write the changes the print backs; leave every record it does not."""
    applied = {"keywords": 0, "keywords_drift": 0, "ind_desc": 0, "cs_desc": 0,
               "skipped": []}
    dirty: dict[str, dict] = {}

    def db(name: str) -> dict:
        if name not in dirty:
            dirty[name] = json.loads((REFERENCE / name).read_text())
        return dirty[name]

    for entry in plan["keywords"]:
        data = db(entry["file"])
        for code in entry["records"]:
            if not (data[code].get("keywords") or "").strip():
                data[code]["keywords"] = entry["value"]
                applied["keywords"] += 1

    for entry in plan["drift"]:
        if not entry.get("value"):
            continue
        data = db(entry["file"])
        for code in entry["records"]:
            if not (data[code].get("keywords") or "").strip():
                data[code]["keywords"] = entry["value"]
                applied["keywords_drift"] += 1

    for entries in plan["ind_desc"].values():
        for entry in entries:
            if entry["where"] in ("unverified", "differs") or not entry["after"] \
                    or entry["after"] == entry["before"]:
                applied["skipped"].append([entry["file"], entry["code"], entry["where"]])
                continue
            db(entry["file"])[entry["code"]]["ind_desc"] = entry["after"]
            applied["ind_desc"] += 1

    for entry in plan["cs_desc"]:
        for change in entry["changes"]:
            if change["action"] in ("unchanged", "differs") \
                    or change["after"] == change["before"]:
                continue          # `differs` is the print disagreeing: reported only
            db(change["file"])[change["code"]]["cs_desc"] = change["after"]
            applied["cs_desc"] += 1

    for name, data in dirty.items():
        (REFERENCE / name).write_text(
            json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    return applied


def _key(entry: dict) -> str:
    return json.dumps(entry, ensure_ascii=False, sort_keys=True)


def _merge_counts(old: dict, new: dict) -> dict:
    return {k: max(old.get(k, 0), new.get(k, 0)) for k in set(old) | set(new)}


def artifact(plan: dict, applied: dict | None, previous: dict | None = None) -> dict:
    """The trail of what was cleaned, merged with what earlier runs wrote.

    A run with nothing left to do must not erase the record of the run that did
    the work, so the per-record trail is accumulated, not replaced.
    """
    old_ind = (previous or {}).get("ind_desc", {})
    ind = {}
    for key, entries in plan["ind_desc"].items():
        writable = [e for e in entries
                    if e["where"] not in ("unverified", "differs") and e["after"]]
        old = old_ind.get(key, {})
        changes, seen = [], set()
        for e in writable:
            entry = {"code": e["code"], "page": e["page"], "where": e["where"],
                     "removed": sorted({i["text"] for i in e["removed"]}),
                     "kinds": dict(Counter(i["kind"] for i in e["removed"])),
                     "kept": sorted(set(e["kept"])),
                     "truncated": e.get("truncated", []),
                     "before": e["before"], "after": e["after"]}
            changes.append(entry)
            seen.add(_key(entry))
        for entry in old.get("changes", []):
            if _key(entry) not in seen:
                changes.append(entry)
        ind[key] = {
            "records": max(len(entries), old.get("records", 0)),
            "written": len(changes),
            "where": _merge_counts(old.get("where", {}),
                                   dict(Counter(e["where"] for e in entries))),
            "removals": _merge_counts(
                old.get("removals", {}),
                dict(Counter(i["kind"] for e in writable for i in e["removed"]))),
            "unverified": [{"code": e["code"], "page": e["page"],
                            "print_says": (row_text(cfg_pdf(key), e["page"], e["code"])
                                           if e["page"] is not None else "")[:200],
                            "before": e["before"], "after": e["after"]}
                           for e in entries if e["where"] == "unverified"],
            "emptied": [{"code": e["code"], "before": e["before"]}
                        for e in entries if not e["after"]],
            "changes": changes,
        }

    old_cs = {e["cs_code"]: e for e in (previous or {}).get("cs_desc", [])}
    cs = []
    for entry in plan["cs_desc"]:
        old = old_cs.get(entry["cs_code"], {})
        changes, seen = [], set()
        for c in entry["changes"]:
            changes.append(c)
            seen.add(_key(c))
        for c in old.get("changes", []):
            if _key(c) not in seen:
                changes.append(c)
        out = {k: entry[k] for k in ("cs_code", "files", "note", "page", "cell")
               if k in entry}
        out["changes"] = changes
        actions = sorted({c["action"] for c in changes} - {"unchanged"})
        out["action"] = "+".join(actions) if actions else old.get("action", "unchanged")
        cs.append(out)

    keywords = plan["keywords"] or (previous or {}).get("keywords", [])
    history = (previous or {}).get("history", [])
    if applied and any(v for k, v in applied.items() if k != "skipped"):
        history = history + [{k: v for k, v in applied.items() if k != "skipped"}]
    return {
        "generated_by": "scripts/fix_reference_text.py",
        "rule": {
            "keywords": "an empty keywords field gets the file's derived subject/"
                        "grade/band tag, the tag the audited subject-grades carry",
            "drift": "the same tag in the reference copies of subjects audited "
                     "elsewhere (`data/curriculum/`), whose records are stale "
                     "extractions: the value is read off the audited copy of the "
                     "same name, never invented, and reported separately",
            "ind_desc": "delete only what the print sets outside the record's own row "
                        "of the indicator column — the footer, the column headings "
                        "(even those the print centres inside the column's own x "
                        "band), the competence labels, the reference codes, the row "
                        "markers, a label the extraction copied only halfway, and "
                        "text the print sets in another record's row; the survivor is "
                        "read back against the print and the record is left alone if "
                        "it does not appear there",
            "cs_desc": "the sentence printed in the content-standard column of the "
                       "standard's own block, as the fullest of that column's "
                       "readings has it: a record that holds none is filled, one "
                       "that stops short is completed, one that runs on into the "
                       "next column is trimmed, and one that holds indicator-column "
                       "text is replaced — the displaced value kept in `changes`.  "
                       "`K1.3.2.1`'s cell is blank in the print, so its five records "
                       "are left as they stand",
            "strength": "`row` and `page` mean the print sets the survivor verbatim; "
                        "`row-order`, `page-order` and `document-order` mean every "
                        "word of it is printed, in the order the record carries them "
                        "(the extraction braided the columns, so its reading skips) "
                        "— reported per record so the weaker readings are visible",
        },
        "vocabulary": plan["evidence"] or (previous or {}).get("vocabulary", {}),
        "keywords": keywords,
        "ind_desc": ind,
        "cs_desc": cs,
        "drift": plan["drift"] or (previous or {}).get("drift", []),
        "applied": applied,
        "history": history,
    }


def cfg_pdf(key: str) -> str:
    subject, _sep, grade = key.rpartition("_")
    return SUBJECTS[subject][0]


# --------------------------------------------------------------------------- #
# what is still furniture after the plan (the close-out check)
# --------------------------------------------------------------------------- #

RESIDUAL_WORDS = tuple(
    [h for h in HEADINGS if " " in h]                          # the table's headings
    + [c for c in CC_LABELS if " " in c])                      # whole competence labels
LEFT = re.compile(r"(?<![A-Za-z])(?:" + "|".join(
    re.escape(w) for w in RESIDUAL_WORDS) + r"|" + FOOTER.pattern + r"|"
    + CC_TAG.pattern + r")(?![A-Za-z])", re.I)


def residuals(key: str) -> dict:
    """Records whose text fields still carry something from the side columns."""
    subject, _sep, grade = key.rpartition("_")
    data = json.loads(db_path(subject, grade).read_text())
    hits = []
    for code, rec in data.items():
        text = rec.get("ind_desc") or ""
        m = LEFT.search(text)
        if m:
            hits.append({"code": code, "found": m.group(),
                         "where": text[max(0, m.start() - 40):m.end() + 40]})
    return {"grade": key, "records": len(data), "with_furniture": len(hits),
            "examples": hits[:5]}


def cs_closeout(pdf: str) -> dict:
    """How the kindergarten field stands against the print's own cell, as it is now.

    The close-out for `cs_desc`: every record's value is either the sentence the
    print sets in the standard's column, or empty where that cell is blank.  Read
    off the files as they stand, so after `--apply` it is the new state.
    """
    cells = cs_candidates(pdf)
    readings: dict[str, set[str]] = defaultdict(set)
    for grade in SUBJECTS["kindergarten"][1]:
        for rec in json.loads(db_path("kindergarten", grade).read_text()).values():
            cs = rec["cs_code"]
            if cs not in readings:
                readings[cs] = {blob(t) for _p, t in (print_cell(cells, cs) or [])}
    counts: Counter = Counter()
    odd: list[dict] = []
    for grade in SUBJECTS["kindergarten"][1]:
        for code, rec in json.loads(db_path("kindergarten", grade).read_text()).items():
            cur, wants = blob(rec.get("cs_desc") or ""), readings[rec["cs_code"]]
            if not wants:
                counts["print cell blank"] += 1
            elif not cur:
                counts["empty"] += 1
                odd.append({"code": code, "note": "empty", "print_says": sorted(wants)[:1]})
            elif cur in wants:
                counts["the print's own sentence"] += 1
            else:
                counts["not the print's cell"] += 1
                odd.append({"code": code, "note": "differs",
                            "value": (rec.get("cs_desc") or "")[:120]})
    return {"counts": dict(counts), "examples": odd[:5]}


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="write the changes (default: report only)")
    args = ap.parse_args()

    print("fix_reference_text — clean the reference-only text fields")
    print("=" * 68)

    plan: dict = {"keywords": [], "ind_desc": {}, "cs_desc": [], "drift": [],
                  "evidence": {}}

    kw = keywords_plan()
    print(f"\nkeywords: {len(kw)} file(s), "
          f"{sum(len(k['records']) for k in kw)} record(s)")
    for entry in kw:
        print(f"  {entry['file']:48s} {len(entry['records']):4d} -> {entry['value']!r}")
    plan["keywords"] = kw

    # Reference copies of audited subjects carry empty keywords too, but their
    # records are stale extractions: the tag is read off the audited copy of the
    # same name and reported apart from the eight subject-grades above.
    plan["drift"] = drift_plan({e["file"] for e in kw})
    for entry in plan["drift"]:
        print(f"  {entry['file']:48s} {len(entry['records']):4d} -> "
              + (f"{entry['value']!r} (from {entry['source']})"
                 if entry.get("value") else f"-- {entry.get('note')}"))

    for subject, (pdf, grades) in SUBJECTS.items():
        haystack = blob("".join(
            json.dumps(v, ensure_ascii=False) for grade in grades
            for v in json.loads(db_path(subject, grade).read_text()).values()))
        items = vocabulary(subject)
        used = [e for e in side_vocabulary(pdf, subject, haystack) if e["in_the_data"]]
        print(f"\n{subject}: {len(used)}/{len(items)} pieces of furniture are both "
              f"printed outside the indicator column and present in the data")
        for e in used:
            print(f"    {e['item']!r:52s} printed on {e['printed_on_pages']:3d} page(s)")
        plan["evidence"][subject] = used
        cache: dict = {}
        for grade in grades:
            key = f"{subject}_{grade}"
            plan["ind_desc"][key] = ind_desc_plan(pdf, subject, grade, items, cache)

    print("\nind_desc (records that change, and how the print backs them)")
    weakest: list[dict] = []
    for key, entries in plan["ind_desc"].items():
        if not entries:
            continue
        where = Counter(e["where"] for e in entries)
        kinds = Counter(i["kind"] for e in entries for i in e["removed"])
        print(f"  {key:24s} {len(entries):4d} record(s)  {dict(where)}")
        if kinds:
            print("          " + ", ".join(f"{n}x {k}" for k, n in kinds.most_common()))
        for e in entries:
            if e["where"] in ("unverified", "unattributable"):
                print(f"          ! {e['code']} (p{e['page']}): {e['where']} — the "
                      f"print's row says "
                      f"{compact(row_text(cfg_pdf(key), e['page'], e['code']))[:60]!r}")
            elif e["where"].endswith("order"):
                weakest.append({"file": e["file"], "code": e["code"],
                                "where": e["where"], "after": e["after"],
                                "truncated": e.get("truncated", [])})
    if weakest:
        print(f"\n  backed word-by-word rather than verbatim ({len(weakest)}):")
        for e in weakest:
            note = ("  [truncated: " + ", ".join(e["truncated"]) + "]"
                    if e["truncated"] else "")
            print(f"    {e['file'][:28]:28s} {e['code']:14s} {e['where']:16s} "
                  f"{e['after'][:60]!r}{note}")

    cs_entries = cs_desc_plan(SUBJECTS["kindergarten"][0])
    plan["cs_desc"] = cs_entries
    print("\nkindergarten cs_desc (the print's sentence in the standard's own column)")
    for e in cs_entries:
        if e["action"] == "no-print-cell":
            print(f"  {e['cs_code']:12s} -- {e['note']} ({len(e['records'])} record(s))")
            continue
        acts = Counter(c["action"] for c in e["changes"])
        if set(acts) <= {"unchanged"}:
            continue
        print(f"  {e['cs_code']:12s} p{str(e['page']):<4s} "
              f"{'+'.join(f'{k}:{v}' for k, v in sorted(acts.items())):22s} "
              f"{e['cell'][:60]!r}")
    print(f"  {sum(1 for e in cs_entries if e['action'] == 'no-print-cell')} standard(s) "
          f"blank in the print, {len(cs_entries)} in all")


    applied = None
    if args.apply:
        applied = apply(plan)
        print(f"\napplied: {applied['keywords']} keywords (+{applied['keywords_drift']}"
              f" in the drifted copies), {applied['ind_desc']} ind_desc, "
              f"{applied['cs_desc']} cs_desc; {len(applied['skipped'])} record(s) left "
              f"alone (not backed by the print)")
        previous = json.loads(ARTIFACT.read_text()) if ARTIFACT.exists() else None
        ARTIFACT.write_text(json.dumps(artifact(plan, applied, previous), indent=1,
                                       ensure_ascii=False) + "\n")
        print(f"wrote {ARTIFACT.relative_to(ROOT)}")

    # the close-out check, read off the files as they stand — after --apply that is
    # the new state, and the point of the run: what the side columns still
    # contribute to a field
    print("\nside-column text left in the fields"
          + ("" if applied else " (nothing written — report only)"))
    for key in plan["ind_desc"]:
        try:
            left = residuals(key)
        except (ValueError, OSError):
            continue
        print(f"  {left['grade']:24s} {left['with_furniture']:3d}/{left['records']} "
              f"record(s) still carry a heading, a competence label or a page footer")
        for ex in left["examples"]:
            print(f"      {ex['code']:14s} {ex['found']!r} … {ex['where']!r}")

    print("\nkindergarten cs_desc as it now stands")
    try:
        close = cs_closeout(SUBJECTS["kindergarten"][0])
    except (ValueError, OSError) as exc:                     # pragma: no cover
        print(f"  (not read: {exc})")
    else:
        for what, n in sorted(close["counts"].items()):
            print(f"  {n:4d} record(s) — {what}")
        for ex in close["examples"]:
            print(f"      {ex['code']:14s} {ex['note']}: {ex.get('value', '')!r}")

    print("\n(report only; pass --apply to write)" if not args.apply else "\n(applied)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
