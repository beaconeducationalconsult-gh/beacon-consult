#!/usr/bin/env python3
"""Re-derive strand names for the reference-only subjects from their source PDFs.

Why this exists
---------------
`computing`, `french` and `kindergarten` are the subjects that exist only in
`data/reference/`, so they never went through the extraction pass that produced
the rest. Their indicator codes and descriptions are correct, but the *labels*
on the hierarchy are not:

    computing B4    strand: "Strand 1"          ← placeholder, real name dropped
                    sub_strand: "Sub-strand 1.1"
    french B4       strand: "Saluer et prendre congé"   ← a SUB-strand name, one
                    sub_strand: "Sub-strand 1.1"            level too low
    kindergarten    strand: "Strand 1"          ← placeholder; the real name is
                    sub_strand: "Sub-strand 1.1"  the theme, e.g. ALL ABOUT ME

The PDFs carry both headings on their own lines:

    STRAND 1: L'IDENTITÉ
    Sub–Strand 1 : Saluer et prendre congé

so the correct labels are recoverable by reading the heading in effect at the
position of each indicator code.

What it writes
--------------
`strand` becomes ``"{n}. {NAME}"`` and `sub_strand` becomes
``"Sub-strand {grade}.{n}.{ss}"`` — the convention every audited subject already
uses (see any `data/curriculum/*_B4_curriculum_db_clean.json`). Matching that
convention is deliberate: the browse tree should not look different depending on
which copy a subject happens to come from.

The real sub-strand names are *not* written, because no other subject carries
them. They are in the PDFs if the app ever wants to display them.

Requires: pypdf   (pip install pypdf)

Usage
-----
    python3 scripts/fix_reference_structure.py            # report only
    python3 scripts/fix_reference_structure.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from _paths import REFERENCE, SOURCES  # noqa: E402

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    sys.exit("pypdf is required:  pip install pypdf")

# subject id -> source PDF, and the code prefix -> grade used in the file name.
# Kindergarten is the odd one out: its codes are K1./K2. while the files are
# kindergarten_KG1_/KG2_.
SUBJECTS = {
    "computing":    {"pdf": "computing_B4-B6.pdf",
                     "code_to_file": {"B4": "B4", "B5": "B5", "B6": "B6"}},
    "french":       {"pdf": "french_B4-B6.pdf",
                     "code_to_file": {"B4": "B4", "B5": "B5", "B6": "B6"}},
    "kindergarten": {"pdf": "kindergarten_KG1-KG2.pdf",
                     "code_to_file": {"K1": "KG1", "K2": "KG2"}},
}

# "STRAND 1: NAME" / "STRAND3: NAME" — must be at the start of a line.
STRAND_RE = re.compile(r"^\s*STRAND\s*(\d+)\s*[::]\s*(.+?)\s*$", re.I)
# "Sub–Strand 1 : NAME" — the dash may be hyphen, en dash or em dash.
SUB_RE = re.compile(r"^\s*SUB[\s\u2010-\u2015-]*STRAND\s*(\d+)\s*[::]\s*(.*?)\s*$", re.I)
# A dot leader means we are looking at the table of contents, not a heading.
TOC_RE = re.compile(r"\.{4,}")
# A trailing class tag on a heading: "STRAND 1: ALL ABOUT ME (K1/K2)".
GRADE_TAG_RE = re.compile(r"\s*\(\s*[Kk]\s?\d\s*/\s*[Kk]\s?\d\s*\)\s*$")
# A 5-part code that DEFINES an indicator, so it must open a line (a leading
# bullet is allowed). Anchoring matters: exemplars cross-reference other codes
# mid-sentence ("follow the procedure as in K2.1.1.1.5"), and counting those
# against whichever heading happens to be in effect invents strand names.
CODE_RE = re.compile(r"^\s*[\uf0b7\u2022\u25cf-]?\s*"
                     r"([BK])\s?(\d)\s*[.,]\s*(\d+)\s*[.,]\s*(\d+)\s*[.,]\s*(\d+)\s*[.,]\s*(\d+)",
                     re.I)


def clean_name(raw: str) -> str:
    """Trim a heading to its name.

    PDF text extraction sometimes runs the next heading onto the same line
    ("INTERNET AND SOCIAL MEDIA SUB-STRAND 1: NETWORK OVERVIEW") and sometimes
    carries a class tag ("ALL ABOUT ME (K1/K2)"), so cut at the first embedded
    heading, drop the tag and collapse whitespace.
    """
    name = re.split(r"\s+SUB[\s\u2010-\u2015-]*STRAND\b", raw, flags=re.I)[0]
    name = re.split(r"\s+STRAND\b", name, flags=re.I)[0]
    name = GRADE_TAG_RE.sub("", name)
    return re.sub(r"\s+", " ", name).strip(" .:;")


def strand_names(subject: str, pdf_path: Path) -> tuple[dict[tuple[str, int], set[str]], list[str]]:
    """(code prefix, strand number) -> every name seen for it, plus notes.

    Three rules keep this honest, because the PDFs are inconsistent:

    * a code only counts where it OPENS a line — exemplars cross-reference other
      codes mid-sentence ("follow the procedure as in K2.1.1.1.5"), and those
      must not be read as definitions;
    * the FIRST time a code opens a line is where it is defined, so later
      mentions (including wrapped ones) are ignored;
    * a heading printed as a sub-strand is read as a strand heading only when
      BOTH of these hold: its number agrees with the codes underneath, and no
      strand heading for that number has been seen yet. That is what separates
      the KG print's "SUB STRAND 7: MY GLOBAL COMMUNITY" (codes are K1.7.1.x,
      and no strand 7 heading precedes it) from a genuine "SUB STRAND 7:
      GARDENING" (codes are K1.6.7.x) and from ordinary sub-strand 1 headings
      (whose strand already has a name).
    """
    reader = PdfReader(str(pdf_path))
    found: dict[tuple[str, int], set[str]] = defaultdict(set)
    notes: list[str] = []
    valid = set(SUBJECTS[subject]["code_to_file"])
    seen: set[str] = set()
    named: set[int] = set()          # strand numbers that already have a heading
    current: str | None = None
    pending: tuple[int, str] | None = None

    for page in reader.pages:
        for line in (page.extract_text() or "").split("\n"):
            if TOC_RE.search(line):
                continue
            m = STRAND_RE.match(line)
            if m:
                name = clean_name(m.group(2))
                if len(name) > 2:
                    current = name
                    named.add(int(m.group(1)))
                pending = None
                continue
            sub = SUB_RE.match(line)
            if sub:
                name = clean_name(sub.group(2))
                pending = (int(sub.group(1)), name) if len(name) > 2 else None
                continue

            hit = CODE_RE.match(line)
            if not hit:
                continue
            grade = f"{hit.group(1)}{hit.group(2)}".upper()
            # Grade-qualified: B4.1.1.1.1, B5.1.1.1.1 and B6.1.1.1.1 share a
            # tail, and keying `seen` on the tail alone lets one grade's
            # definition consume another grade's.
            code = f"{grade}." + ".".join(hit.groups()[2:6])
            strand_num = int(hit.group(3))
            if grade not in valid or code in seen:
                continue
            promote = bool(pending and pending[0] == strand_num
                           and strand_num not in named)
            if current is None and not promote:
                # Nothing to attribute it to yet (front matter, a table of
                # contents). Don't consume its first occurrence.
                pending = None
                continue
            if promote:
                current = pending[1]
                named.add(strand_num)
                notes.append(f"{grade}.{strand_num}: read sub-strand heading "
                             f"{pending[1]!r} as the strand heading (its codes are "
                             f"{grade}.{strand_num}.x, and no strand "
                             f"{strand_num} heading precedes it)")
            pending = None
            seen.add(code)
            found[(grade, strand_num)].add(current)
    return found, notes


def indicator_texts(pdf_path: Path) -> dict[str, list[str]]:
    """code -> candidate texts for it, in document order.

    Used only to replace descriptions the extractor left as stubs. The rule
    matches how the healthy entries in these files read: the text that follows
    the code, with the exemplar (teaching guidance) left out.

    Every occurrence is kept rather than just the first, because a code is also
    printed in the front matter as a format example ("K1.1.1. 1.1" in Figure 1),
    where it is followed by the figure's labels rather than by its own text.
    """
    reader = PdfReader(str(pdf_path))
    out: dict[str, list[str]] = {}
    code: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if code:
            text = re.sub(r"\s+", " ", " ".join(buf)).strip()
            # A definition always has text on the code's own line; the figure in
            # the front matter has the code alone.
            if text and text not in out.get(code, []):
                out.setdefault(code, []).append(text)

    for page in reader.pages:
        for line in (page.extract_text() or "").split("\n"):
            if "Exemplars:" in line:
                head = line.split("Exemplars:")[0].strip()
                if code and head:
                    buf.append(head)
                flush()
                code, buf = None, []
                continue
            hit = CODE_RE.match(line)
            if hit:
                grade = f"{hit.group(1)}{hit.group(2)}".upper()
                flush()
                code = f"{grade}." + ".".join(hit.groups()[2:6])
                buf = [line[hit.end():].strip()]
                if not buf[0]:
                    code = None      # not a definition line
                continue
            if code is not None and line.strip():
                buf.append(line.strip())
    flush()
    return out


def is_stub(text: str) -> bool:
    """True for the extractor's placeholder, e.g. 'Kindergarten Learning
    Indicator K1.1.1.1.1' — a restatement of the code, not content."""
    return bool(re.match(r"^(?:Kindergarten\s+)?Learning\s+Indicator\s*[: ]?\s*[BK]?\d\.[\d.]*$",
                         (text or "").strip(), re.I))


def plausibly_clean(text: str) -> bool:
    """Reject extractions that swallowed a running head, a page number or the
    copyright line, rather than accepting whatever the block scan produced."""
    if len(text) < 20 or len(text) > 600:
        return False
    bad = ("© NaCCA", "NaCCA, Ministry", "STRAND", "Exemplars", "Content Standard")
    if any(b.lower() in text.lower() for b in bad):
        return False
    return not re.fullmatch(r"[\d\s.,:;-]*", text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the changes (default: report only)")
    args = ap.parse_args()

    problems = 0
    for subject, cfg in SUBJECTS.items():
        pdf = SOURCES / cfg["pdf"]
        if not pdf.exists():
            print(f"  {subject}: source PDF missing at {pdf.relative_to(ROOT)}")
            problems += 1
            continue

        names, notes = strand_names(subject, pdf)
        print(f"=== {subject}  ({pdf.name}) ===")

        for note in notes:
            print(f"  note: {note}")

        # A strand that resolves to two different names means the heading scan
        # is not trustworthy; refuse rather than write a guess.
        ambiguous = {k: v for k, v in names.items() if len(v) > 1}
        for k, v in sorted(ambiguous.items()):
            print(f"  AMBIGUOUS {k}: {sorted(v)}")
            problems += 1

        for code_grade, file_grade in cfg["code_to_file"].items():
            path = REFERENCE / f"{subject}_{file_grade}_curriculum_db_clean.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())

            # Every strand in the file must have exactly one name from the PDF;
            # a strand with none means the scan missed a heading form.
            strand_nums = sorted({int(c.split(".")[1]) for c in data if len(c.split(".")) >= 4})
            unnamed = [n for n in strand_nums if not names.get((code_grade, n))]
            if unnamed:
                print(f"  {code_grade}: NO NAME FOUND for strand(s) {unnamed}")
                problems += 1

            changes = []
            for code, row in data.items():
                seg = code.split(".")
                if len(seg) < 4:
                    continue
                strand_num, sub_num = int(seg[1]), int(seg[2])
                candidates = names.get((code_grade, strand_num))
                if not candidates or len(candidates) != 1:
                    continue
                want_strand = f"{strand_num}. {next(iter(candidates))}"
                # "Sub-strand B4.1.1" / "Sub-strand K1.1.1", the form every
                # audited subject uses.
                want_sub = f"Sub-strand {code_grade}.{strand_num}.{sub_num}"
                if row.get("strand") != want_strand or row.get("sub_strand") != want_sub:
                    changes.append((code, row.get("strand"), want_strand,
                                    row.get("sub_strand"), want_sub))

            print(f"  {code_grade}: {len(changes)}/{len(data)} indicators would change")
            for code, old_s, new_s, old_ss, new_ss in changes[:2]:
                print(f"      {code}")
                print(f"        strand     {old_s!r} -> {new_s!r}")
                print(f"        sub-strand {old_ss!r} -> {new_ss!r}")

            # Second step: replace descriptions that only restate the code.
            texts = indicator_texts(pdf)
            filled = []
            for code, row in data.items():
                if not is_stub(str(row.get("ind_desc") or "")):
                    continue
                candidate = next((x for x in texts.get(code, []) if plausibly_clean(x)), None)
                if candidate:
                    filled.append((code, row["ind_desc"], candidate))
                    row["ind_desc"] = candidate
                else:
                    print(f"      STUB kept (no usable text found in the PDF): {code}")
                    problems += 1
            for code, old, new in filled:
                print(f"      stub filled {code}")
                print(f"        was {old!r}")
                print(f"        now {new[:88] + ('…' if len(new) > 88 else '')!r}")

            if args.apply and (changes or filled):
                for code, _os, ns, _oss, nss in changes:
                    data[code]["strand"] = ns
                    data[code]["sub_strand"] = nss
                path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
                print(f"      wrote {path.relative_to(ROOT)}")

    if problems:
        print(f"\n  {problems} problem(s) — see above")
        return 1
    print("\n  done" + ("" if args.apply else "  (report only; pass --apply to write)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
