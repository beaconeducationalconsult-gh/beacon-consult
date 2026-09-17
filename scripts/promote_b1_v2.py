#!/usr/bin/env python3
"""Promote the Basic 1 `_v2` lesson-plan books to canonical, retiring v1.

## The decision

For four Basic 1 subjects two versions existed with no record of which was
authoritative. They are not cosmetic variants — they differ in substance:

| Subject | v1 | v2 | Verdict |
|---|---|---|---|
| Ghanaian Language | **540 placeholder strings** — prints "Ghanaian Language Content Standard B1.1.1.1" and "… Learning Indicator B1.1.1.1.1" instead of real curriculum text, across all 180 lessons | **0 placeholders** — real NaCCA text throughout | **v2, decisively** |
| Creative Arts | Truncated content (e.g. `'culture'`) | Full text (+34,808 chars) | v2 |
| English | — | Adds assessment detail (+17,888 chars) | v2 |
| Mathematics | — | Effectively identical (+41 chars) | either; v2 for consistency |

v1's Ghanaian Language book was unsellable as printed. v2 wins on every axis,
so v2 becomes the canonical file and v1 is retired.

## What this does

Overwrites `Basic1_<Subject>_Lesson_Plans_Full_Year.docx` with the `_v2` content
and deletes the `_v2` file. Filenames stay stable so catalogue SKUs
(`LP-B1-*`) and any published links keep working.

**Nothing is lost:** every original is in git at commit `c9a186c`. Restore with
`git checkout c9a186c -- <file>`.

Usage
-----
    python3 tools/promote_b1_v2.py            # dry run — report only
    python3 tools/promote_b1_v2.py --apply    # do it
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PAIRS = [
    "Basic1_Mathematics",
    "Basic1_English",
    "Basic1_Ghanaian_Language",
    "Basic1_Creative_Arts",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="actually promote; without it this is a dry run")
    args = ap.parse_args()

    pending, missing = [], []
    for stem in PAIRS:
        v1 = ROOT / f"{stem}_Lesson_Plans_Full_Year.docx"
        v2 = ROOT / f"{stem}_Lesson_Plans_Full_Year_v2.docx"
        if not v2.exists():
            missing.append(v2.name)
            continue
        if not v1.exists():
            missing.append(v1.name)
            continue
        pending.append((v1, v2))

    if missing:
        print("Missing expected files:")
        for m in missing:
            print(f"  - {m}")

    print(f"\n{'DRY RUN — nothing will change' if not args.apply else 'APPLYING'}\n")
    print(f"{'canonical (overwritten with v2)':48} {'v1 KB':>7} {'v2 KB':>7} {'delta':>7}")
    for v1, v2 in pending:
        a, b = v1.stat().st_size, v2.stat().st_size
        print(f"  {v1.name:46} {a / 1024:7.0f} {b / 1024:7.0f} {(b - a) / 1024:+7.0f}")

    if not args.apply:
        print(f"\n{len(pending)} book(s) would be promoted. Re-run with --apply.")
        return

    for v1, v2 in pending:
        shutil.copyfile(v2, v1)  # v2 content into the canonical name
        v2.unlink()              # retire the _v2 file
        print(f"  promoted {v2.name} -> {v1.name}")

    print(f"\nDone. {len(pending)} Basic 1 book(s) promoted to v2.")
    print("Originals remain in git:  git checkout c9a186c -- <file>")

    # Sanity: no _v2 lesson-plan files should remain.
    leftovers = sorted(ROOT.glob("*_v2.docx"))
    print(f"\nRemaining _v2 files: {[f.name for f in leftovers] or 'none'}")
    if leftovers:
        sys.exit(0)


if __name__ == "__main__":
    main()
