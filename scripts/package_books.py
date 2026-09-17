#!/usr/bin/env python3
"""Package the 77 lesson-plan DOCX volumes into sellable bundles.

Bundles written to dist/bundles/ (gitignored, rebuilt on demand):

  grade/Basic{1-9}_Complete.zip        all subjects for one grade
  subject/{Subject}_B1-B9.zip          one subject across all grades it exists in
  library/Beacon_Complete_Library.zip  every canonical volume

Also emits:
  dist/MANIFEST.md     human-readable catalogue with SKUs and sizes
  dist/manifest.json   machine-readable index (feed this to a storefront later)

Volumes flagged as `_v2` are treated as ALTERNATE revisions, not separate products:
they are reported in the manifest but excluded from bundles until the conflict is
resolved. Pass --include-v2 to override.

Usage:
    python3 tools/package_books.py                # build everything
    python3 tools/package_books.py --manifest-only
    python3 tools/package_books.py --include-v2
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from collections import defaultdict
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from _paths import BOOKS  # noqa: E402
DIST = ROOT / "dist"
BUNDLES = DIST / "bundles"

# filename subject slug -> (SKU code, display name)
SUBJECTS = {
    "Mathematics":          ("MAT", "Mathematics"),
    "English":              ("ENG", "English Language"),
    "Science":              ("SCI", "Science"),
    "Ghanaian_Language":    ("GHA", "Ghanaian Language"),
    "History":              ("HIS", "History"),
    "RME":                  ("RME", "Religious & Moral Education"),
    "OWOP":                 ("OWOP", "Our World Our People"),
    "Creative_Arts":        ("CRA", "Creative Arts"),
    "Creative_Arts_Design": ("CAD", "Creative Arts & Design"),
    "Computing":            ("COM", "Computing"),
    "Career_Technology":    ("CTE", "Career Technology"),
    "French":               ("FRE", "French"),
    "Social_Studies":       ("SOC", "Social Studies"),
}

FILENAME_RE = re.compile(
    r"^Basic(?P<grade>\d)_(?P<subject>.+?)_Lesson_Plans_Full_Year(?P<rev>_v\d+)?\.docx$"
)


def scan(include_v2: bool = False):
    """Return (canonical, alternates) lists of volume dicts."""
    canonical, alternates = [], []
    for path in sorted(BOOKS.glob("*.docx")):
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        subject_slug = m.group("subject")
        if subject_slug not in SUBJECTS:
            print(f"  ! unmapped subject slug: {subject_slug} ({path.name})")
            continue
        code, name = SUBJECTS[subject_slug]
        grade = "B" + m.group("grade")
        vol = {
            "sku": f"LP-{grade}-{code}",
            "grade": grade,
            "subject_code": code,
            "subject": name,
            "lessons": 180,
            "path": path,
            "kb": round(path.stat().st_size / 1024),
        }
        (alternates if m.group("rev") else canonical).append(vol)
        if m.group("rev") and include_v2:
            canonical.append({**vol, "sku": vol["sku"] + m.group("rev").upper()})
    return canonical, alternates


def write_zip(target: Path, volumes: list[dict]) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for v in volumes:
            arcname = f"{v['sku']}_{v['subject'].replace(' ', '-')}_{v['grade']}.docx"
            zf.write(v["path"], arcname)
            total += v["path"].stat().st_size
    return total


def build(canonical: list[dict]) -> dict:
    if BUNDLES.exists():
        shutil.rmtree(BUNDLES)
    BUNDLES.mkdir(parents=True)

    by_grade = defaultdict(list)
    by_subject = defaultdict(list)
    for v in canonical:
        by_grade[v["grade"]].append(v)
        by_subject[(v["subject_code"], v["subject"])].append(v)

    made = {"grades": [], "subjects": [], "library": None}

    for grade in sorted(by_grade, key=lambda g: int(g[1:])):
        vols = sorted(by_grade[grade], key=lambda v: v["subject"])
        target = BUNDLES / "grade" / f"Basic{grade[1:]}_Complete_{len(vols)}_volumes.zip"
        made["grades"].append({
            "name": f"Basic {grade[1:]} — Complete Year",
            "file": str(target.relative_to(ROOT)),
            "volumes": len(vols),
            "lessons": len(vols) * 180,
            "kb": round(write_zip(target, vols) / 1024),
            "sku": f"BND-{grade}-ALL",
        })

    for (code, name), vols in sorted(by_subject.items()):
        vols = sorted(vols, key=lambda v: int(v["grade"][1:]))
        slug = name.replace(" ", "-").replace("&", "and")
        target = BUNDLES / "subject" / f"{slug}_{len(vols)}_volumes.zip"
        made["subjects"].append({
            "name": f"{name} — Complete Set",
            "file": str(target.relative_to(ROOT)),
            "volumes": len(vols),
            "lessons": len(vols) * 180,
            "grades": f"{vols[0]['grade']}–{vols[-1]['grade']}",
            "kb": round(write_zip(target, vols) / 1024),
            "sku": f"BND-{code}-ALL",
        })

    target = BUNDLES / "library" / f"Beacon_Complete_Library_{len(canonical)}_volumes.zip"
    made["library"] = {
        "name": "Complete Library",
        "file": str(target.relative_to(ROOT)),
        "volumes": len(canonical),
        "lessons": len(canonical) * 180,
        "kb": round(write_zip(target, canonical) / 1024),
        "sku": "BND-LIBRARY",
    }
    return made


def write_manifest(canonical, alternates, made):
    lines = [
        "# Lesson Plan Library — Manifest",
        "",
        f"**{len(canonical)} canonical volumes · {len(canonical) * 180:,} lessons**",
        "",
    ]
    if alternates:
        lines += [
            f"> ⚠️ **{len(alternates)} alternate (`_v2`) volumes are excluded from bundles.**",
            "> They are *revisions* of existing B1 volumes, not extra products. Resolve the",
            "> conflict — pick v1 or v2 — then re-run with `--include-v2` if v2 wins.",
            ">",
        ]
        for v in alternates:
            lines.append(f"> - `{v['path'].name}`")
        lines.append("")

    lines += ["## Index by grade", ""]
    lines.append("| SKU | Grade | Subject | Lessons | Size |")
    lines.append("|---|---|---|---|---|")
    by_grade = defaultdict(list)
    for v in canonical:
        by_grade[v["grade"]].append(v)
    for grade in sorted(by_grade, key=lambda g: int(g[1:])):
        for v in sorted(by_grade[grade], key=lambda v: v["subject"]):
            lines.append(
                f"| `{v['sku']}` | {grade} | {v['subject']} | 180 | {v['kb']} KB |"
            )
    lines.append("")

    lines += ["## Grade bundles", "", "| SKU | Bundle | Volumes | Lessons | Size |", "|---|---|---|---|---|"]
    for b in made["grades"]:
        lines.append(
            f"| `{b['sku']}` | {b['name']} | {b['volumes']} | {b['lessons']:,} | {b['kb']} KB |"
        )
    lines.append("")

    lines += ["## Subject bundles", "", "| SKU | Bundle | Grades | Volumes | Lessons | Size |", "|---|---|---|---|---|---|"]
    for b in made["subjects"]:
        lines.append(
            f"| `{b['sku']}` | {b['name']} | {b['grades']} | {b['volumes']} | "
            f"{b['lessons']:,} | {b['kb']} KB |"
        )
    lines.append("")

    lib = made["library"]
    lines += [
        "## Complete library",
        "",
        f"| SKU | Bundle | Volumes | Lessons | Size |",
        "|---|---|---|---|---|",
        f"| `{lib['sku']}` | {lib['name']} | {lib['volumes']} | {lib['lessons']:,} | {lib['kb']} KB |",
        "",
    ]

    (DIST / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "volumes": [
            {k: (str(v["path"].name) if k == "path" else v[k])
             for k in ("sku", "grade", "subject", "subject_code", "lessons", "kb", "path")}
            for v in canonical
        ],
        "alternates": [v["path"].name for v in alternates],
        "bundles": made,
    }
    (DIST / "manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-v2", action="store_true",
                    help="treat _v2 volumes as canonical (overrides, causing duplicates)")
    ap.add_argument("--manifest-only", action="store_true", help="skip building zips")
    args = ap.parse_args()

    canonical, alternates = scan(include_v2=args.include_v2)
    print(f"Found {len(canonical)} canonical volumes "
          f"({len(canonical) * 180:,} lessons), {len(alternates)} alternates.")

    made = {"grades": [], "subjects": [], "library": None}
    if not args.manifest_only:
        made = build(canonical)
        print(f"Built {len(made['grades'])} grade bundles, "
              f"{len(made['subjects'])} subject bundles, 1 library bundle.")
        for b in made["grades"] + made["subjects"] + [made["library"]]:
            print(f"  {b['file']}  ({b['volumes']} vols, {b['kb']} KB)")

    DIST.mkdir(exist_ok=True)
    write_manifest(canonical, alternates, made)
    print(f"\nManifest: {DIST / 'MANIFEST.md'}")


if __name__ == "__main__":
    main()
