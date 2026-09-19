#!/usr/bin/env python3
"""Derive the canonical inventory of this repository **from the dataset itself**.

Every headline number in README.md, docs/DATA_MODEL.md, docs/TODO.md and
.kiro/steering/project.md is produced by this script. Before it existed those
numbers were hand-typed and had drifted: the docs claimed the app was empty,
pointed at `tools/` paths that are now `scripts/`, and described "148 curriculum
JSON databases" (75 databases + 73 summaries = 148 *files*, not 148 databases).

The dataset has three layers, and conflating them is what let the divergences
hide. This script keeps them apart:

    L1  curriculum   data/curriculum/  *_curriculum_db_clean.json + *_summary.json
                     the audited extraction from the NaCCA source PDFs.
    L2  lessons      data/lessons/*_lessons_enriched.json
                     the teaching template filled per lesson slot.
    L3  bundle       public/curriculum/*.json
                     what the React app can serve — the only layer a teacher touches.

    (ref) reference  data/reference/ — a second, partly-divergent copy that
                     `scripts/_paths.py` silently falls back to. Some L3 pairs
                     exist ONLY here. Reported loudly, never counted as a total.

Usage
-----
    python3 scripts/build_inventory.py            # write data/inventory.json + report
    python3 scripts/build_inventory.py --quiet    # write only (CI)

Exit codes
----------
    0  dataset and app agree (warnings may still print)
    1  the app cannot serve part of the dataset, a module declares data that does
       not exist, or a headline layer is missing
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CURRICULUM = DATA / "curriculum"
LESSONS = DATA / "lessons"
REFERENCE = DATA / "reference"
BUNDLE = ROOT / "public" / "curriculum"
MODULES = ROOT / "legacy" / "kernel-app" / "src" / "modules"
OUT = DATA / "inventory.json"

# Dataset subject ids are the canonical ones. Anything on disk that spells them
# differently is mapped here (the `math` -> `mathematics` mismatch that broke
# MathModule is exactly the class of bug this table exists to surface).
SLUG_TO_SUBJECT = {
    "math": "mathematics", "mathematics": "mathematics",
    "english": "english-language", "english-language": "english-language",
    "ghanaian": "ghanaian-language", "ghanaian-language": "ghanaian-language",
    "ghanaian_language": "ghanaian-language",
    "creative-arts": "creative-arts", "creative_arts": "creative-arts",
    "creative-arts-design": "creative-arts-design", "creative_arts_design": "creative-arts-design",
    "career-technology": "career-technology", "career_technology": "career-technology",
    "social-studies": "social-studies", "social_studies": "social-studies",
    "computing": "computing", "french": "french", "history": "history",
    "owop": "owop", "rme": "rme", "science": "science", "kindergarten": "kindergarten",
}

# Subjects present in a layer that deliberately have no app module yet.
INTENTIONALLY_UNSERVED = {
    "kindergarten": "KG1/KG2 indicators only (no lessons, no module planned yet)",
}

# Lesson fields that describe the teaching template. Reported as distinct/total
# ratios so nobody calls 13,140 template-filled slots "13,140 lesson plans".
FIDELITY_FIELDS = (
    "ind_desc", "perf_indicator", "session_title",
    "rpk", "starter", "main", "plenary", "assessment",
)

HISTORICAL_DOCS = {"REPO_ANALYSIS_REPORT.md", "APP_BUILD_PLAN.md", "FULL_README.md", "DEVELOPMENT_GUIDE.md"}

# The dataset spells kindergarten two ways: filenames and summaries say KG1/KG2
# while the indicator codes say K1/K2. Normalise on the former.
GRADE_ALIASES = {"K1": "KG1", "K2": "KG2"}
GRADE_RE = re.compile(r"^([A-Za-z]+\d+)\.")
DB_NAME_RE = re.compile(r"^(?P<slug>[A-Za-z0-9_\-]+?)(?:_(?P<grade>[A-Za-z]+\d+))?_curriculum_db_clean\.json$")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def stringify(value) -> str:
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value or "").strip()


def grade_of(code: str) -> str:
    m = GRADE_RE.match(str(code or ""))
    if not m:
        return ""
    g = m.group(1).upper()
    return GRADE_ALIASES.get(g, g)


def grade_sort_key(grade: str):
    digits = int(re.sub(r"\D", "", grade) or 0)
    return (0, digits, grade) if grade.upper().startswith("KG") else (1, digits, grade)


def subject_of_slug(slug: str) -> str:
    return SLUG_TO_SUBJECT.get(slug.lower(), slug.lower().replace("_", "-"))


# ────────────────────────────────────────────── L1 / reference: DB + summary ──
def read_db_layer(layer_dir: Path) -> tuple[dict, list]:
    """-> ({(subject, grade): pair}, [summary files missing a counts block])

    A pair is discovered from the database filename (subject slug + optional
    grade hint) and/or from a summary file. Indicators are counted from the
    codes actually present in the database, filtered to the pair's grade — this
    is what makes multi-grade files and the B1 `math_curriculum_db_clean.json`
    style names (no grade in the filename) come out right.
    """
    pairs: dict[tuple[str, str], dict] = {}
    malformed: list[str] = []
    grade_mismatches: list[str] = []

    summaries = {}
    for path in sorted(layer_dir.glob("*_curriculum_summary.json")):
        s = load(path)
        sid, grade = s.get("id"), s.get("grade")
        if not sid or not grade:
            continue
        grade = GRADE_ALIASES.get(grade.upper(), grade.upper())
        if "counts" not in s:
            malformed.append(path.name)
            continue
        summaries[(sid, grade)] = {
            "file": path.name,
            "name": s.get("name", sid),
            "indicators": s.get("counts", {}).get("indicators"),
            "strands": s.get("counts", {}).get("strands"),
            "subStrands": s.get("counts", {}).get("subStrands"),
            "standards": s.get("counts", {}).get("standards"),
            "source": s.get("sourceTitle", ""),
            "url": s.get("sourceUrl", ""),
            "extraction": s.get("extraction_method", ""),
        }

    for path in sorted(layer_dir.glob("*_curriculum_db_clean.json")):
        raw = load(path)
        if not isinstance(raw, dict):
            continue
        codes = list(raw)
        code_grades = sorted({grade_of(c) for c in codes if grade_of(c)}, key=grade_sort_key)
        m = DB_NAME_RE.match(path.name)
        slug = m.group("slug") if m else path.stem
        hint = (m.group("grade") or "").upper() if m else ""
        hint = GRADE_ALIASES.get(hint, hint)
        subject = subject_of_slug(slug)

        if hint:
            targets = [hint]
            if code_grades and hint not in code_grades:
                grade_mismatches.append(f"{path.name}: filename says {hint}, codes contain {code_grades}")
        else:
            targets = code_grades
            if len(code_grades) > 1:
                grade_mismatches.append(f"{path.name}: no grade in filename, codes span {code_grades}")

        for grade in targets:
            key = (subject, grade)
            pair = pairs.setdefault(key, {"dbs": [], "dbIndicators": 0})
            pair["dbs"].append(path.name)
            pair["dbIndicators"] += sum(1 for c in codes if grade_of(c) == grade) if code_grades else len(codes)

    # summary-only pairs (a summary with no database in this layer, e.g. english B5)
    for key, s in summaries.items():
        pair = pairs.setdefault(key, {"dbs": [], "dbIndicators": None})
        pair["summaryOnly"] = not pair["dbs"]

    for key, pair in pairs.items():
        s = summaries.get(key)
        pair.update({
            "subjectId": key[0],
            "grade": key[1],
            "name": (s or {}).get("name", key[0]),
            "summaryIndicators": (s or {}).get("indicators"),
            "summaryFile": (s or {}).get("file"),
            "strands": (s or {}).get("strands"),
            "subStrands": (s or {}).get("subStrands"),
            "standards": (s or {}).get("standards"),
            "source": (s or {}).get("source", ""),
            "extraction": (s or {}).get("extraction", ""),
            "summaryOnly": bool(pair.get("summaryOnly")),
        })
    return pairs, malformed, grade_mismatches


# ──────────────────────────────────────────────────────────── L2: lessons ────
def read_lessons() -> dict:
    out = {}
    for path in sorted(LESSONS.glob("*_lessons_enriched.json")):
        rows = load(path)
        if not isinstance(rows, list) or not rows:
            continue
        n = len(rows)
        codes = [str(r.get("ind_code") or "") for r in rows]
        grades = sorted({grade_of(c) for c in codes if grade_of(c)}, key=grade_sort_key)
        distinct = {f: len({stringify(r.get(f)) for r in rows}) for f in FIDELITY_FIELDS}
        out[path.name] = {
            "slug": subject_of_slug(re.sub(r"_b\d+$", "", path.name.replace("_lessons_enriched.json", ""))),
            "lessons": n,
            "grades": grades,
            "grade": grades[0] if len(grades) == 1 else "",
            "indicators": len(set(codes)),
            "terms": sorted({int(r["term"]) for r in rows if isinstance(r.get("term"), int)}),
            "maxWeek": max((int(r.get("week") or 0) for r in rows), default=0),
            "distinct": distinct,
            "distinctRatio": {f: round(distinct[f] / n, 3) for f in FIDELITY_FIELDS},
        }
    return out


# ───────────────────────────────────────────────────────────── L3: bundle ────
def read_bundle() -> dict:
    grades_path = BUNDLE / "grades.json"
    if not grades_path.exists():
        return {"built": False, "grades": [], "pairs": {}, "subjects": {}, "gradeNames": {}, "scheduleGrades": []}
    grades = load(grades_path)
    pairs, subjects, names = {}, collections.defaultdict(list), {}
    sched_grades = set()
    for g in grades:
        gid = g.get("id")
        if not gid:
            continue
        names[gid] = g.get("name", gid)
        subj_path = BUNDLE / f"{gid.lower()}_subjects.json"
        if not subj_path.exists():
            continue
        for s in load(subj_path):
            pairs[(s["id"], gid)] = s.get("counts", {}).get("indicators", 0)
            subjects[s["id"]].append(gid)
            # Schedules are split per subject-grade (schedules/<grade>-<id>.json);
            # the subjects file says which of them exist, so the grade list does
            # not depend on globbing a directory that may not exist.
            if s.get("hasSchedule") and (BUNDLE / "schedules" / f"{gid.lower()}-{s['id']}.json").exists():
                sched_grades.add(gid)
    return {
        "built": True,
        "grades": [g["id"] for g in grades],
        "gradeNames": names,
        "pairs": pairs,
        "subjects": dict(subjects),
        "scheduleGrades": sorted(sched_grades, key=grade_sort_key),
        "hasQuestions": (BUNDLE / "questions").exists(),
        "bytes": sum(p.stat().st_size for p in BUNDLE.rglob("*.json")),
    }


# ────────────────────────────────────────────────────────── app modules ──────
def read_modules() -> dict:
    """Regex lint over TS literals — deliberately not a TypeScript parser."""
    out = {}
    for path in sorted(MODULES.glob("*/*Module.ts")):
        text = path.read_text(encoding="utf-8")
        mid = re.search(r"\bid\s*=\s*'([^']+)'", text)
        grades = re.search(r"\bgrades\s*=\s*\[([^\]]*)\]", text)
        caps = re.search(r"\bcapabilities\s*=\s*new Set\(\[([^\]]*)\]\)", text)
        name = re.search(r"\bdisplayName\s*=\s*'([^']+)'", text)
        out[path.name] = {
            "id": mid.group(1) if mid else None,
            "displayName": name.group(1) if name else None,
            "grades": re.findall(r"'([^']+)'", grades.group(1)) if grades else [],
            "capabilities": re.findall(r"'([^']+)'", caps.group(1)) if caps else [],
            "validateIsStub": bool(re.search(r"validate\(\)\s*:\s*string\[\]\s*\{\s*return\s*\[\s*\]", text, re.S)),
        }
    return out


def check_doc_links() -> dict:
    missing: dict[str, set[str]] = collections.defaultdict(set)
    roots = [ROOT / "README.md", ROOT / "docs", ROOT / ".kiro"]
    for root in roots:
        paths = [root] if root.is_file() else list(root.rglob("*.md"))
        for path in paths:
            rel = str(path.relative_to(ROOT))
            if path.name in HISTORICAL_DOCS or "CODE_REVIEW" in path.name:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            # Only root-relative `docs/...` references: a bare regex would also
            # match the tail of `legacy/docs/CODE_REVIEW.md` and report a file
            # that exists. Require the match not to be preceded by a path char,
            # a backtick, or `(`/`[` immediately followed by a path prefix.
            for match in re.finditer(r"(?<![\w./\-])docs/[A-Za-z0-9_\-]+\.md", text):
                ref = match.group(0)
                if not (ROOT / ref).exists():
                    missing[ref].add(rel)
    return {k: sorted(v) for k, v in sorted(missing.items())}


# ──────────────────────────────────────────────────────────────── main ───────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quiet", action="store_true", help="write data/inventory.json without printing the report")
    args = ap.parse_args()

    l1, l1_malformed, grade_mismatches = read_db_layer(CURRICULUM)
    ref, ref_malformed, _ = read_db_layer(REFERENCE)
    l2_raw = read_lessons()
    l3 = read_bundle()
    modules = read_modules()

    errors: list[str] = []
    warnings: list[str] = []

    # ── L2 index by subject-grade (a subject can span several files)
    l2: dict[tuple[str, str], dict] = {}
    for info in l2_raw.values():
        for grade in info["grades"]:
            agg = l2.setdefault((info["slug"], grade), {"lessons": 0, "indicators": 0, "files": []})
            agg["lessons"] += info["lessons"]
            agg["indicators"] += info["indicators"]
            agg["files"].append(info["slug"])

    universe = sorted(set(l1) | set(l2) | set(l3["pairs"]) | set(ref), key=lambda p: (p[0], grade_sort_key(p[1])))

    subject_grades = []
    for sid, grade in universe:
        a, b = l1.get((sid, grade)), ref.get((sid, grade))
        subject_grades.append({
            "subjectId": sid,
            "subjectName": (a or b or {}).get("name", sid),
            "grade": grade,
            "l1Indicators": (a or {}).get("dbIndicators") if a and not a.get("summaryOnly") else None,
            "l1SummaryIndicators": (a or {}).get("summaryIndicators"),
            "refIndicators": (b or {}).get("dbIndicators"),
            "l2LessonSlots": l2.get((sid, grade), {}).get("lessons", 0),
            "l2IndicatorsScheduled": l2.get((sid, grade), {}).get("indicators", 0),
            "l3BundleIndicators": l3["pairs"].get((sid, grade)),
            "referenceOnly": (sid, grade) not in l1 and (sid, grade) in ref,
        })

    grades_present = sorted({p[1] for p in universe}, key=grade_sort_key)
    subjects_present = sorted({p[0] for p in universe})

    totals = {
        "grades": len(grades_present),
        "subjects": len(subjects_present),
        "subjectGrades": len(universe),
        "l1": {
            "label": "curriculum",
            "subjectGrades": len(l1),
            "indicators": sum(v["dbIndicators"] or 0 for v in l1.values()),
            "databases": sum(len(v["dbs"]) for v in l1.values()),
            "summaries": sum(1 for v in l1.values() if v["summaryFile"]),
            "summaryOnlyPairs": sorted(f"{k[0]} {k[1]}" for k, v in l1.items() if v["summaryOnly"]),
            "pairsWithoutSummary": sorted(f"{k[0]} {k[1]}" for k, v in l1.items() if not v["summaryFile"]),
        },
        "l2": {
            "label": "lessons",
            "subjectGrades": len(l2),
            "files": len(l2_raw),
            "lessonSlots": sum(v["lessons"] for v in l2_raw.values()),
            "subjects": len({v["slug"] for v in l2_raw.values()}),
            "grades": len({g for _, g in l2}),
        },
        "l3": {
            "label": "bundle",
            "subjectGrades": len(l3["pairs"]),
            "indicators": sum(l3["pairs"].values()),
            "grades": len(l3["grades"]),
            "subjects": len(l3["subjects"]),
            "hasQuestions": l3.get("hasQuestions", False),
            "megabytes": round(l3.get("bytes", 0) / 1e6, 1),
        },
        "reference": {
            "label": "reference-fallback",
            "databases": sum(len(v["dbs"]) for v in ref.values()),
            "summaries": sum(1 for v in ref.values() if v["summaryFile"]),
            "malformedSummaries": len(ref_malformed),
            "suppliesBundlePairs": sorted(
                f"{s} {g}" for (s, g) in l3["pairs"] if (s, g) not in l1 and (s, g) in ref
            ),
            "bundlePairsWithoutAnySource": sorted(
                f"{s} {g}" for (s, g) in l3["pairs"] if (s, g) not in l1 and (s, g) not in ref
            ),
        },
        "sources": {"pdfs": len(list((DATA / "sources").glob("*.pdf")))},
        "sampleDocuments": len(list((DATA / "books").glob("*.docx"))),
    }

    grades = []
    for g in grades_present:
        rows = [r for r in subject_grades if r["grade"] == g]
        grades.append({
            "id": g,
            "name": l3["gradeNames"].get(g, g),
            "l1Subjects": sum(1 for r in rows if r["l1Indicators"] is not None),
            "l1Indicators": sum(r["l1Indicators"] or 0 for r in rows),
            "l2Subjects": sum(1 for r in rows if r["l2LessonSlots"]),
            "l2LessonSlots": sum(r["l2LessonSlots"] for r in rows),
            "l3Subjects": sum(1 for r in rows if r["l3BundleIndicators"] is not None),
            "l3Indicators": sum(r["l3BundleIndicators"] or 0 for r in rows),
            "hasSchedules": g in l3["scheduleGrades"],
        })

    subjects = []
    for sid in subjects_present:
        rows = [r for r in subject_grades if r["subjectId"] == sid]
        subjects.append({
            "id": sid,
            "name": rows[0]["subjectName"],
            "grades": [r["grade"] for r in rows],
            "l1Indicators": sum(r["l1Indicators"] or 0 for r in rows),
            "l2LessonSlots": sum(r["l2LessonSlots"] for r in rows),
            "l3Indicators": sum(r["l3BundleIndicators"] or 0 for r in rows),
            "l2Grades": [r["grade"] for r in rows if r["l2LessonSlots"]],
        })

    fidelity_totals = {}
    for field in FIDELITY_FIELDS:
        num = sum(v["distinct"][field] for v in l2_raw.values())
        den = sum(v["lessons"] for v in l2_raw.values()) or 1
        fidelity_totals[field] = round(num / den, 3)

    # ── CHECKS
    # Two classes of finding, deliberately separated:
    #   errors  -> the *portal* (this repository's live product) cannot serve the
    #              dataset, or a layer is missing/broken. These block a release.
    #   legacy  -> the retired NCOS kernel app under legacy/kernel-app. It is kept
    #              for reference only (nothing imports it); its module manifest is
    #              reported, never treated as a failure of the current portal.
    module_ids = {m["id"] for m in modules.values() if m["id"]}
    pair_set = set(universe)
    legacy = []
    for row in subject_grades:
        sid, g = row["subjectId"], row["grade"]
        if sid in INTENTIONALLY_UNSERVED:
            continue
        if l3["built"] and row["l3BundleIndicators"] is None:
            errors.append(f"{sid} {g} is not in the app bundle — the portal cannot serve it")
        if sid not in module_ids and (row["l1Indicators"] or row["l2LessonSlots"] or row["l3BundleIndicators"]):
            layers = []
            if row["l1Indicators"] is not None:
                layers.append(f"L1 {row['l1Indicators']} indicators")
            if row["l2LessonSlots"]:
                layers.append(f"L2 {row['l2LessonSlots']} lesson slots")
            if row["l3BundleIndicators"] is not None:
                layers.append(f"L3 {row['l3BundleIndicators']} indicators")
            legacy.append(f"{sid} {g} has data ({', '.join(layers)}) but the legacy app "
                          f"declares no module id '{sid}' — the portal does not use modules")

    for name, m in sorted(modules.items()):
        if not m["id"]:
            continue
        if m["id"] not in subjects_present:
            near = [s for s in subjects_present if s.startswith(m["id"][:4])]
            legacy.append(f"{name} declares id '{m['id']}' which is not a dataset subject id"
                          + (f" (the dataset uses '{near[0]}')" if near else ""))
            continue
        for g in m["grades"]:
            if (m["id"], g) not in pair_set:
                legacy.append(f"{name} declares grade {g} which no layer has for '{m['id']}'")
        slots = sum(r["l2LessonSlots"] for r in subject_grades if r["subjectId"] == m["id"])
        if slots and "record_of_work" not in m["capabilities"]:
            legacy.append(f"{name} does not declare 'record_of_work' although L2 has {slots} lesson slots")
        if m["validateIsStub"]:
            legacy.append(f"{name} validate() returns [] unconditionally — legacy boot cannot catch bad ids")
    if legacy:
        warnings.append(f"legacy app (legacy/kernel-app) is out of step with the dataset in "
                        f"{len(legacy)} places — it is retired reference code, so this does not "
                        "fail the audit; see checks.legacy in data/inventory.json")

    for key, v in sorted(l1.items()):
        if (not v["summaryOnly"] and v["summaryIndicators"] is not None
                and v["dbIndicators"] is not None and v["summaryIndicators"] != v["dbIndicators"]):
            warnings.append(f"{key[0]} {key[1]}: summary claims {v['summaryIndicators']} indicators, "
                            f"{v['dbs'][0]} contains {v['dbIndicators']}")
        if v["summaryOnly"]:
            warnings.append(f"{key[0]} {key[1]}: L1 has a summary but no database in data/curriculum/ "
                            f"(the database only exists in data/reference/)")
        elif not v["summaryFile"]:
            warnings.append(f"{key[0]} {key[1]}: L1 database {v['dbs'][0]} has no summary (no source URL, no counts)")

    for mismatch in grade_mismatches:
        warnings.append(f"grade mismatch — {mismatch}")

    if totals["reference"]["suppliesBundlePairs"]:
        warnings.append(
            f"{len(totals['reference']['suppliesBundlePairs'])} app-bundle subject-grades exist ONLY in "
            f"data/reference/ and have no audited L1 counterpart: "
            + ", ".join(totals["reference"]["suppliesBundlePairs"])
        )
    if totals["reference"]["bundlePairsWithoutAnySource"]:
        errors.append("app-bundle subject-grades with no source in L1 or data/reference: "
                      + ", ".join(totals["reference"]["bundlePairsWithoutAnySource"]))
    if ref_malformed:
        warnings.append(f"data/reference/ has {len(ref_malformed)} summary files with no counts block "
                        f"(e.g. {ref_malformed[0]})")

    for sid in sorted(INTENTIONALLY_UNSERVED):
        if sid not in subjects_present:
            warnings.append(f"INTENTIONALLY_UNSERVED lists '{sid}' but no layer has that subject")

    if l3["built"] and not l3.get("hasQuestions"):
        legacy.append("public/curriculum/questions/ does not exist, yet the legacy math module "
                      "declares the 'questions' capability")
    if not l3["built"]:
        errors.append("public/curriculum/ is not built — run `make build-curriculum`")

    for ref_path, users in check_doc_links().items():
        warnings.append(f"{ref_path} is referenced by {', '.join(users)} but does not exist")

    inventory = {
        "schema": 3,
        "generatedBy": "scripts/build_inventory.py",
        "layers": {
            "L1_curriculum": "data/curriculum/ — audited extraction (DB + summary)",
            "L2_lessons": "data/lessons/ — teaching template filled per lesson slot",
            "L3_bundle": "public/curriculum/ — what the portal serves",
            "reference": "data/reference/ — second, partly-divergent copy; a silent fallback source, never a total",
        },
        "totals": totals,
        "grades": grades,
        "subjects": subjects,
        "subjectGrades": subject_grades,
        "lessonFidelity": {
            "note": "distinct values / lesson slots per field. 1.0 = every slot bespoke; "
                    "near 0 = one template value shared by every slot in that file.",
            "acrossDataset": fidelity_totals,
            "perFile": {k: {"lessons": v["lessons"], "ratio": v["distinctRatio"]} for k, v in sorted(l2_raw.items())},
        },
        "appCoverage": {
            "bundleBuilt": l3["built"],
            "bundleGrades": l3["grades"],
            "bundleScheduleGrades": l3.get("scheduleGrades", []),
            "modules": {m["id"]: {"grades": m["grades"], "capabilities": m["capabilities"], "file": f}
                        for f, m in sorted(modules.items()) if m["id"]},
            "intentionallyUnserved": INTENTIONALLY_UNSERVED,
            "notInBundle": sorted(f"{r['subjectId']} {r['grade']}" for r in subject_grades
                                  if l3["built"] and r["l3BundleIndicators"] is None
                                  and r["subjectId"] not in INTENTIONALLY_UNSERVED),
        },
        "checks": {"errors": errors, "warnings": warnings, "legacy": legacy},
    }
    OUT.write_text(json.dumps(inventory, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    if not args.quiet:
        print_report(inventory)
    return 1 if errors else 0


def print_report(inv: dict) -> None:
    t = inv["totals"]
    l1, l2, l3, ref = t["l1"], t["l2"], t["l3"], t["reference"]
    print(f"Dataset inventory — derived from data/, written to {OUT.relative_to(ROOT)}\n")
    print("Three layers, three different truths:")
    print(f"  L1 curriculum  {l1['subjectGrades']:3} subject-grades  {l1['indicators']:5,} indicators   "
          f"({l1['databases']} DB files, {l1['summaries']} summaries)")
    print(f"  L2 lessons     {l2['subjectGrades']:3} subject-grades  {l2['lessonSlots']:5,} lesson slots "
          f"({l2['files']} files, {l2['subjects']} subjects, {l2['grades']} grades)")
    print(f"  L3 bundle      {l3['subjectGrades']:3} subject-grades  {l3['indicators']:5,} indicators   "
          f"({l3['grades']} grades, {l3['megabytes']} MB — what the portal serves)")
    print(f"  reference      {ref['databases']:3} DB files, {ref['summaries']} summaries, "
          f"{len(ref['suppliesBundlePairs'])} of which back an L3 pair with no L1 counterpart")
    print(f"  sources        {t['sources']['pdfs']} NaCCA PDFs · {t['sampleDocuments']} sample .docx\n")

    print("Coverage by grade")
    print(f"  {'grade':6} {'L1 subj':>8} {'L1 ind':>7} {'L2 files':>9} {'L2 slots':>9} {'L3 subj':>8} {'L3 ind':>7}  schedules")
    for g in inv["grades"]:
        print(f"  {g['id']:6} {g['l1Subjects']:8} {g['l1Indicators']:7} {g['l2Subjects']:9} {g['l2LessonSlots']:9} "
              f"{g['l3Subjects']:8} {g['l3Indicators']:7}  {'yes' if g['hasSchedules'] else '-'}")

    print(f"\nLesson-field fidelity across all {l2['lessonSlots']:,} slots (distinct / slots)")
    for field, ratio in sorted(inv["lessonFidelity"]["acrossDataset"].items(), key=lambda kv: -kv[1]):
        print(f"  {field:15} {ratio * 100:5.1f}%  {'#' * max(1, round(ratio * 40))}")

    if inv["checks"].get("legacy"):
        print(f"\n  LEGACY ({len(inv['checks']['legacy'])}) — retired NCOS app vs the dataset "
              "(reference only, does not fail the audit):")
        for item in inv["checks"]["legacy"][:6]:
            print(f"    - {item}")
        if len(inv["checks"]["legacy"]) > 6:
            print(f"    … {len(inv['checks']['legacy']) - 6} more in data/inventory.json")
    if inv["checks"]["errors"]:
        print(f"\n  ERRORS ({len(inv['checks']['errors'])}) — the portal cannot serve this dataset:")
        for e in inv["checks"]["errors"]:
            print(f"    x {e}")
    if inv["checks"]["warnings"]:
        print(f"\n  WARNINGS ({len(inv['checks']['warnings'])}):")
        for w in inv["checks"]["warnings"]:
            print(f"    ! {w}")
    if not inv["checks"]["errors"] and not inv["checks"]["warnings"]:
        print("\n  Dataset and app agree.")


if __name__ == "__main__":
    sys.exit(main())
