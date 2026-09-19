#!/usr/bin/env python3
"""Drop records that were built from a print's front-matter notation example.

Every NaCCA print explains its own code scheme in the front matter, and that
explanation carries a worked example:

    The notation is indicated in Table 2. Example: B7/JHS1 .4.2.3.1
    ANNOTATION MEANING / REPRESENTATION …

An extraction that reads the whole document, rather than its body tables, can pick
that example up and manufacture a record from it. Two databases carry exactly that:
`data/reference/french_B7` and `data/reference/ghanaian-language_B7` each hold a
`B7.4.2.3.1` whose `cs_desc` is `"… Content Standard B7.4.2.3"` and whose `ind_desc`
is `"… Learning Indicator B7.4.2.3.1"` — labels copied out of the annotation table
itself. Neither print sets that indicator anywhere in its body.

This script removes such records. A record qualifies only when **all** of these hold:

* its `ind_desc` or `cs_desc` is that label form (it names its own code rather than
  describing anything);
* the code occurs **exactly once** in the whole print, tolerating the `/JHS1` year
  annotation the prints interpose (`B7/JHS1 .4.2.3.1`), and that occurrence is on a
  page that explains the notation (`Example:` / `ANNOTATION`);
* no page of the print carries the code as a row of its indicator column.

Anything else is reported, never deleted — in particular a record whose code the
print does carry but whose description was never filled in (that is a text problem,
not a fabricated record; the reference copies hold many of them).

Report by default, `--apply` to delete; every removal is written with its print
evidence to `data/audit/front_matter_records.json`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fix_reference_text as F                                   # noqa: E402
import fix_ind_desc_exemplars as X                               # noqa: E402
from _paths import CURRICULUM, REFERENCE, AUDIT                  # noqa: E402

LABEL_INDICATOR = re.compile(r"^[A-Z][A-Za-z ]*?Learning Indicator\s+[BK]?\s*\d[\d.\s]*$",
                             re.I)
LABEL_STANDARD = re.compile(r"^[A-Z][A-Za-z ]*?Content Standard\s+[BK]?\s*\d[\d.\s]*$", re.I)
NOTATION_PAGE = re.compile(r"Example\s*:|ANNOTATION", re.I)


def code_pattern(code: str) -> re.Pattern:
    """The record's code as the print may set it — `/JHS1` and spacing tolerated."""
    parts = re.findall(r"\d+", code)
    if len(parts) < 2:
        return re.compile(r"(?!x)x")               # matches nothing
    sep = r"[^\d]{0,8}"
    body = sep.join(re.escape(p) for p in parts[1:])
    return re.compile(r"(?<!\d)" + re.escape(parts[0])
                      + r"(?:\s*/\s*JHS\s*\d)?" + sep + body + r"(?!\d)")


def occurrences(pdf: str, code: str) -> list[tuple[int, str, bool]]:
    """[(page, the line it is on, whether the page explains the notation)]."""
    rx = code_pattern(code)
    out = []
    for page in range(F.npages(pdf)):
        text = " ".join(t for _y, t in F.page_lines(pdf, page, 0.0, 1_000.0))
        m = rx.search(text)
        if not m:
            continue
        line = text[max(0, m.start() - 90):m.end() + 60]
        out.append((page, line, bool(NOTATION_PAGE.search(text))))
    return out


def is_label(record: dict) -> bool:
    ind = (record.get("ind_desc") or "").strip()
    cs = (record.get("cs_desc") or "").strip()
    return bool(LABEL_INDICATOR.match(ind) or LABEL_STANDARD.match(cs))


def body_row(pdf: str, code: str) -> str:
    """What the print's indicator column sets for the code, if anything."""
    return F.compact(F.row_text_all(pdf, code))


def scan() -> tuple[list[dict], list[dict], dict]:
    """(records to drop, label-form records the print does carry, tallies)."""
    drop: list[dict] = []
    placeholder: list[dict] = []
    for layer, root in (("curriculum", CURRICULUM), ("reference", REFERENCE)):
        for path in sorted(root.glob("*_curriculum_db_clean.json")):
            parsed = X.subject_grade(path.name)
            if not parsed:
                continue
            subject, grade = parsed
            pdf = X.print_for(subject, grade)
            data = json.loads(path.read_text())
            for code, record in data.items():
                if not is_label(record):
                    continue
                entry = {"layer": layer, "file": path.name, "code": code,
                         "print": pdf, "record": record}
                if not pdf:
                    entry["reason"] = "no print"
                    placeholder.append(entry)
                    continue
                row = body_row(pdf, code)
                found = occurrences(pdf, code)
                entry["pages"] = [p for p, _l, _n in found]
                entry["print_line"] = found[0][1] if found else ""
                if row:
                    entry["reason"] = "the print carries the code as a row — its text needs filling"
                    placeholder.append(entry)
                    continue
                if len(found) == 1 and found[0][2]:
                    entry["front_matter_page"] = found[0][0]
                    entry["reason"] = "the print's front matter uses the code as its notation example"
                    drop.append(entry)
                    continue
                entry["reason"] = (f"{len(found)} occurrence(s) in the print, none a row"
                                   if found else "the code is not in the print at all")
                placeholder.append(entry)
    tally = {"drop": len(drop), "placeholder": len(placeholder),
             "drop_files": {}, "placeholder_files": {}}
    for entry in drop:
        tally["drop_files"][entry["file"]] = tally["drop_files"].get(entry["file"], 0) + 1
    for entry in placeholder:
        tally["placeholder_files"][entry["file"]] = \
            tally["placeholder_files"].get(entry["file"], 0) + 1
    return drop, placeholder, tally


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="delete the fabricated records")
    ap.add_argument("--details", action="store_true", help="print every record found")
    args = ap.parse_args()

    drop, placeholder, tally = scan()
    print(f"{len(drop)} record(s) built from a print's front-matter notation example")
    for entry in drop:
        print(f"  {entry['layer']:10s} {entry['file']:48s} {entry['code']}")
        print(f"       print says (p{entry['front_matter_page']}): {entry['print_line'].strip()[:110]}")
    for layer in ("curriculum", "reference"):
        n = sum(1 for e in placeholder if e["layer"] == layer)
        print(f"{n} label-form record(s) in {layer} — the prints carry the text, "
              f"so fill, do not drop")
    for name, count in sorted(tally["placeholder_files"].items()):
        print(f"  {name:52s} {count:3d}")
    if args.details:
        for entry in placeholder:
            print(f"  … {entry['layer']}/{entry['file']} {entry['code']}: {entry['reason']}")

    artifact = AUDIT / "front_matter_records.json"
    old: dict = {}
    if artifact.exists():
        try:
            old = json.loads(artifact.read_text())
        except ValueError:
            old = {}
    removed = list(old.get("removed", []))
    seen = {(e.get("layer"), e["file"], e["code"]) for e in removed}
    for entry in removed:                       # backfill what a new scan can no longer see
        if not entry.get("layer"):
            for new in drop:
                if (new["file"], new["code"]) == (entry["file"], entry["code"]):
                    entry["layer"] = new["layer"]
        if not entry.get("print"):
            parsed = X.subject_grade(entry["file"])
            entry["print"] = (X.print_for(*parsed) or "") if parsed else ""
    for entry in drop:
        key = (entry["layer"], entry["file"], entry["code"])
        if key not in seen:
            seen.add(key)
            removed.append({k: entry[k] for k in
                            ("layer", "file", "print", "code", "pages", "print_line",
                             "front_matter_page", "reason") if k in entry}
                           | {"record": entry.get("record", {})})
    audit = {"removed": removed,
             "placeholder": [{"layer": e["layer"], "file": e["file"], "code": e["code"],
                              "pages": e.get("pages", []), "reason": e["reason"]}
                             for e in placeholder] or old.get("placeholder", []),
             "applied": old.get("applied", {"records": 0, "files": {}})}

    if args.apply and drop:
        by_file: dict[str, list[dict]] = {}
        for entry in drop:
            by_file.setdefault((entry["layer"], entry["file"]), []).append(entry)
        for (layer, name), entries in by_file.items():
            path = (CURRICULUM if layer == "curriculum" else REFERENCE) / name
            data = json.loads(path.read_text())
            before = len(data)
            for entry in entries:
                data.pop(entry["code"], None)
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            audit["applied"]["files"][f"{layer}/{name}"] = {
                "removed": before - len(data), "records": len(data)}
            audit["applied"]["records"] += before - len(data)
            print(f"  dropped {before - len(data)} from {layer}/{name} "
                  f"({len(data)} records left)")
    AUDIT.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(audit, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
