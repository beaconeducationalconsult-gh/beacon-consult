#!/usr/bin/env python3
"""Promote the reference-only subject-grades into the audited layer, data/curriculum/.

`data/reference/` is a *fallback*: `find_data()` reads it after `data/curriculum/`,
Audit A enumerates only `data/curriculum/`, and the inventory counts it as a
separate, partly-divergent copy.  Nine subject-grades lived there and nowhere else:

    computing B4, B5, B6      french B4, B5, B6      kindergarten KG1, KG2
    english-language B5

They are real NaCCA curriculum — their sources are in `data/sources/`, they pass
Audit B (which resolves databases through `find_data`), and their text fields have
been cleaned against their prints (`fix_reference_structure.py`,
`fix_french_content_standards.py`, `fix_reference_text.py`).  What was missing is
the layer: a copy under `data/curriculum/`, and a summary with the `counts` block
every other summary carries.

This script moves the audited database and the summary of each of those nine, and
writes the summaries that L1 is missing (`english-language B4`'s summary is in
`data/reference/`, `mathematics B1` has none):

* a summary keeps its `id`, `name`, `grade`, `sourceTitle` and `sourceUrl` — the
  provenance is not rewritten, only the counts are added;
* `counts` and the per-strand breakdown are *derived from the database* in the same
  shape the audited summaries use (`strands`, `subStrands`, `standards`,
  `indicators`), so a summary can always be re-derived and checked;
* the vestigial `sourceVerified` flag the eight summaries carried is dropped: it is
  read by nothing, and it says `false` about subject-grades Audit B passes.  What
  the portal shows comes from `data/audit/` (see `build_app_curriculum.py`).

Report only by default; pass `--apply` to move the files and write the summaries.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import CURRICULUM, REFERENCE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# the subject-grades whose database must move into data/curriculum/
PROMOTE = [
    ("computing", "B4"), ("computing", "B5"), ("computing", "B6"),
    ("french", "B4"), ("french", "B5"), ("french", "B6"),
    ("kindergarten", "KG1"), ("kindergarten", "KG2"),
    ("english-language", "B5"),
]

# L1 pairs whose *summary* is missing from data/curriculum/ although the database
# is there (TODO P1-2).  `None` means "write one, taking the provenance from the
# sibling grade of the same document".
SUMMARY_ONLY = [
    ("english-language", "B4", None),
    ("mathematics", "B1", ("mathematics", "B2")),
]

# the B1 databases are named after the document, not the subject id
B1_PREFIX = {"mathematics": "math", "science": "science", "english-language": "english"}


def db_name(subject: str, grade: str) -> str:
    if grade == "B1":                        # the B1 files are named for the document
        return f"{B1_PREFIX.get(subject, subject)}_curriculum_db_clean.json"
    return f"{subject}_{grade}_curriculum_db_clean.json"


def summary_name(subject: str, grade: str) -> str:
    if grade == "B1":
        return f"{B1_PREFIX.get(subject, subject)}_curriculum_summary.json"
    return f"{subject}_{grade}_curriculum_summary.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def find_in(*dirs: Path, name: str) -> Path | None:
    for base in dirs:
        p = base / name
        if p.exists():
            return p
    return None


def strand_code(subject: str, grade: str, strand_no: int) -> str:
    """`B4.1` / `K1.1` — the letter and grade digit as the codes print them."""
    letter = "K" if grade.startswith(("K", "KG")) else "B"
    digit = grade[-1]
    return f"{letter}{digit}.{strand_no}"


def strand_label(named: str, code: str) -> str:
    """The strand's name without its own numbering (`1. WORD PROCESSING`)."""
    text = re.sub(r"^\s*\d+\s*[.):-]?\s*", "", (named or "").strip()).strip()
    text = re.sub(r"\s+", " ", text)
    return text or code


def counts_of(data: dict) -> tuple[dict, list[dict]]:
    """(counts, per-strand breakdown) derived from the database itself."""
    standards: set[str] = set()
    sub_strands: set[tuple[int, int]] = set()
    per: dict[int, dict] = {}
    for code, rec in data.items():
        strand_no, sub_no, cs = code_parts_of(code, rec)
        entry = per.setdefault(strand_no, {"subs": set(), "standards": set(), "n": 0})
        entry["subs"].add(sub_no)
        entry["standards"].add(cs)
        entry["n"] += 1
        standards.add(cs)
        sub_strands.add((strand_no, sub_no))
    rows = [{"code": str(no), "name": "", "subStrands": len(v["subs"]),
             "standards": len(v["standards"]), "indicators": v["n"]}
            for no, v in sorted(per.items())]
    counts = {"strands": len(per), "subStrands": len(sub_strands),
              "standards": len(standards), "indicators": len(data)}
    return counts, rows


def code_parts_of(code: str, rec: dict) -> tuple[int, int, str]:
    """(strand number, sub-strand number, standard code) for one record."""
    # `B4.1.2.1.6` and `K1.3.2.1.4`: the first component is the grade, the second
    # the strand, the third the sub-strand — the summary counts the last two
    m = re.match(r"^[BK]\s*\d+\s*\.\s*(\d+)\s*\.\s*(\d+)", code)
    if m:
        strand, sub = int(m.group(1)), int(m.group(2))
    else:                                   # no code shape to read: fall back to fields
        strand = int(re.sub(r"\D", "", str(rec.get("strand") or "0")) or 0)
        sub = 0
    cs = rec.get("cs_code") or code.rsplit(".", 1)[0]
    return strand, sub, cs


def planned_summary(subject: str, grade: str, data: dict, old: dict) -> dict:
    """The summary as it should stand: provenance kept, counts derived."""
    counts, rows = counts_of(data)
    names = {}
    for code, rec in data.items():
        strand_no, _sub, _cs = code_parts_of(code, rec)
        names.setdefault(strand_no, strand_label(rec.get("strand"), code))
    for row in rows:
        no = int(row["code"])
        code = strand_code(subject, grade, no)
        row.update({"code": code, "name": strand_label(names.get(no), code)})
    out = {k: old[k] for k in ("id", "name", "grade", "sourceTitle", "sourceUrl")
           if k in old}
    out.setdefault("id", subject)
    out.setdefault("name", subject.replace("-", " ").title())
    out["grade"] = grade
    out["counts"] = counts
    out["strands"] = rows
    return out


def queue(writes: list, path: Path, payload: dict, who: str) -> bool:
    """Add a summary to the write list only when its content would change."""
    if path.exists():
        try:
            if json.loads(path.read_text()) == payload:
                return False
        except ValueError:
            pass
    writes.append((path, payload, who))
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true",
                    help="move the files and write the summaries (default: report)")
    args = ap.parse_args()

    print("promote_reference_subjects — move the reference-only layer into L1")
    print("=" * 72)
    moves: list[tuple[Path, Path, str]] = []
    writes: list[tuple[Path, dict, str]] = []
    notes: list[str] = []

    print("\nthe nine subject-grades")
    for subject, grade in PROMOTE:
        db = find_in(CURRICULUM, REFERENCE, name=db_name(subject, grade))
        summ = find_in(CURRICULUM, REFERENCE, name=summary_name(subject, grade))
        if db is None:
            notes.append(f"{subject} {grade}: no database found — skipped")
            continue
        data = read_json(db)
        old = read_json(summ) if summ else {}
        new = planned_summary(subject, grade, data, old)
        where = db.parent.name
        print(f"  {subject:16s} {grade:4s} db={db.name:52s} in {where}")
        print(f"  {'':16s} {'':4s} summary={summ.name if summ else '--':52s}"
              f" n={len(data):4d} strands={new['counts']['strands']} "
              f"subStrands={new['counts']['subStrands']} "
              f"standards={new['counts']['standards']}")
        if old.get("counts") and old["counts"] != new["counts"]:
            print(f"  {'':16s} {'':4s} ! summary says {old['counts']}")
            notes.append(f"{subject} {grade}: summary counts disagreed with the "
                         f"database (rewritten from the database)")
        if old and "sourceVerified" in old:
            print(f"  {'':16s} {'':4s} - dropping the vestigial "
                  f"`sourceVerified: {old['sourceVerified']}`")
        for path in (db, summ):
            if path is not None and path.parent != CURRICULUM:
                moves.append((path, CURRICULUM / path.name, f"{subject} {grade}"))
        queue(writes, CURRICULUM / summary_name(subject, grade), new,
              f"{subject} {grade}")

    print("\nsummaries L1 is missing (TODO P1-2)")
    for subject, grade, donor in SUMMARY_ONLY:
        db = find_in(CURRICULUM, REFERENCE, name=db_name(subject, grade))
        if db is None:
            notes.append(f"{subject} {grade}: no database found — skipped")
            continue
        data = read_json(db)
        old = {}
        if donor is not None:
            dsub, dgrade = donor
            src = find_in(CURRICULUM, REFERENCE, name=summary_name(dsub, dgrade))
            if src is None:
                notes.append(f"{subject} {grade}: no sibling summary to take the "
                             f"provenance from — skipped")
                continue
            old = {k: v for k, v in read_json(src).items()
                   if k in ("sourceTitle", "sourceUrl")}
            print(f"  {subject:16s} {grade:4s} provenance from {src.name}")
        else:
            src = find_in(CURRICULUM, REFERENCE, name=summary_name(subject, grade))
            if src is not None and src.parent != CURRICULUM:
                old = read_json(src)
                moves.append((src, CURRICULUM / src.name, f"{subject} {grade}"))
                print(f"  {subject:16s} {grade:4s} moving {src.name} from "
                      f"{src.parent.name}")
            elif src is not None:
                print(f"  {subject:16s} {grade:4s} {src.name} is already in place")
                continue
        new = planned_summary(subject, grade, data, old)
        print(f"  {'':16s} {'':4s} {summary_name(subject, grade)} n={len(data)} "
              f"strands={new['counts']['strands']} "
              f"standards={new['counts']['standards']}")
        queue(writes, CURRICULUM / summary_name(subject, grade), new,
              f"{subject} {grade}")

    fresh = [w for w in writes if not w[0].exists()]
    edits = [w for w in writes if w[0].exists()]
    print(f"\nto move: {len(moves)} file(s)")
    print(f"to write: {len(fresh)} new summary file(s), {len(edits)} whose content "
          f"would change")
    for path, _payload, _who in edits:
        print(f"  rewrite {path.name}")

    leftovers = []
    for subject, grade in PROMOTE:
        name = db_name(subject, grade)
        m = re.match(r"^(.+)_(B\d|KG\d)_curriculum_db_clean\.json$", name)
        if not m:
            continue
        stem = f"{m.group(1)}_{m.group(2)}"
        for path in sorted(REFERENCE.glob(f"{stem}_*.json")):
            if path.name not in (name, summary_name(subject, grade)):
                leftovers.append(path.name)
    if leftovers:
        print(f"\nreference copies left behind (not the audited extraction): "
              f"{len(leftovers)}")
        for name in leftovers[:10]:
            print(f"  {name}")

    for note in notes:
        print(f"! {note}")

    if not args.apply:
        print("\n(report only; pass --apply to move the files and write the summaries)")
        return 0

    for src, dst, _who in moves:
        if dst.exists():
            raise SystemExit(f"refusing to overwrite {dst}")
        CURRICULUM.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    for path, payload, _who in writes:
        path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"\nmoved {len(moves)} file(s) into data/curriculum/, wrote {len(writes)} "
          f"summaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
