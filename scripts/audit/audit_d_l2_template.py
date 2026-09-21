#!/usr/bin/env python3
"""Audit D - What in L2 is per-lesson content and what is a subject-wide template (P1-4).

L2 is 13,140 scheduled lesson slots. This audit answers one question about it,
field by field: **how many distinct values does a field take inside a single
subject-grade?** A field with one value across all 180 slots of a subject-grade is
not lesson planning — it is the printed teaching template, repeated. A field with
many values is content someone (or a template with per-indicator inputs) wrote.

The reading decides how the product may describe itself, and it is what the app
uses to label a plan it filled from the curriculum: a teacher should know which
parts they inherited verbatim and which parts are theirs to write.

Measured 2026-09-19, across the 73 subject-grades that have lessons:

    field           constant in      median distinct / 180 slots
    rpk             70 of 73         1
    plenary         60 of 73         1
    assessment      67 of 73         1
    competencies    67 of 73         1
    resources       66 of 73         1
    keywords        66 of 73         1
    starter          0 of 73        156
    main             0 of 73         60
    perf_indicator   0 of 73         42   (derived from ind_desc)
    ind_desc         0 of 73         42   (~4 slots per indicator)
    session_title    0 of 73         21

So L2 is **per-lesson `starter`/`main` content inside a subject-wide routine
template** — not 13,140 authored lesson plans. That is a good product, honestly
described.

Writes `data/audit/l2_template.json` and prints the table. Report-only apart from
that artifact; it changes no data.

    python3 scripts/audit/audit_d_l2_template.py
    python3 scripts/audit/audit_d_l2_template.py --json   # print the artifact
"""
# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import argparse
import json
from pathlib import Path

from _paths import AUDIT, DATA

LESSONS = DATA / "lessons"

# The full skeleton of a slot, in the order the printed lesson plan uses.
FIELDS = ["session_title", "perf_indicator", "ind_desc", "competencies", "resources",
          "keywords", "rpk", "starter", "main", "plenary", "assessment"]

# One value in every slot of a subject-grade = the subject's template.
TEMPLATE_FIELDS = {"competencies", "resources", "keywords", "rpk", "plenary", "assessment"}


def value_of(slot: dict, field: str) -> str:
    value = slot.get(field)
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def measure() -> dict:
    per_file = []
    global_distinct = {field: set() for field in FIELDS}
    slots = 0

    for path in sorted(LESSONS.glob("*.json")):
        rows = json.loads(path.read_text(encoding="utf-8"))
        slots += len(rows)
        fields = {}
        for field in FIELDS:
            values = {value_of(slot, field) for slot in rows}
            global_distinct[field] |= values
            fields[field] = {
                "distinct": len(values),
                "constant": len(values) == 1,
                "example": sorted(values)[0][:160] if values else None,
            }
        per_file.append({"file": path.name, "slots": len(rows), "fields": fields})

    summary = {}
    for field in FIELDS:
        counts = [entry["fields"][field]["distinct"] for entry in per_file]
        summary[field] = {
            "constantIn": sum(1 for entry in per_file if entry["fields"][field]["constant"]),
            "subjectGrades": len(per_file),
            "medianDistinct": sorted(counts)[len(counts) // 2],
            "globalDistinct": len(global_distinct[field]),
            # A field is *routine* when it is one value in every slot of most
            # subject-grades — those are the ones a plan inherits, not writes.
            "routine": field in TEMPLATE_FIELDS
            and sum(1 for entry in per_file if entry["fields"][field]["constant"]) >= len(per_file) * 0.8,
        }

    return {
        "generatedBy": "scripts/audit/audit_d_l2_template.py",
        "question": "how many distinct values does each lesson field take inside one subject-grade?",
        "slots": slots,
        "files": len(per_file),
        "summary": summary,
        "perSubjectGrade": per_file,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the artifact instead of the table")
    args = ap.parse_args()

    if not LESSONS.exists():
        _sys.exit(f"No data/lessons/ at {LESSONS}")
    result = measure()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0

    print(f"L2: {result['slots']} slots in {result['files']} subject-grade files\n")
    print(f"  {'field':16} {'constant in':>11}  {'median distinct':>15}  {'global':>7}  reading")
    for field, row in result["summary"].items():
        reading = "subject-wide template" if row["routine"] else "per-lesson content"
        print(f"  {field:16} {row['constantIn']:>6}/{row['subjectGrades']:<4} "
              f"{row['medianDistinct']:>15}  {row['globalDistinct']:>7}  {reading}")

    routine = [f for f, r in result["summary"].items() if r["routine"]]
    print(f"\n  routine fields (constant in >=80% of subject-grades): {', '.join(routine) or 'none'}")
    print("  These are inherited, not written: a plan filled from the curriculum carries the")
    print("  subject's printed template for them, which is what the app now says out loud.")

    AUDIT.mkdir(parents=True, exist_ok=True)
    out = AUDIT / "l2_template.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n  wrote {out.relative_to(DATA.parent)}")
    return 0


if __name__ == "__main__":
    _sys.exit(main())
