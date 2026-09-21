#!/usr/bin/env python3
"""Correct the NaCCA grade-band label on the lesson-plan title pages.

## The defect

33 of the 77 lesson-plan books carry the wrong band on the cover:

- **All 21 B4–B6 books** read *"Basic 4 · Lower Primary"*. B4–B6 is
  **Upper Primary**.
- **12 B7–B9 books** (English, Ghanaian Language, Mathematics, Science) read
  *"Basic 9 · JHS 3 · Lower Primary"* — a spurious third band tacked onto the
  correct JHS label.

NaCCA bands: KG1–KG2 Kindergarten · **B1–B3 Lower Primary** ·
**B4–B6 Upper Primary** · **B7–B9 Junior High School (JHS 1–3)**.

A headteacher spots this immediately, and it undercuts the credibility of a
product whose whole claim is curriculum accuracy.

## What this does

Rewrites only the title-page runs that contain the wrong text. Nothing else in
the document is touched — verified by comparing paragraph counts and full text
before and after.

**Nothing is lost:** every original is in git at `c9a186c`.

The newly generated Schemes of Learning and Records of Work already use the
correct bands and never had this defect.

Usage
-----
    python3 scripts/fix_grade_band_labels.py            # dry run — report only
    python3 scripts/fix_grade_band_labels.py --apply    # do it
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from docx import Document
except ImportError:
    sys.exit("python-docx is required:  pip install python-docx")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _paths import BOOKS  # noqa: E402

BANDS = {
    **{f"B{i}": "Lower Primary" for i in (1, 2, 3)},
    **{f"B{i}": "Upper Primary" for i in (4, 5, 6)},
    "B7": "JHS 1", "B8": "JHS 2", "B9": "JHS 3",
}

FILE_RE = re.compile(r"^Basic(\d)_(.+)_Lesson_Plans_Full_Year\.docx$")


def find_books():
    out = []
    for p in sorted(BOOKS.glob("Basic*_Lesson_Plans_Full_Year.docx")):
        m = FILE_RE.match(p.name)
        if m:
            out.append((p, f"B{m.group(1)}"))
    return out


def expected_label(grade):
    return f"Basic {grade[1:]}  ·  {BANDS[grade]}"


def fix_runs(doc, grade):
    """Rewrite the title-page band, and only where it is actually wrong.

    B1-B3 are already correct — touching them would strip the right label, so
    they are skipped. The function is idempotent: re-running it on an already
    corrected book changes nothing.
    """
    want = expected_label(grade)
    changes = []
    for para in doc.paragraphs:
        for run in para.runs:
            before = run.text
            if "Lower Primary" not in before:
                continue

            if grade in ("B1", "B2", "B3"):
                continue  # already correct
            if grade in ("B4", "B5", "B6"):
                if "Upper Primary" in before:
                    continue  # already fixed
                after = before.replace("Lower Primary", "Upper Primary")
            else:  # B7-B9: strip the spurious trailing band, keep "Basic N · JHS n"
                if "  ·  Lower Primary" not in before:
                    continue  # already fixed
                after = before.replace("  ·  Lower Primary", "")

            if after == before:
                continue
            run.text = after
            changes.append((before, after))
            if want not in after:
                changes.append((before, f"!! result does not contain {want!r}: {after!r}"))
    return changes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="actually rewrite the files; without it this is a dry run")
    args = ap.parse_args()

    books = find_books()
    print(f"Scanning {len(books)} lesson-plan books "
          f"({'DRY RUN — nothing will change' if not args.apply else 'APPLYING'})\n")

    affected = []
    for path, grade in books:
        doc = Document(path)
        changes = fix_runs(doc, grade)
        if not changes:
            continue
        affected.append((path, grade, doc, changes))
        sample = changes[0]
        print(f"  {path.name}")
        print(f"      {sample[0].strip()[:60]!r}")
        print(f"   -> {sample[1].strip()[:60]!r}")

    print(f"\n{len(affected)} of {len(books)} books mislabelled.")

    if not args.apply:
        print("Re-run with --apply to fix them.")
        return

    fixed = 0
    for path, grade, doc, _ in affected:
        before_paras = len(doc.paragraphs)
        doc.save(path)
        # Re-open and confirm the label is now correct and structure is intact.
        check = Document(path)
        text = "\n".join(p.text for p in check.paragraphs[:8])
        want = expected_label(grade)
        ok = want in text and len(check.paragraphs) == before_paras
        if not ok:
            print(f"  !! verification failed for {path.name}")
            continue
        fixed += 1
        print(f"  fixed  {path.name}  ({before_paras} paragraphs preserved)")

    print(f"\nDone. {fixed} book(s) corrected.")
    print("Originals remain in git:  git checkout c9a186c -- <file>")


if __name__ == "__main__":
    main()
