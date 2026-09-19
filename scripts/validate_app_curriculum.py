#!/usr/bin/env python3
"""Validate public/curriculum/ before shipping.

Checks the invariants the React app relies on. A failure here means the app
renders empty lists, orphaned indicator chips, or a scheme that silently
collapses to nothing.

    python3 scripts/validate_app_curriculum.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURR = ROOT / "public" / "curriculum"

errors: list[str] = []
warnings: list[str] = []


def load(name):
    p = CURR / name
    if not p.exists():
        errors.append(f"missing file: {name}")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        errors.append(f"{name}: invalid JSON ({e})")
        return None


def main():
    if not CURR.exists():
        sys.exit(f"No curriculum directory at {CURR}. Run scripts/build_app_curriculum.py first.")

    grades = load("grades.json") or []
    print(f"Validating {len(grades)} grades in {CURR}\n")

    total_ind = total_lessons = total_scheme_rows = 0

    for g in grades:
        gid = g["id"]
        gl = gid.lower()
        tag = f"{gid}"

        subjects = load(f"{gl}_subjects.json")
        indicators = load(f"{gl}_indicators.json")
        schemes = load(f"{gl}_schemes.json")
        if subjects is None or indicators is None or schemes is None:
            continue

        subj_ids = {s["id"] for s in subjects}
        ind_ids = {i["id"] for i in indicators}

        # --- indicator ids unique and well-formed
        if len(ind_ids) != len(indicators):
            errors.append(f"{tag}: {len(indicators) - len(ind_ids)} duplicate indicator ids")

        # --- every indicator belongs to a declared subject
        orphan_subj = {i["subjectId"] for i in indicators} - subj_ids
        if orphan_subj:
            errors.append(f"{tag}: indicators reference undeclared subjects: {sorted(orphan_subj)}")

        # --- buildTree() needs numeric strand/sub-strand numbers
        bad_num = [i["id"] for i in indicators
                   if not isinstance(i.get("strandNumber"), int)
                   or not isinstance(i.get("subStrandNumber"), int)]
        if bad_num:
            errors.append(f"{tag}: {len(bad_num)} indicators lack numeric strand/subStrandNumber"
                          f" (buildTree() sorts numerically) — e.g. {bad_num[:3]}")

        # --- every indicator has the text the UI shows
        empty_desc = [i["id"] for i in indicators if not (i.get("description") or "").strip()]
        if empty_desc:
            warnings.append(f"{tag}: {len(empty_desc)} indicators with empty description")

        # --- subjects.json counts agree with reality
        for s in subjects:
            actual = sum(1 for i in indicators if i["subjectId"] == s["id"])
            if s["counts"]["indicators"] != actual:
                errors.append(f"{tag}/{s['id']}: counts.indicators="
                              f"{s['counts']['indicators']} but {actual} present")

        # --- schedules: one file per subject-grade, only where hasSchedule.
        # useSchedules(grade, subjectId) fetches exactly one of these; a file
        # the subjects file does not declare is dead weight the app never asks
        # for, and a declared one that is missing renders an empty planner.
        lessons = []
        for s in subjects:
            name = f"schedules/{gl}-{s['id']}.json"
            # Not every subject is scheduled, and a subject that is not has no
            # file at all — only a *declared* schedule may be missing.
            rows = load(name) if (CURR / name).exists() else None
            if s["hasSchedule"]:
                if not rows:
                    errors.append(f"{tag}/{s['id']}: hasSchedule=true but {name} "
                                  f"is missing or empty")
                else:
                    lessons.extend(rows)
            elif rows:
                errors.append(f"{tag}/{s['id']}: hasSchedule=false but {name} "
                              f"holds {len(rows)} lessons")
        if lessons:
            bad_ref = {l["indicatorId"] for l in lessons} - ind_ids
            if bad_ref:
                errors.append(f"{tag}: {len(bad_ref)} scheduled lessons reference "
                              f"missing indicators — e.g. {sorted(bad_ref)[:3]}")
            sched_subj = {l["subjectId"] for l in lessons}
            if sched_subj - subj_ids:
                errors.append(f"{tag}: schedules reference undeclared subjects "
                              f"{sorted(sched_subj - subj_ids)}")

        # --- schemes
        weeks = schemes.get("teachingWeeksPerTerm")
        for sid, terms in (schemes.get("subjects") or {}).items():
            if sid not in subj_ids:
                errors.append(f"{tag}: scheme for undeclared subject {sid}")
                continue
            for term, rows in terms.items():
                if not rows:
                    errors.append(f"{tag}/{sid} term {term}: empty scheme")
                    continue
                lesson_rows = [r for r in rows if r.get("kind") == "lesson"]
                special = [r for r in rows if r.get("kind") == "special"]
                if len(lesson_rows) != weeks:
                    errors.append(f"{tag}/{sid} term {term}: {len(lesson_rows)} lesson rows "
                                  f"but teachingWeeksPerTerm={weeks}")
                if not special:
                    errors.append(f"{tag}/{sid} term {term}: no REVISION/EXAMINATION rows")
                for r in rows:
                    if r.get("kind") != "lesson":
                        continue
                    missing = [c for c in r.get("indicatorIds", []) if c not in ind_ids]
                    if missing:
                        errors.append(f"{tag}/{sid} term {term} week {r.get('week')}: "
                                      f"orphan indicatorIds {missing[:3]}")
                    if not (r.get("contentStandards") or "").strip():
                        warnings.append(f"{tag}/{sid} term {term} week {r.get('week')}: "
                                        "no content standard")
                total_scheme_rows += len(rows)

        total_ind += len(indicators)
        total_lessons += len(lessons)

        print(f"  {tag:4} {len(subjects):2} subjects · {len(indicators):4} indicators · "
              f"{len(lessons):5} lessons · "
              f"{sum(len(v) for t in (schemes.get('subjects') or {}).values() for v in t.values()):3} "
              f"scheme rows")

    print(f"\nTotals: {total_ind} indicators · {total_lessons} scheduled lessons · "
          f"{total_scheme_rows} scheme rows")

    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for w in warnings[:10]:
            print(f"   - {w}")
        if len(warnings) > 10:
            print(f"   … and {len(warnings) - 10} more")

    if errors:
        print(f"\n❌ {len(errors)} error(s):")
        for e in errors[:20]:
            print(f"   - {e}")
        if len(errors) > 20:
            print(f"   … and {len(errors) - 20} more")
        sys.exit(1)

    print("\n✅ All invariants hold — the app can consume this data safely.")


if __name__ == "__main__":
    main()
