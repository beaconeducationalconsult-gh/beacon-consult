#!/usr/bin/env python3
"""Validate `data/questions/` and serve it as part of the curriculum bundle (P1-5).

Before this script, the question bank was a dead file: `data/questions/mathematics/
B4.json` held hand-written questions that nothing read, and `public/curriculum/
questions/` did not exist — so the app's quiz and paper flows rendered an empty
selection from an empty bank.

What it does, per subject-grade:

  1. **Collects** the authored file (`data/questions/<subject>/<grade>.json`) and the
     generated one (`<grade>.generated.json`) — authored items first, and an id
     clash between the two is a hard error rather than a silent overwrite.
  2. **Validates every item against the served curriculum** — the indicator code
     must exist in `public/curriculum/<grade>_indicators.json`, and the item must
     be answerable: an MCQ needs two or more options with its answer among them,
     anything else needs an answer, every item needs a prompt and marks.
  3. **Writes the bundle**: `public/curriculum/questions/<subject>/<grade>.json`
     and an index with the counts and coverage the app reads.

Coverage is the honest headline: how many of the served indicators have at least
one question. It prints per subject-grade and in total, and writes it into the
index.

    python3 scripts/build_question_bank.py            # report
    python3 scripts/build_question_bank.py --apply    # write public/curriculum/questions/
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "public" / "curriculum"
QUESTIONS = ROOT / "data" / "questions"
OUT = BUNDLE / "questions"

REQUIRED = ("id", "indicatorCode", "prompt", "type", "marks")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def bundle_indicators(subject: str, grade: str) -> dict[str, dict]:
    """The served indicators **of one subject**, keyed by code.

    Subject-scoped on purpose: a mathematics question must hang off a mathematics
    indicator, and coverage has to be measured against the indicators a bank for
    that subject could actually cover — not the whole grade's.
    """
    path = BUNDLE / f"{grade.lower()}_indicators.json"
    if not path.exists():
        return {}
    return {row["code"]: row for row in load(path) if row.get("subjectId") == subject}


def check_item(item: dict, indicators: dict[str, dict], where: str) -> list[str]:
    problems = []
    for field in REQUIRED:
        if item.get(field) in (None, ""):
            problems.append(f"{where}: item {item.get('id') or '?'} has no {field}")
    if problems:
        return problems

    indicator = indicators.get(item["indicatorCode"])
    if indicator is None:
        problems.append(f"{where}: {item['indicatorCode']} is not a served indicator "
                        f"in this grade — the question would be an orphan in the app")
    if item["type"] == "mcq":
        options = item.get("options") or []
        if len(options) < 2:
            problems.append(f"{where}: {item['id']} is an MCQ with {len(options)} option(s)")
        elif str(item.get("answer")) not in [str(o) for o in options]:
            problems.append(f"{where}: {item['id']} answer {item.get('answer')!r} is not one of its options")
        elif len(set(map(str, options))) != len(options):
            problems.append(f"{where}: {item['id']} repeats an option")
    elif not str(item.get("answer") or "").strip():
        problems.append(f"{where}: {item['id']} has no answer")
    if not isinstance(item.get("marks"), int) or item["marks"] < 1:
        problems.append(f"{where}: {item['id']} marks must be a positive whole number")
    return problems


def sources(subject: str, grade: str) -> list[tuple[str, Path]]:
    """(kind, path) for the authored and generated files of one subject-grade."""
    found = []
    authored = QUESTIONS / subject / f"{grade}.json"
    if authored.exists():
        found.append(("authored", authored))
    generated = QUESTIONS / subject / f"{grade}.generated.json"
    if generated.exists():
        found.append(("generated", generated))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write public/curriculum/questions/")
    args = ap.parse_args()

    if not QUESTIONS.exists():
        sys.exit(f"No data/questions/ at {QUESTIONS}")

    problems: list[str] = []
    files: dict[tuple[str, str], dict] = {}

    pairs = sorted({(p.parent.name, p.name.replace(".generated.json", "").replace(".json", ""))
                    for p in QUESTIONS.glob("*/*.json")})
    for subject, grade in pairs:
        indicators = bundle_indicators(subject, grade)
        where = f"{subject} {grade}"
        if not indicators:
            problems.append(f"{where}: no served curriculum for this grade — cannot validate")
            continue

        items, seen = [], {}
        for kind, path in sources(subject, grade):
            payload = load(path)
            if isinstance(payload, list):  # the pre-2026-09-19 shape
                problems.append(f"{path.relative_to(ROOT)} is in the old list shape — "
                                f"expected {{subjectId, grade, items: [...]}}")
                continue
            for item in payload.get("items", []):
                item = dict(item)
                item.setdefault("source", kind)
                if item["id"] in seen:
                    problems.append(f"{where}: duplicate id {item['id']} "
                                    f"(in both {seen[item['id']]} and {kind})")
                    continue
                seen[item["id"]] = kind
                items.append(item)

        problems.extend(p for item in items for p in check_item(item, indicators, where))

        covered = len({i["indicatorCode"] for i in items})
        by_source = defaultdict(int)
        for item in items:
            by_source[item["source"].split(":")[0]] += 1
        files[(subject, grade)] = {
            "subjectId": subject,
            "grade": grade,
            "items": items,
            "indicators": len(indicators),
            "coveredIndicators": covered,
            "bySource": dict(by_source),
        }
        marks = sum(i["marks"] for i in items)
        print(f"  {subject:12} {grade:4} {len(items):4} questions · "
              f"{covered:3}/{len(indicators):3} indicators covered "
              f"({covered / max(1, len(indicators)) * 100:4.0f}%) · {marks:4} marks  "
              + " ".join(f"{k}={v}" for k, v in sorted(by_source.items())))

    total_items = sum(f["items"].__len__() for f in files.values())
    total_indicators = sum(f["indicators"] for f in files.values())
    total_covered = sum(f["coveredIndicators"] for f in files.values())

    served_indicators = sum(len(load(path)) for path in BUNDLE.glob("*_indicators.json"))
    print(f"\n{total_items} questions · {total_covered} of {total_indicators} "
          f"indicators in the covered subject-grades "
          f"({total_covered / max(1, total_indicators) * 100:.0f}%) · "
          f"{served_indicators} indicators served overall")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems[:25]:
            print(f"  x {problem}")
        if len(problems) > 25:
            print(f"  … and {len(problems) - 25} more")
        return 1
    if not total_items:
        print("\nNo questions to build — run scripts/generate_question_bank.py --apply "
              "or add authored items.")
        return 0

    if not args.apply:
        print("\nreport only — pass --apply to write public/curriculum/questions/")
        return 0

    for (subject, grade), payload in files.items():
        out_dir = OUT / subject
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{grade}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8")

    index = {
        "built": True,
        "generatedBy": "scripts/build_question_bank.py",
        "subjects": {
            subject: {
                grade: {"questions": len(payload["items"]),
                        "indicators": payload["indicators"],
                        "coveredIndicators": payload["coveredIndicators"]}
                for (s, grade), payload in sorted(files.items()) if s == subject
            }
            for subject in sorted({s for s, _ in files})
        },
        "totals": {
            "questions": total_items,
            "indicatorsInPacks": total_indicators,
            "indicatorsCovered": total_covered,
            "indicatorsServed": served_indicators,
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    print(f"\nWrote {len(files)} subject-grade file(s) and _index.json to "
          f"{OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
