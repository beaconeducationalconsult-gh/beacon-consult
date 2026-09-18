#!/usr/bin/env python3
"""Take the print's exemplar tail back off `ind_desc`.

`ind_desc` is the indicator, and several extractions read past the end of it into
the print's exemplar column — the numbered teaching steps that follow the
indicator in the same cell of an "INDICATORS AND EXEMPLARS" table. Two shapes are
in the databases today, and both are visible in every generated document:

    1. the tail repeats the indicator, so the field reads as a stutter
       `Describe ways of maintaining personal hygiene 1. In groups, discuss ways
        of maintaining personal hygiene`
    2. the tail is only the exemplar's own introduction, left dangling
       `Study some visual artworks … in the people of Africa Learners are to`

This script cuts the field back to the indicator — the text the print sets
*before* the exemplar begins — for records whose tail is one of those two shapes.
It never invents text: the replacement is always a prefix of what the record
already said, and the cut is made only when the print's own row carries the
indicator that would be left behind (`--no-verify` reports without checking, and
`--apply` refuses to write an unverified record).

The exemplar text is not thrown away: every removal is recorded in
`data/audit/ind_desc_exemplars.json`, before and after.

Exemplar tails that carry *content* the indicator does not (`Discuss food hygiene
1. Explain what is meant by food hygiene`, `Enquiry route: Which Europeans …`)
are reported, not cut — the field loses a sentence the database holds nowhere
else, and that is a decision about the data, not a cleanup.

Report by default, `--apply` to write.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fix_reference_text as F                                   # noqa: E402
from _paths import CURRICULUM, AUDIT                             # noqa: E402

# --------------------------------------------------------------------------- #
# what the print uses to introduce its exemplars

MARKERS = [
    ("numbered exemplar", re.compile(r"\s\d+\.\s")),
    ("learners are to", re.compile(r"\s(?:the\s+)?learners?\s+(?:are|is)\s+to\s*:?", re.I)),
    ("enquiry route", re.compile(r"\sEnquiry\s+route\s*:", re.I)),
    ("suggested process", re.compile(r"\sSuggested\s+process\s*/?\s*steps?", re.I)),
    ("e.g.", re.compile(r"\sE\.g\.\s*,?")),
    ("note", re.compile(r"\sNote\s*:")),
]

# The prints this reads, and the x band of their indicator column when the page
# does not draw its own rules (the bands the audit's cross-check already uses).
PRINTS = {
    "mathematics": (("B1", "B2", "B3"), "math_B1-B3.pdf", (140.0, 560.0)),
    "science": (("B1", "B2", "B3"), "science_B1-B3.pdf", (140.0, 560.0)),
    "english-language": (("B1", "B2", "B3"), "english_B1-B3.pdf", (140.0, 560.0)),
    "ghanaian-language": (("B1", "B2", "B3"), "gh_lang_b1b3.pdf", (140.0, 560.0)),
    "creative-arts": (("B1", "B2", "B3"), "creative_arts_B1-B3.pdf", (200.0, 545.0)),
    "owop": (("B1",), "owop_B1-B3.pdf", (140.0, 560.0)),
    "history": (("B1", "B2", "B3", "B4", "B5", "B6"), "history.pdf", (265.0, 610.0)),
    "rme": (("B1", "B2", "B3", "B4", "B5", "B6"), "rme_B1-B6.pdf", (140.0, 560.0)),
    "creative-arts|B4-B6": (("B4", "B5", "B6"), "creative_arts_B4-B6.pdf", (200.0, 545.0)),
    "computing|B4-B6": (("B4", "B5", "B6"), "computing_B4-B6.pdf", (190.0, 545.0)),
    "french|B4-B6": (("B4", "B5", "B6"), "french_B4-B6.pdf", (140.0, 560.0)),
    "mathematics|B4-B6": (("B4", "B5", "B6"), "mathematics_B4-B6.pdf", (140.0, 560.0)),
    "science|B4-B6": (("B4", "B5", "B6"), "science_B4-B6.pdf", (140.0, 560.0)),
    "english-language|B4-B6": (("B4", "B5", "B6"), "english_B4-B6.pdf", (140.0, 560.0)),
    "ghanaian-language|B4-B6": (("B4", "B5", "B6"), "ghanaian_language_B4-B6.pdf", (140.0, 560.0)),
    "owop|B4-B6": (("B4", "B5", "B6"), "owop_B4-B6.pdf", (140.0, 560.0)),
    "mathematics|B7-B9": (("B7", "B8", "B9"), "mathematics_CCP_B7-B9_draft.pdf", (140.0, 560.0)),
    "science|B7-B9": (("B7", "B8", "B9"), "science_CCP_B7-B9.pdf", (140.0, 560.0)),
    "english-language|B7-B9": (("B7", "B8", "B9"), "english_CCP_B7-B9.pdf", (140.0, 560.0)),
    "ghanaian-language|B7-B9": (("B7", "B8", "B9"), "ghanaian_language_CCP_B7-B9.pdf", (140.0, 560.0)),
    "rme|B7-B9": (("B7", "B8", "B9"), "rme_CCP_B7-B9.pdf", (140.0, 560.0)),
    "computing|B7-B9": (("B7", "B8", "B9"), "computing_CCP_B7-B9.pdf", (140.0, 560.0)),
    "career-technology": (("B7", "B8", "B9"), "career_tech_CCP_B7-B9.pdf", (220.0, 590.0)),
    "creative-arts-design": (("B7", "B8", "B9"), "creative_arts_design_CCP_B7-B9.pdf", (140.0, 560.0)),
    "french|B7-B9": (("B7", "B8", "B9"), "french_CCP_B7-B9.pdf", (140.0, 560.0)),
}

# B1 databases are named without their grade: `math_`, `english_`, `creative_arts_` …
B1_ALIAS = {"math": "mathematics", "science": "science", "english": "english-language",
            "ghanaian_language": "ghanaian-language", "history": "history",
            "owop": "owop", "rme": "rme", "creative_arts": "creative-arts"}

SUFFIX = "_curriculum_db_clean.json"


def subject_grade(name: str) -> tuple[str, str] | None:
    """(subject, grade) of a database file name.

    B1 databases have no grade in their name (`math_`, `creative_arts_`), which is
    why the stem is looked up in the alias table before the name is split.
    """
    if not name.endswith(SUFFIX):
        return None
    stem = name[: -len(SUFFIX)]
    if stem in B1_ALIAS:
        return B1_ALIAS[stem], "B1"
    subject, _, grade = stem.rpartition("_")
    return (subject, grade) if subject and grade.startswith(("B", "K")) else None


def print_for(subject: str, grade: str) -> str | None:
    """The NaCCA print a subject-grade was extracted from, by the audit's table.

    A key is either plain (`history`, one print for every grade it covers) or
    `subject|B4-B6` where the same subject was printed twice.
    """
    for key, (grades, pdf, band) in PRINTS.items():
        base, sep, span = key.partition("|")
        if base != subject or grade not in grades:
            continue
        if sep:
            lo, _, hi = span.partition("-")
            if not lo <= grade <= hi:
                continue
        F.WINDOW.setdefault(pdf, band)
        return pdf
    return None


# --------------------------------------------------------------------------- #
# reading one field

def split_marker(text: str) -> tuple[str, str, str] | None:
    """(marker name, text before it, text after it) — the print's own exemplar intro."""
    best = None
    for name, rx in MARKERS:
        m = rx.search(text)
        if m and (best is None or m.start() < best[1].start()):
            best = (name, m)
    if not best:
        return None
    name, m = best
    return name, text[:m.start()].strip(), text[m.end():].strip()


def longest_run(one: str, two: str) -> int:
    """The longest run of whole words `one` and `two` have in common."""
    a = re.sub(r"\W+", " ", one.lower()).split()
    b = re.sub(r"\W+", " ", two.lower()).split()
    best = 0
    for i in range(len(a)):
        for j in range(len(b)):
            k = 0
            while i + k < len(a) and j + k < len(b) and a[i + k] == b[j + k]:
                k += 1
            best = max(best, k)
    return best


def classify(head: str, tail: str) -> str | None:
    """Which of the two defect shapes this tail is — or none of them.

    A tail that mentions the indicator in passing is not a repeat: history's rows
    carry their whole cell (enquiry route, then a dozen steps that naturally name
    the topic), and cutting those would delete the only copy of that text. The
    artefact is a *short* tail that says the indicator back.
    """
    words = len(re.sub(r"\W+", " ", tail).split())
    if words < 3:
        return "dangling"                 # the exemplar's intro, and nothing after it
    head_words = len(re.sub(r"\W+", " ", head).split())
    run = longest_run(head, tail)
    if run >= 4 and run >= 0.5 * head_words and words <= 30:
        return "repeats"                  # the exemplar says the indicator again
    return None                           # real exemplar content: report, do not cut


_PAGE_TEXT: dict = {}


def page_text(pdf: str, page: int) -> str:
    """The page's indicator column, joined (cached — the page walk is the cost)."""
    key = (pdf, page)
    if key not in _PAGE_TEXT:
        _PAGE_TEXT[key] = F.compact(" ".join(t for _y, t in F.ind_lines(pdf, page)))
    return _PAGE_TEXT[key]


def pages_with(pdf: str, head: str) -> list[int]:
    """The pages whose indicator column carries the head, by its text.

    The prints number their rows irregularly (`B7.1.1.1. 2`, `B1 2 .2.3`) and set
    some tables a column to the left of others, so the code is not a reliable way
    to find a row; the indicator's own words are.
    """
    words = re.sub(r"\W+", " ", head).split()[:6]
    key = F.blob(" ".join(words)) if len(words) >= 4 else ""
    if not key:
        return []
    return [page for page in range(F.npages(pdf)) if key in F.blob(page_text(pdf, page))]


def printed_head(pdf: str, pages: list[int], head: str) -> tuple[str, float]:
    """(the print's text up to its exemplar marker, how close that is to `head`).

    Reading a row from the middle: the print sets the indicator, then one of the
    exemplar introductions, and this asks where the two meet. The comparison is
    on the folded text because the print breaks words as its lines tighten.
    """
    want = F.blob(head)
    n = len(want)
    if not n:
        return "", 0.0
    best = ("", 0.0)
    for page in pages:
        text = page_text(pdf, page)
        for _name, rx in MARKERS:
            for m in rx.finditer(text):
                before = F.blob(text[:m.start()])
                if len(before) < n - 2:
                    continue
                # the print sets the row's code and column heading in front of the
                # indicator, so the comparison starts at the text's own end
                for slack in (0, 8, 20):
                    tail = before[-(n + slack):] if slack else before[-n:]
                    ratio = difflib.SequenceMatcher(None, want, tail).ratio()
                    if ratio > best[1]:
                        best = (text[:m.start()][-220:], ratio)
    return best


def plan() -> tuple[list[dict], list[dict], dict]:
    """Every record with an exemplar tail: what to cut, what to report, the tally."""
    cut: list[dict] = []
    report: list[dict] = []
    tally: dict = {"files": {}, "cut": 0, "report": 0, "unverified": 0}
    for path in sorted(CURRICULUM.glob("*_curriculum_db_clean.json")):
        parsed = subject_grade(path.name)
        if not parsed:
            continue
        subject, grade = parsed
        pdf = print_for(subject, grade)
        records = json.loads(path.read_text())
        for code, record in records.items():
            text = record.get("ind_desc") or ""
            split = split_marker(text)
            if not split:
                continue
            marker, head, tail = split
            kind = classify(head, tail)
            entry = {"file": path.name, "code": code, "marker": marker,
                     "kind": kind or "content", "before": text,
                     "after": head if kind else text,
                     "removed": tail if kind else ""}
            if kind is None:
                report.append(entry)
                continue
            if not pdf or not head:
                entry["verified"] = False
                entry["reason"] = "no print" if not pdf else "nothing left"
                tally["unverified"] += 1
                cut.append(entry)
                continue
            pages = sorted(set(F.pages_of(pdf, code)) | set(pages_with(pdf, head)))
            want, ratio = printed_head(pdf, pages, head)
            entry["pages"] = pages[:6]
            entry["print_head"] = want[:300]
            entry["ratio"] = round(ratio, 3)
            if not pages:
                entry["verified"] = False
                entry["reason"] = "indicator not in the print"
                tally["unverified"] += 1
            elif ratio < 0.9:
                entry["verified"] = False
                entry["reason"] = f"print reads the lead differently ({ratio:.2f})"
                tally["unverified"] += 1
            else:
                entry["verified"] = True
            cut.append(entry)
        for entry in [e for e in cut if e["file"] == path.name]:
            tally["files"].setdefault(path.name, {"cut": 0, "report": 0, "unverified": 0})
            tally["files"][path.name]["cut" if entry.get("verified") else "unverified"] += 1
        tally["report"] += sum(1 for e in report if e["file"] == path.name)
        tally["files"].setdefault(path.name, {"cut": 0, "report": 0, "unverified": 0})
        tally["files"][path.name]["report"] = sum(1 for e in report if e["file"] == path.name)
    tally["cut"] = sum(1 for e in cut if e.get("verified"))
    return cut, report, tally


LESSONS = CURRICULUM.parent / "lessons"


def phrase_pattern(text: str) -> str:
    """`text` as a whole-phrase pattern that tolerates the print's spacing."""
    return r"(?<![A-Za-z0-9])" + r"\s*".join(re.escape(w) for w in text.split()) + r"(?![A-Za-z0-9])"


def swap(haystack: str, before: str, after: str) -> str | None:
    """`haystack` with its copy of `before` replaced by `after`, or None.

    The lesson template lower-cases the indicator's first letter where the database
    capitalises it, and it is the template that is being edited, so the case the
    text already has is the case it keeps.
    """
    m = re.search(phrase_pattern(before), haystack, re.I)
    if not m:
        return None
    got = m.group(0)
    repl = after
    if after and got:
        if got[0].isupper() != after[0].isupper():
            repl = after[0].swapcase() + after[1:]
    return haystack[:m.start()] + repl + haystack[m.end():]


def flat_run(run: dict) -> dict:
    """A history entry: what one run wrote, without the file-by-file detail."""
    return {"records": run.get("records", 0), "repeats": run.get("repeats", 0),
            "dangling": run.get("dangling", 0),
            "lesson_slots": run.get("lesson_slots", 0)}


def lesson_plan(cuts: list[dict]) -> list[dict]:
    """Lesson slots carrying one of the cleaned indicators (their `ind_desc` and
    the `perf_indicator` built from it)."""
    by_before = {F.compact(e["before"]): e for e in cuts if e.get("verified")}
    out = []
    for path in sorted(LESSONS.glob("*_lessons_enriched.json")):
        slots = json.loads(path.read_text())
        hits = []
        for slot in slots:
            entry = by_before.get(F.compact(slot.get("ind_desc") or ""))
            if not entry:
                continue
            after = entry["after"]
            slot_after = dict(slot)
            slot_after["ind_desc"] = after
            perf = swap(slot.get("perf_indicator") or "", entry["before"], after)
            if perf is not None:
                slot_after["perf_indicator"] = perf
            hits.append({"lesson_num": slot.get("lesson_num"), "ind_code": slot.get("ind_code"),
                         "before": slot.get("ind_desc"), "after": after,
                         "perf": perf is not None})
        if hits:
            out.append({"file": path.name, "slots": hits,
                        "slots_changed": len(hits),
                        "perf_changed": sum(1 for h in hits if h["perf"])})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write the cuts to the databases")
    ap.add_argument("--files", nargs="*", help="only these database files (names)")
    args = ap.parse_args()

    cut, report, tally = plan()
    if args.files:
        keep = set(args.files)
        cut = [e for e in cut if e["file"] in keep]
        report = [e for e in report if e["file"] in keep]
    lessons = lesson_plan(cut)

    print(f"{len(cut) + len(report)} record(s) carry the print's exemplar tail")
    print(f"  to cut   {sum(1 for e in cut if e.get('verified'))}"
          f"  (repeats {sum(1 for e in cut if e.get('verified') and e['kind'] == 'repeats')},"
          f" dangling {sum(1 for e in cut if e.get('verified') and e['kind'] == 'dangling')})")
    print(f"  report   {len(report)}  (exemplar content the indicator does not carry)")
    print(f"  skipped  {sum(1 for e in cut if not e.get('verified'))}  (print does not back the cut)")
    print(f"  lessons  {sum(e['slots_changed'] for e in lessons)} slot(s) in "
          f"{len(lessons)} lesson file(s) carry one of them")
    print()
    for name, row in sorted(tally["files"].items()):
        if row["cut"] or row["unverified"] or row["report"]:
            print(f"  {name:52s} cut {row['cut']:3d}  skipped {row['unverified']:3d}  report {row['report']:3d}")
    for entry in cut:
        if not entry.get("verified"):
            print(f"\n  SKIP {entry['file']} {entry['code']}: {entry.get('reason')}")
            if entry.get("print_head"):
                print(f"       print: {entry['print_head']}")
            print(f"       db   : {entry['before'][:200]}")

    audit = {"cut": cut, "report": report, "lessons": lessons,
             "applied": {"records": 0, "repeats": 0, "dangling": 0, "files": {},
                         "lesson_slots": 0, "lesson_files": {}}}
    if args.apply:
        by_file: dict[str, list[dict]] = {}
        for entry in cut:
            if entry.get("verified"):
                by_file.setdefault(entry["file"], []).append(entry)
        for name, entries in by_file.items():
            path = CURRICULUM / name
            data = json.loads(path.read_text())
            for entry in entries:
                data[entry["code"]]["ind_desc"] = entry["after"]
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            audit["applied"]["files"][name] = len(entries)
            audit["applied"]["records"] += len(entries)
            audit["applied"]["repeats"] += sum(1 for e in entries if e["kind"] == "repeats")
            audit["applied"]["dangling"] += sum(1 for e in entries if e["kind"] == "dangling")
        print(f"\napplied: {audit['applied']['records']} record(s) in "
              f"{len(by_file)} file(s)")
        for entry in lessons:
            path = LESSONS / entry["file"]
            slots = json.loads(path.read_text())
            by_num = {h["lesson_num"]: h for h in entry["slots"]}
            for slot in slots:
                hit = by_num.get(slot.get("lesson_num"))
                if not hit:
                    continue
                slot["ind_desc"] = hit["after"]
                if hit.get("perf"):
                    swapped = swap(slot.get("perf_indicator") or "", hit["before"], hit["after"])
                    if swapped is not None:
                        slot["perf_indicator"] = swapped
            path.write_text(json.dumps(slots, indent=1, ensure_ascii=False) + "\n")
            audit["applied"]["lesson_files"][entry["file"]] = entry["slots_changed"]
            audit["applied"]["lesson_slots"] += entry["slots_changed"]
        print(f"          {audit['applied']['lesson_slots']} lesson slot(s) in "
              f"{len(lessons)} lesson file(s)")
    AUDIT.mkdir(parents=True, exist_ok=True)
    path = AUDIT / "ind_desc_exemplars.json"
    keep = False
    if path.exists():
        try:
            old = json.loads(path.read_text())
        except ValueError:
            old = {}
        done = old.get("applied", {}).get("records", 0)
        # A later run finds nothing left to cut, and overwriting would replace the
        # record of what the cleanup did with an empty list (the trap the text
        # fixer's trail fell into). The file is only rewritten when it has no
        # applied run to lose, or when this run is itself writing one.
        keep = bool(done) and audit["applied"]["records"] == 0
        if keep:
            audit["history"] = [flat_run(h.get("applied", h))
                                for h in old.get("history", [])]
            audit["applied"] = old["applied"]
            audit["cut"] = old.get("cut", [])
            audit["report"] = old.get("report", audit["report"])
            audit["lessons"] = old.get("lessons", audit["lessons"])
    if args.apply and audit["applied"]["records"]:
        audit.setdefault("history", []).append(flat_run(audit["applied"]))
    path.write_text(json.dumps(audit, indent=1, ensure_ascii=False) + "\n")
    print(f"{'kept' if keep else 'wrote'} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
