#!/usr/bin/env python3
"""Re-derive strand names for the reference-only subjects from their source PDFs.

Why this exists
---------------
`computing` and `french` (plus kindergarten) are the subjects that exist only in
`data/reference/`, so they never went through the extraction pass that produced
the rest. Their indicator codes and descriptions are correct, but the *labels*
on the hierarchy are not:

    computing B4    strand: "Strand 1"          ← placeholder, real name dropped
                    sub_strand: "Sub-strand 1.1"
    french B4       strand: "Saluer et prendre congé"   ← a SUB-strand name, one
                    sub_strand: "Sub-strand 1.1"            level too low

The PDFs carry both headings on their own lines:

    STRAND 1: L'IDENTITÉ
    Sub–Strand 1 : Saluer et prendre congé

so the correct labels are recoverable by reading the heading in effect at the
position of each indicator code.

What it writes
--------------
`strand` becomes ``"{n}. {NAME}"`` and `sub_strand` becomes
``"Sub-strand {grade}{n}.{ss}"`` — the convention every audited subject already
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

# subject id -> source PDF in data/sources/
PDFS = {
    "computing": "computing_B4-B6.pdf",
    "french": "french_B4-B6.pdf",
}
GRADES = ["B4", "B5", "B6"]

# "STRAND 1: NAME" / "STRAND3: NAME" — must be at the start of a line.
STRAND_RE = re.compile(r"^\s*STRAND\s*(\d+)\s*[::]\s*(.+?)\s*$", re.I)
# "Sub–Strand 1 : NAME" — the dash may be hyphen, en dash or em dash.
SUB_RE = re.compile(r"^\s*SUB[\s\u2010-\u2015-]*STRAND\s*(\d+)\s*[::]\s*(.*?)\s*$", re.I)
# A dot leader means we are looking at the table of contents, not a heading.
TOC_RE = re.compile(r"\.{4,}")
CODE_RE = re.compile(r"\b[Bb]\s?([4-6])\s*[.,]\s*(\d+)\s*[.,]\s*(\d+)\s*[.,]\s*(\d+)\s*[.,]\s*(\d+)")


def clean_name(raw: str) -> str:
    """Trim a heading to its name.

    PDF text extraction sometimes runs the next heading onto the same line
    ("INTERNET AND SOCIAL MEDIA SUB-STRAND 1: NETWORK OVERVIEW") and sometimes
    leaves the capitalisation of a running head, so cut at the first embedded
    heading and collapse whitespace.
    """
    name = re.split(r"\s+SUB[\s\u2010-\u2015-]*STRAND\b", raw, flags=re.I)[0]
    name = re.split(r"\s+STRAND\b", name, flags=re.I)[0]
    return re.sub(r"\s+", " ", name).strip(" .:;")


def strand_names(pdf_path: Path) -> dict[tuple[str, int], set[str]]:
    """(grade, strand number) -> every name seen for it, in document order."""
    reader = PdfReader(str(pdf_path))
    found: dict[tuple[str, int], set[str]] = defaultdict(set)
    current: str | None = None

    for page in reader.pages:
        for line in (page.extract_text() or "").split("\n"):
            if TOC_RE.search(line):
                continue
            m = STRAND_RE.match(line)
            if m:
                name = clean_name(m.group(2))
                if len(name) > 2:
                    current = name
                continue
            if current is None:
                continue
            for hit in CODE_RE.finditer(line):
                grade, strand_num = f"B{hit.group(1)}", int(hit.group(2))
                found[(grade, strand_num)].add(current)
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the changes (default: report only)")
    args = ap.parse_args()

    problems = 0
    for subject, pdf_name in PDFS.items():
        pdf = SOURCES / pdf_name
        if not pdf.exists():
            print(f"  {subject}: source PDF missing at {pdf.relative_to(ROOT)}")
            problems += 1
            continue

        names = strand_names(pdf)
        print(f"=== {subject}  ({pdf.name}) ===")

        # A strand that resolves to two different names means the heading scan
        # is not trustworthy; refuse rather than write a guess.
        ambiguous = {k: v for k, v in names.items() if len(v) > 1}
        for k, v in sorted(ambiguous.items()):
            print(f"  AMBIGUOUS {k}: {sorted(v)}")
            problems += 1

        for grade in GRADES:
            path = REFERENCE / f"{subject}_{grade}_curriculum_db_clean.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text())
            changes = []
            for code, row in data.items():
                seg = code.split(".")
                if len(seg) < 4:
                    continue
                strand_num, sub_num = int(seg[1]), int(seg[2])
                candidates = names.get((grade, strand_num))
                if not candidates or len(candidates) != 1:
                    continue
                want_strand = f"{strand_num}. {next(iter(candidates))}"
                # "Sub-strand B4.1.1", the form every audited subject uses.
                want_sub = f"Sub-strand {grade}.{strand_num}.{sub_num}"
                if row.get("strand") != want_strand or row.get("sub_strand") != want_sub:
                    changes.append((code, row.get("strand"), want_strand,
                                    row.get("sub_strand"), want_sub))

            print(f"  {grade}: {len(changes)}/{len(data)} indicators would change")
            for code, old_s, new_s, old_ss, new_ss in changes[:2]:
                print(f"      {code}")
                print(f"        strand     {old_s!r} -> {new_s!r}")
                print(f"        sub-strand {old_ss!r} -> {new_ss!r}")

            if args.apply and changes:
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
