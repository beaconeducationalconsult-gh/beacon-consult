#!/usr/bin/env python3
"""Build the Beacon app's static curriculum bundle for every grade.

The app (app/src/hooks/useCurriculum.js) serves the curriculum as static JSON
from /curriculum/ — no Firestore reads. Until now only Basic 1 was generated
(app/seed/build_curriculum.py handles B1 alone). This builds KG + B1-B9 from
the repo's full dataset, and adds a new file the app didn't have: per-grade
Schemes of Learning, derived from the 13,140 enriched lessons.

Outputs (public/curriculum/, committed — this is portal source data)
--------------------------------------------------------------------
    grades.json                 one entry per grade that has data
    <grade>_subjects.json       subjects for the grade, with counts
    <grade>_indicators.json     flat indicators, full hierarchy, rich metadata
    <grade>_schedules.json      every scheduled lesson: term/week/day + phases
    <grade>_schemes.json        NEW — scheme rows per subject per term

Shapes match what useCurriculum.js / buildTree() / ForecastForm already expect,
so no app changes are needed to read them. See docs/APP_CURRICULUM.md.

Usage
-----
    python3 tools/build_app_curriculum.py
    python3 tools/build_app_curriculum.py --grade B4
    python3 scripts/build_app_curriculum.py --out public/curriculum
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

# Pure-data helpers; the docx import inside generate_schemes is optional.
from generate_schemes import (  # noqa: E402
    B1_DB_PREFIX,
    DB_SEARCH,
    SUBJECTS,
    build_scheme,
    discover,
)

GRADES = ["KG1", "KG2"] + [f"B{i}" for i in range(1, 10)]

# Kindergarten has a single subject in the dataset and no enriched lessons.
EXTRA_SUBJECTS = {"kindergarten": ("kindergarten", "Kindergarten")}
SUBJECT_NAMES = {sid: name for sid, name in SUBJECTS.values()}
SUBJECT_NAMES.update(EXTRA_SUBJECTS)

PAGE_JUNK_RE = re.compile(r"\s*===\s*PAGE \d+\s*===.*$", re.S)
NUM_NAME_RE = re.compile(r"^\s*(\d+)\s*[.):]?\s*(.*)$")


def clean_text(v):
    if not isinstance(v, str):
        return v or ""
    v = PAGE_JUNK_RE.sub("", v)
    return re.sub(r"\s+", " ", v).strip()


def split_num_name(text, fallback):
    """'1. NUMBER' -> (1, 'NUMBER'); 'Sub-strand B4.1.1' -> (fallback, same)."""
    m = NUM_NAME_RE.match(text or "")
    if m and m.group(2):
        return int(m.group(1)), m.group(2).strip()
    return fallback, (text or "").strip()


def code_parts(code):
    """'B4.1.1.1.1' -> [1, 1, 1, 1]  (strand, sub-strand, standard, indicator)."""
    seg = (code or "").split(".")
    if len(seg) < 4:
        return []
    try:
        return [int(x) for x in seg[1:]]
    except ValueError:
        return []


def find_file(name):
    for base in DB_SEARCH:
        p = base / name
        if p.exists():
            return p
    return None


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def db_index():
    """Map (subjectId, grade) -> database path, for every DB we can find."""
    out = {}
    for key, (sid, _name) in list(SUBJECTS.items()) + list(EXTRA_SUBJECTS.items()):
        for grade in GRADES:
            if (sid, grade) in out:
                continue
            if grade == "B1" and key in B1_DB_PREFIX:
                fname = f"{B1_DB_PREFIX[key]}_curriculum_db_clean.json"
            else:
                fname = f"{sid}_{grade}_curriculum_db_clean.json"
            p = find_file(fname)
            if p:
                out[(sid, grade)] = p
    return out


def summary_for(sid, grade):
    """Read the sibling *_curriculum_summary.json when it exists."""
    if grade == "B1":
        for key, (s, _n) in SUBJECTS.items():
            if s == sid and key in B1_DB_PREFIX:
                p = find_file(f"{B1_DB_PREFIX[key]}_curriculum_summary.json")
                if p:
                    return load_json(p)
    p = find_file(f"{sid}_{grade}_curriculum_summary.json")
    return load_json(p) if p else {}


def build_indicators(sid, sname, grade, db_path):
    clean = load_json(db_path)
    indicators, strands, subs, standards = [], set(), set(), set()

    for code, row in clean.items():
        parts = code_parts(code)
        strand_num = parts[0] if parts else 0
        sub_num = parts[1] if len(parts) > 1 else 0
        strand_num, strand_name = split_num_name(clean_text(row.get("strand")), strand_num)
        _, sub_name = split_num_name(clean_text(row.get("sub_strand")), sub_num)
        if parts:
            strand_num = parts[0]
            sub_num = parts[1] if len(parts) > 1 else sub_num

        cs_code = row.get("cs_code") or code.rsplit(".", 1)[0]
        strands.add(strand_num)
        subs.add((strand_num, sub_num))
        standards.add(cs_code)

        indicators.append({
            "id": f"{sid}_{code}",
            "code": code,
            "grade": grade,
            "subjectId": sid,
            "subjectName": sname,
            "strandNumber": strand_num,
            "strandName": strand_name,
            "subStrandNumber": sub_num,
            "subStrandName": sub_name,
            "contentStandardCode": cs_code,
            "contentStandardDescription": clean_text(row.get("cs_desc")),
            "description": clean_text(row.get("ind_desc")),
            "competencies": clean_text(row.get("competencies")),
            "resources": clean_text(row.get("resources")),
            "keywords": clean_text(row.get("keywords")),
            "assessment": clean_text(row.get("assessment")),
        })

    counts = {
        "strands": len(strands),
        "subStrands": len(subs),
        "standards": len(standards),
        "indicators": len(indicators),
    }
    return indicators, counts


def namespace_ids(rows, sid):
    """Scheme rows carry bare indicator codes; the app refs them as `{sid}_{code}`.

    Matches the convention in src/lib/schemeAuto.js: `indicators` is the text
    shown in the cell, `indicatorIds` is the set of document references.
    """
    out = []
    for r in rows:
        if r.get("kind") != "lesson":
            out.append(r)
            continue
        out.append({**r, "indicatorIds": [f"{sid}_{c}" for c in r.get("indicatorIds", [])]})
    return out


def build_schedules(sid, grade, lessons, clean):
    out = []
    for les in lessons:
        code = les["ind_code"]
        ref = clean.get(code, {}) if clean else {}
        parts = code_parts(code)
        strand_num, strand_name = split_num_name(
            clean_text(ref.get("strand") or les.get("strand_name")),
            parts[0] if parts else les.get("strand_num", 0),
        )
        _, sub_name = split_num_name(
            clean_text(ref.get("sub_strand") or les.get("sub_strand")), 0
        )
        out.append({
            "id": f"{sid}_{grade}_T{les['term']}_W{les['week']}_{les['day']}",
            "grade": grade,
            "subjectId": sid,
            "lessonNum": les.get("lesson_num"),
            "term": les["term"],
            "week": les["week"],
            "day": les["day"],
            "isRevision": bool(les.get("is_revision")),
            "strandName": strand_name,
            "subStrandName": sub_name,
            "contentStandardCode": les.get("cs_code"),
            "contentStandardDescription": clean_text(ref.get("cs_desc") or les.get("cs_desc")),
            "indicatorId": f"{sid}_{code}",
            "indicatorCode": code,
            "indicatorDescription": clean_text(ref.get("ind_desc") or les.get("ind_desc")),
            "sessionTitle": les.get("session_title") or "",
            "performanceIndicator": clean_text(les.get("perf_indicator")) or "",
            "competencies": clean_text(les.get("competencies") or ref.get("competencies")) or "",
            "resources": clean_text(les.get("resources") or ref.get("resources")) or "",
            "keywords": clean_text(les.get("keywords") or ref.get("keywords")) or "",
            "rpk": clean_text(les.get("rpk")) or "",
            "starter": [clean_text(s) for s in les.get("starter") or []],
            "main": [clean_text(s) for s in les.get("main") or []],
            "plenary": [clean_text(s) for s in les.get("plenary") or []],
            "assessment": clean_text(les.get("assessment") or ref.get("assessment")) or "",
        })
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grade", help="build a single grade, e.g. B4")
    ap.add_argument("--out", default=None, help="output directory")
    args = ap.parse_args()

    out_dir = Path(args.out) if args.out else ROOT / "public" / "curriculum"
    out_dir.mkdir(parents=True, exist_ok=True)

    dbs = db_index()
    # Index lessons by *subject id*, not file key: two file keys (ghanaian,
    # ghanaian_language) resolve to the same subject id, and iterating by key
    # would count B1 Ghanaian Language twice.
    lessons_by_subject = {(SUBJECTS[k][0], g): p for k, g, p in discover()}

    grades_out, report = [], []

    for grade in GRADES:
        if args.grade and grade != args.grade:
            continue

        subjects, indicators, schedules = [], [], []
        schemes = {}
        teaching_weeks = 12

        pairs = sorted({(sid, g) for (sid, g) in dbs if g == grade}
                       | {(sid, g) for (sid, g) in lessons_by_subject if g == grade})

        for sid, _ in pairs:
            sname = SUBJECT_NAMES.get(sid, sid)
            db_path = dbs.get((sid, grade))
            lesson_path = lessons_by_subject.get((sid, grade))
            if not db_path and not lesson_path:
                continue

            clean = load_json(db_path) if db_path else {}
            subj_indicators, counts = ([], None)
            if db_path:
                subj_indicators, counts = build_indicators(sid, sname, grade, db_path)
                indicators.extend(subj_indicators)

            lessons = load_json(lesson_path) if lesson_path else []
            has_schedule = bool(lessons)
            if has_schedule:
                schedules.extend(build_schedules(sid, grade, lessons, clean))
                scheme = build_scheme(lessons, None)
                schemes[sid] = {
                    str(t): namespace_ids(rows, sid)
                    for t, rows in sorted(scheme.items())
                }
                teaching_weeks = max(
                    int(r["week"]) for rows in scheme.values()
                    for r in rows if r["kind"] == "lesson")

            summary = summary_for(sid, grade)
            subjects.append({
                "id": sid,
                "name": summary.get("name") or sname,
                "grade": grade,
                "sourceTitle": summary.get("sourceTitle")
                               or f"NaCCA {grade} {sname} Curriculum",
                "sourceUrl": summary.get("sourceUrl") or "",
                "hasSchedule": has_schedule,
                "counts": counts or {
                    "strands": 0, "subStrands": 0, "standards": 0, "indicators": 0,
                },
            })

        if not subjects:
            continue

        subjects.sort(key=lambda s: s["name"])
        indicators.sort(key=lambda i: (i["subjectId"],
                                       [int(p) for p in i["code"].split(".")[1:]]
                                       if code_parts(i["code"]) else [0]))
        schedules.sort(key=lambda l: (l["subjectId"], l["term"], l["week"],
                                      l["lessonNum"] or 0))

        g = grade.lower()
        files = {
            f"{g}_subjects.json": subjects,
            f"{g}_indicators.json": indicators,
            f"{g}_schemes.json": {
                "grade": grade,
                "teachingWeeksPerTerm": teaching_weeks,
                "subjects": schemes,
            },
        }
        if schedules:
            files[f"{g}_schedules.json"] = schedules

        for name, payload in files.items():
            (out_dir / name).write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8")

        grades_out.append({
            "id": grade,
            "name": ("KG " + grade[2:]) if grade.startswith("KG")
                    else f"Basic {grade[1:]}",
            "available": True,
            "subjects": len(subjects),
            "indicators": len(indicators),
            "hasSchedules": sorted({s["id"] for s in subjects if s["hasSchedule"]}),
        })

        report.append({
            "grade": grade,
            "subjects": len(subjects),
            "indicators": len(indicators),
            "lessons": len(schedules),
            "scheme_subjects": len(schemes),
            "kb": sum((out_dir / n).stat().st_size for n in files) // 1024,
        })
        print(f"  {grade:4} {len(subjects):2} subjects · {len(indicators):4} indicators · "
              f"{len(schedules):5} lessons · {len(schemes):2} schemes · "
              f"{report[-1]['kb']:5} KB")

    (out_dir / "grades.json").write_text(
        json.dumps(grades_out, ensure_ascii=False, indent=1), encoding="utf-8")

    total_kb = sum(f.stat().st_size for f in out_dir.glob("*.json")) // 1024
    print(f"\nWrote {len(grades_out)} grades to {out_dir}")
    print(f"  {len(list(out_dir.glob('*.json')))} files · {total_kb} KB total")
    print(f"  {sum(r['subjects'] for r in report)} subject-grades · "
          f"{sum(r['indicators'] for r in report)} indicators · "
          f"{sum(r['lessons'] for r in report)} scheduled lessons")

    (out_dir / "_BUILD_REPORT.json").write_text(json.dumps({
        "grades": grades_out, "detail": report, "totalKb": total_kb,
    }, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
