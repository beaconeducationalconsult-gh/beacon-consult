#!/usr/bin/env python3
"""Fill the empty content-standard descriptions of the French B4-B6 databases.

Why this exists
---------------
The French B4-B6 databases (`data/reference/french_B{4,5,6}_curriculum_db_clean.json`)
came out of the extraction pass with `cs_desc` empty for 262 of their 267 records,
and the five values that are filled are harvested from *indicator* rows, not from
a content standard.

The reason is not a lost field: the French B4-B6 print does not carry
sentence-style content standards.  Its CONTENT STANDARDS column holds the four
skill areas, and the SCOPE AND SEQUENCE table (pp. xviii-xx) lists exactly those
four - in this order - for *every* sub-strand:

    1. Compréhension Orale      3. Compréhension Écrite
    2. Production Orale         4. Production Écrite

The front matter (p. xvii) fixes what the code digits mean:

    B4.1.2.3.1  ->  B4 = class, 1 = strand, 2 = sub-strand,
                    3 = CONTENT STANDARD number, 1 = indicator number

so the content standard of a record is fully determined by the fourth component
of its indicator code - which is what `cs_code` already carries.  This script
writes that label into `cs_desc`, and cross-checks the two claims above against
the PDF before it does (see `verify_against_pdf`).

What it writes
--------------
    cs_desc  =  the skill area named by the content-standard number

Only the three reference-only French databases are touched.  French B7-B9 is
left alone: those grades *do* print a content standard statement, and their
`cs_desc` is already filled (its own defects are tracked separately in
docs/TODO.md).

Anything it refuses to guess is reported instead: a code whose fourth component
is not 1-4 has no content standard to name.  `B6.1.2.5.3` is the one such record
- the print numbers a fifth content standard in a sub-strand that has four.

Requires: pypdf   (pip install pypdf)

Usage
-----
    python3 scripts/fix_french_content_standards.py            # report only
    python3 scripts/fix_french_content_standards.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from _paths import AUDIT, REFERENCE, SOURCES  # noqa: E402

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    sys.exit("pypdf is required:  pip install pypdf")

# The four content standards of the French B4-B6 curriculum, in the order the
# SCOPE AND SEQUENCE table prints them (and therefore in the order the content
# standard number counts them).
SKILLS = {
    "1": "Compréhension Orale",
    "2": "Production Orale",
    "3": "Compréhension Écrite",
    "4": "Production Écrite",
}

DB_GLOB = "french_B*_curriculum_db_clean.json"
GRADES = ("B4", "B5", "B6")
PDF = SOURCES / "french_B4-B6.pdf"
ARTIFACT = AUDIT / "french_content_standards.json"

# The print is not consistent about the shape of a label - it mixes case
# ("Production orale" / "Production Orale"), drops the space ("ProductionOrale")
# and wraps two-word labels over two lines - so every comparison happens on a
# form with the whitespace and the case removed.
KEY = lambda s: re.sub(r"\s+", "", (s or "").strip()).lower()  # noqa: E731
BY_KEY = {KEY(v): v for v in SKILLS.values()}
HEAD = re.compile(r"^(?:compr[ée]hension|production)$", re.I)
# "Compréhension Orale", "ProductionOrale", "compréhension écrite" - the print
# takes liberties with the spacing and the case.
LABEL_RE = re.compile(r"(?:compr[ée]hension|production)\s*(?:orale|écrite)", re.I)
WRAPPED_TAIL = re.compile(r"^(?:orale|écrite|ecrite)$", re.I)


def _page_items(page) -> list[tuple[float, float, str]]:
    """Every text item on the page with its position.

    `extract_text()` alone reads these tables row-wise and re-orders columns; the
    per-item coordinates let each *column* be read on its own.
    """
    items: list[tuple[float, float, str]] = []

    def visitor(text, cm, tm, fd, fs):
        t = (text or "").replace("\n", " ").strip()
        if t:
            items.append((round(tm[4], 1), round(tm[5], 1), t))

    page.extract_text(visitor_text=visitor)
    return items


def _join(frags: list[tuple[float, str]]) -> str:
    """Join the fragments of one visual line back into text.

    The extractor splits a line into as many runs as the PDF has positioning
    operations, sometimes mid-token (`B7/JHS1` + `.1.6.1`) and sometimes between
    words (`Comprendre` + `et` + `s’exprimer`), so a space goes between two runs
    unless one of them clearly continues the other.
    """
    out = ""
    for _x, t in frags:
        if not out:
            out = t
        elif out.endswith((".", "/", "’", "'", "-", "(")) or t[:1] in ".,;:)’":
            out += t
        else:
            out += " " + t
    return out


def _column_lines(items, x_min: float, x_max: float) -> list[tuple[float, str]]:
    """Visual lines (top-down) built only from items in one column band."""
    rows: dict[int, list[tuple[float, str]]] = {}
    for x, y, t in items:
        if x_min <= x < x_max:
            rows.setdefault(round(y / 2) * 2, []).append((x, t))
    return [(y, _join(sorted(rows[y]))) for y in sorted(rows, reverse=True)]


def _fold_wrapped(lines: list[tuple[float, str]]) -> list[tuple[float, str]]:
    """Fold a label the print wraps over two lines ("Compréhension" / "Orale").

    Only a head that is exactly one word of a label, followed immediately by a
    bare "Orale"/"Écrite", is folded - blanket line merging would glue unrelated
    rows together.
    """
    out: list[tuple[float, str]] = []
    i = 0
    while i < len(lines):
        y, text = lines[i]
        s = text.strip()
        if HEAD.match(s) and i + 1 < len(lines) and WRAPPED_TAIL.match(lines[i + 1][1].strip()):
            out.append((y, f"{s} {lines[i + 1][1].strip()}"))
            i += 2
        else:
            out.append((y, s))
            i += 1
    return out


def verify_against_pdf() -> dict:
    """Check the two prints this fix relies on.  Returns facts for the report."""
    reader = PdfReader(str(PDF))
    facts = {"pages": len(reader.pages), "scope_blocks": 0, "scope_pages": [],
             "scope_out_of_order": [], "body_label_counts": Counter(),
             "body_other_labels": []}

    # 1. SCOPE AND SEQUENCE (pp. xviii-xx): every sub-strand lists the four
    #    skills in order, in the CONTENT STANDARDS column (x ~ 415).
    for i in range(16, 22):
        text = reader.pages[i].extract_text() or ""
        if "CONTENT" not in text or "√" not in text:
            continue
        facts["scope_pages"].append(i + 1)
        # Match on content, not on a column band: the extractor glues the first
        # label of a block onto the sub-strand title in the next column across.
        seq = []
        for _y, line in _column_lines(_page_items(reader.pages[i]), 0, 100_000):
            for m in LABEL_RE.finditer(line):
                seq.append(BY_KEY[KEY(m.group(0))])
        # A page can open mid-block (the four labels of one sub-strand are not
        # kept together by the print), so try each phase and check the sequence
        # runs the canonical cycle from there.
        good = None
        for phase in range(4):
            if all(hit == SKILLS[str((phase + j) % 4 + 1)] for j, hit in enumerate(seq)):
                good = phase
                break
        if good is None:
            facts["scope_out_of_order"].append((i + 1, seq[:6] if seq else "no labels"))
        else:
            facts["scope_blocks"] += (good + len(seq)) // 4

    # 2. Body tables: the CONTENT STANDARDS column (x < 150) holds those same
    #    four labels and nothing else.
    for i in range(21, len(reader.pages)):
        page = reader.pages[i]
        if "INDICATOR" not in (page.extract_text() or "").upper():
            continue
        lines = [(y, t) for y, t in _column_lines(_page_items(page), 0, 150)
                 if t.strip() and not re.match(r"^©|^NaCCA|^CONTENT|^STANDARDS|^\d+$", t.strip())]
        for _y, label in _fold_wrapped(lines):
            s = label.strip()
            if not re.search(r"compr[ée]hension|production", s, re.I):
                continue
            hit = BY_KEY.get(KEY(s))
            if hit:
                facts["body_label_counts"][hit] += 1
            else:
                facts["body_other_labels"].append((i + 1, s))
    return facts


def plan_changes() -> tuple[list[dict], list[dict]]:
    """-> (per-file change plans, records that cannot be labelled)."""
    plans, unlabelled = [], []
    for grade in GRADES:
        path = REFERENCE / f"french_{grade}_curriculum_db_clean.json"
        if not path.exists():
            sys.exit(f"missing {path}")
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        plan = {"grade": grade, "path": path, "data": data, "fills": [],
                "already": 0, "displaced": [], "by_label": Counter()}
        for code, rec in data.items():
            parts = code.split(".")
            number = parts[3] if len(parts) == 5 else None
            label = SKILLS.get(number or "")
            if not label:
                unlabelled.append({"code": code, "cs_code": rec.get("cs_code"),
                                   "ind_desc": rec.get("ind_desc", "")[:80]})
                continue
            current = (rec.get("cs_desc") or "").strip()
            if KEY(current) == KEY(label):
                plan["already"] += 1
                continue
            if current:
                plan["displaced"].append({"key": code, "cs_code": rec.get("cs_code"),
                                          "was": current})
            plan["fills"].append((code, label))
            plan["by_label"][label] += 1
        plans.append(plan)
    return plans, unlabelled


# ── French B7-B9 ──────────────────────────────────────────────────────────────
# Those grades *do* print a content standard statement, and their `cs_desc` is
# filled - except where the extraction picked up the neighbouring column instead.
# The CORE COMPETENCIES column (x ~ 542) sits to the right of the CONTENT
# STANDARD column (x ~ 63), and every record of some content standards carries
# that column's text, plus one placeholder ("French Content Standard B9.2.3.1").
CCP_PDF = SOURCES / "french_CCP_B7-B9.pdf"
CCP_GRADES = ("B7", "B8", "B9")
CCP_WIDTH = 200.0        # right edge of the CONTENT STANDARD column
JUNK = re.compile(
    r"^(?:Communication and|Critical Thinking|Creativity and|Cultural identity"
    r"|Personal development|Digital literacy|Core Competenc)|French Content Standard", re.I)


def ccp_code(grade: str, cs_code: str) -> str:
    """B7.1.6.1 -> B7/JHS1.1.6.1 (the shape the B7-B9 print uses)."""
    jhs = {"B7": "JHS1", "B8": "JHS2", "B9": "JHS3"}[grade]
    tail = cs_code.split(".", 1)[1]          # 1.6.1
    return f"{grade}/{jhs}.{tail}"


CS_LINE = re.compile(r"^B\d\s*/\s*JHS\d\s*[.,]\s*\d+", re.I)


def recover_statements() -> list[dict]:
    """Read the content-standard statement printed for every junk-filled B7-B9 standard.

    -> [{grade, cs_code, printed, statement, page, misprinted, records}]

    `statement` is None when the print has no such content standard at all.
    """
    reader = PdfReader(str(CCP_PDF))
    pages: list[tuple[int, list[tuple[float, float, str]]]] = [
        (i + 1, _page_items(p)) for i, p in enumerate(reader.pages)]
    out = []

    for grade in CCP_GRADES:
        path = REFERENCE / f"french_{grade}_curriculum_db_clean.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        by_cs: dict[str, list[str]] = {}
        for code, rec in data.items():
            by_cs.setdefault(rec["cs_code"], []).append(code)
        broken = {cs: keys for cs, keys in by_cs.items()
                  if any(JUNK.search(data[k].get("cs_desc") or "") for k in keys)}
        for cs_code in sorted(broken):
            printed = ccp_code(grade, cs_code)
            hit = None
            for page_no, items in pages:
                cs_lines = _column_lines(items, 0, CCP_WIDTH)
                body_lines = _column_lines(items, CCP_WIDTH, 100_000)
                # the row's first indicator carries the same code plus a fifth
                # component; without it this is a cross-reference, not the
                # definition of the content standard
                ind_y = min((y for y, t in body_lines
                             if KEY(t).startswith(KEY(printed) + ".")), default=None)
                if ind_y is None:
                    continue
                # The content standard's own line is the last code-shaped line
                # above that row.  Matching on shape rather than on the exact
                # code catches the print's own mis-numbering - the statement of
                # B9.2.3.1 is labelled "B8/JHS2.2.3.1" in the B9 section.
                code_y, code_text = None, None
                for y, t in cs_lines:
                    if y >= ind_y and CS_LINE.match(t.strip()):
                        code_y, code_text = y, t.strip()
                if code_y is None:
                    continue
                body = [t for y, t in cs_lines if ind_y < y <= code_y]
                statement = re.sub(r"\s+", " ", " ".join(body)).strip()
                statement = re.sub(re.escape(printed).replace(r"\.", r"[.\s]*"), " ", statement)
                statement = re.sub(r"^B\d\s*/\s*JHS\d[.\s]*[\d.]*\s*", "", statement)
                statement = re.sub(r"\s+", " ", statement)
                statement = re.sub(r"\s+([,;.])", r"\1", statement).strip()
                if len(statement) > 15:
                    hit = {"statement": statement, "page": page_no, "code_line": code_text}
                    break
            out.append({"grade": grade, "cs_code": cs_code, "printed": printed,
                        "records": broken[cs_code],
                        "statement": hit["statement"] if hit else None,
                        "page": hit["page"] if hit else None,
                        "misprinted": bool(hit and KEY(hit["code_line"]) != KEY(printed)),
                        "code_line": hit["code_line"] if hit else None})
    return out


def plan_ccp(repairs: list[dict]) -> list[dict]:
    """-> per-file ({grade, path, data, fills, confirmed}) for the B7-B9 repairs.

    `confirmed` counts the records whose old value already ended with the very
    statement recovered from the print - i.e. the text was polluted by the
    neighbouring column rather than wrong.
    """
    plans = []
    for grade in CCP_GRADES:
        path = REFERENCE / f"french_{grade}_curriculum_db_clean.json"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        statement_of = {r["cs_code"]: r["statement"] for r in repairs
                        if r["grade"] == grade and r["statement"]}
        fills, confirmed = [], 0
        for code, rec in data.items():
            statement = statement_of.get(rec["cs_code"])
            if not statement or KEY(rec.get("cs_desc") or "") == KEY(statement):
                continue
            if KEY(rec["cs_desc"] or "").endswith(KEY(statement)):
                confirmed += 1
            fills.append((code, statement))
        plans.append({"grade": grade, "path": path, "data": data, "fills": fills,
                      "confirmed": confirmed})
    return plans


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the databases (default: report only)")
    args = ap.parse_args()

    print("FRENCH CONTENT STANDARDS  (data/reference, grades B4-B6)")
    print(f"  source : {PDF.relative_to(ROOT)}")
    print("  rule   : the content standard is the skill area named by the fourth")
    print("           component of the indicator code (front matter p. xvii):")
    for number, label in SKILLS.items():
        print(f"             {number} -> {label}")

    facts = verify_against_pdf()
    print("\n  print cross-check (the claims this fix rests on)")
    print(f"    SCOPE AND SEQUENCE pages {facts['scope_pages']}: {facts['scope_blocks']} "
          "sub-strand blocks list the four skills in order")
    if facts["scope_out_of_order"]:
        print(f"    !! out-of-order skills: {facts['scope_out_of_order'][:5]}")
    total_body = sum(facts["body_label_counts"].values())
    print(f"    body CONTENT STANDARDS cells: {total_body} label occurrences, "
          f"{len(facts['body_label_counts'])} distinct values")
    for label, n in facts["body_label_counts"].most_common():
        print(f"        {n:4d}  {label}")
    if facts["body_other_labels"]:
        print(f"    !! other values in the column: {facts['body_other_labels'][:5]}")

    plans, unlabelled = plan_changes()
    print("\n  changes")
    changed_files = 0
    for plan in plans:
        data, label = plan["data"], plan["grade"]
        n_fill = len(plan["fills"])
        print(f"    french_{label}  {len(data):3d} records | cs_desc empty or wrong "
              f"{n_fill:3d} | already correct {plan['already']:3d}")
        for name, count in sorted(plan["by_label"].items()):
            print(f"        {count:3d}  -> {name}")
        for d in plan["displaced"]:
            print(f"        displaced  {d['key']:12s} was {d['was'][:58]!r}")
        if n_fill:
            changed_files += 1

    if unlabelled:
        print("\n  left empty (no content standard to name - print defect)")
        for u in unlabelled:
            print(f"    {u['code']:12s} cs_code={u['cs_code']:10s} {u['ind_desc']!r}")

    # ── French B7-B9 ─────────────────────────────────────────────────────────
    print("\nFRENCH CONTENT STANDARDS  (data/reference, grades B7-B9)")
    print(f"  source : {CCP_PDF.relative_to(ROOT)}")
    print("  issue  : the CONTENT STANDARD column (x ~ 63) and the CORE COMPETENCIES")
    print("           column (x ~ 542) sit apart in the print, but the records below")
    print("           carry the neighbour's text - or a placeholder.")
    repairs = recover_statements()
    ccp_plans = plan_ccp(repairs)
    for r in repairs:
        mark = "recovered" if r["statement"] else "NOT IN PRINT"
        print(f"    {r['cs_code']:11s} {len(r['records']):2d} record(s)  {mark}")
        if r["statement"]:
            note = f"  (print labels it {r['code_line']})" if r["misprinted"] else ""
            print(f"        p{r['page']}  {r['statement']!r}{note}")
        else:
            print("        the print has no content standard with this code"
                  " - see docs/TODO.md")
    print("\n  changes")
    for plan in ccp_plans:
        print(f"    french_{plan['grade']}  cs_desc to rewrite: {len(plan['fills'])}  "
              f"(of which the record's own text already ends with the statement: "
              f"{plan['confirmed']})")

    if args.apply:
        for plan in plans + ccp_plans:
            if not plan["fills"]:
                continue
            for code, label in plan["fills"]:
                plan["data"][code]["cs_desc"] = label
            plan["path"].write_text(
                json.dumps(plan["data"], indent=1, ensure_ascii=False) + "\n",
                encoding="utf-8")
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps({
            "source": str(PDF.relative_to(ROOT)),
            "rule": {number: label for number, label in SKILLS.items()},
            "scope_blocks_verified": facts["scope_blocks"],
            "scope_pages": facts["scope_pages"],
            "body_label_counts": dict(facts["body_label_counts"]),
            "files": [{"grade": p["grade"], "filled": len(p["fills"]),
                       "already": p["already"], "displaced": p["displaced"]}
                      for p in plans],
            "left_empty": unlabelled,
            "b7_b9": {
                "source": str(CCP_PDF.relative_to(ROOT)),
                "recovered": [{"grade": r["grade"], "cs_code": r["cs_code"],
                               "page": r["page"], "statement": r["statement"],
                               "records": r["records"],
                               "print_labels_it": r["code_line"] if r["misprinted"] else None}
                              for r in repairs if r["statement"]],
                "not_in_print": [{"grade": r["grade"], "cs_code": r["cs_code"],
                                  "records": r["records"]}
                                 for r in repairs if not r["statement"]],
                "files": [{"grade": p["grade"], "filled": len(p["fills"]),
                           "confirmed_by_own_text": p["confirmed"]} for p in ccp_plans],
            },
        }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\n  done" + ("" if args.apply else "  (report only; pass --apply to write)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
