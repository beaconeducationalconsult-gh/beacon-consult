#!/usr/bin/env python3
"""Fill the records that restate their own code, from the print's own words (P1-11).

302 records in these databases carry a *label* instead of the curriculum text:

    "ind_desc": "Our World Our People Learning Indicator B4.1.1.1.1"
    "cs_desc":  "Our World Our People Content Standard B4.1.1.1"
    "strand":   "Strand B4.1"        "sub_strand": "Sub-strand B4.1.1"

74 of them are served (`owop_B4`/`B5`/`B6`, 25/25/24 — the whole of those three
files); the other 228 sit in `data/reference/`. `scripts/drop_front_matter_records.py`
proved the prints *do* carry the real wording, so these are a filling job, not a
deletion: the label is where an extractor gave up, not what the curriculum says.

The wording is read off the print row by row.  A table's columns are not the same
width on any two pages, so the band is taken from the page's own vertical rules
(the pair that brackets the line the record's code starts) rather than a fixed
window; the content standard is the cell immediately to the left of that band, and
the strand / sub-strand names are the block headings the print sets above the table.

Nothing is written on a hunch.  A field is filled only when the read:

* comes from the cell that begins with the record's own code (blob-compared, so the
  print's `B 4 .1.1.1.1.` counts);
* says more than the code, is not itself a label, and has at least three words;
* for `cs_desc`, comes from a cell that begins with the record's own `cs_code` — the
  two prints whose rows pair an indicator with another standard's number are reported
  as `cs_mismatch`, never guessed;
* for `strand`/`sub_strand`, is the print's own heading whose number matches the
  code's component, and is not the code restated.

Escapes are honoured, so `B7.4.2.3.1` in a front-matter example can never be read as
a row — but such records are already gone (P1-10); this script only fills.

Report by default, `--apply` writes; every write and every refusal is recorded in
`data/audit/label_form_text.json`.
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

LABEL_INDICATOR = re.compile(r"^\w[\w &-]* Learning Indicator\s+[BK]?\s*\d[\d.\s]*$", re.I)
LABEL_STANDARD = re.compile(r"^\w[\w &-]* Content Standard\s+[BK]?\s*\d[\d.\s]*$", re.I)
CODE_SHAPED = re.compile(r"^(Strand|Sub-?strand)\s+[BK]?\s*\d[\d.\s]*$", re.I)
STOP_LINE = re.compile(r"^(Indicator|Exemplars|Content Standard|Core Competencies)\b", re.I)
STRAND_HEAD = re.compile(r"^Strand\s+(\d+)\s*:?\s*(.+)$", re.I)
SUB_HEAD = re.compile(r"^Sub-?strand\s+([\d.]+)\s*:?\s*(.+)$", re.I)
NAME_OK = re.compile(r"^[A-Z][A-Za-z0-9'’&,\- ]{2,60}$")

# one vertical rule set per (pdf, page): [(x, y, h)] in the print's own coordinates
_RULES: dict[tuple[str, int], list[tuple[float, float, float]]] = {}
# one visual line list per (pdf, page): [(y, x, text)] top to bottom
_LINES: dict[tuple[str, int], list[tuple[float, float, str]]] = {}


def is_label(text: str) -> bool:
    return bool(LABEL_INDICATOR.match(text) or LABEL_STANDARD.match(text))


def rules(pdf: str, page: int) -> list[tuple[float, float, float]]:
    """The page's vertical rules: (x, bottom y, height) in bottom-up coordinates."""
    key = (pdf, page)
    if key not in _RULES:
        out = []
        contents = F._reader(pdf).pages[page].get_contents()
        # a page that draws nothing has an empty ContentStream, and an empty
        # ContentStream is falsy — `if contents` silently skipped every one of them
        for op in (contents.operations if contents is not None else []):
            try:
                operands, operator = op
            except (TypeError, ValueError):
                continue
            if operator != b"re":
                continue
            x, y, w, h = (float(v) for v in operands)
            if w < 2.5 and h > 5:
                out.append((round(x, 1), round(y, 1), round(h, 1)))
        _RULES[key] = out
    return _RULES[key]


def rules_at(pdf: str, page: int, y: float) -> list[float]:
    return sorted({x for x, ry, h in rules(pdf, page) if ry - 2 <= y <= ry + h + 2})


def visual_lines(pdf: str, page: int) -> list[tuple[float, float, str]]:
    """The page's text as visual lines, top to bottom, with the leftmost x of each."""
    key = (pdf, page)
    if key not in _LINES:
        rows = sorted(((x, y, t) for _p, x, y, t in F.chunks(pdf, [page])),
                      key=lambda r: (-r[1], r[0]))
        out: list[tuple[float, float, str]] = []
        for x, y, t in rows:
            if out and abs(y - out[-1][0]) <= 2.0:
                out[-1] = (out[-1][0], min(out[-1][1], x), out[-1][2] + " " + t.strip())
            else:
                out.append((y, x, t.strip()))
        _LINES[key] = [(y, x, re.sub(r"\s+", " ", t).strip()) for y, x, t in out]
    return _LINES[key]


def row_bands(pdf: str, page: int):
    """Every (y_lo, y_hi, [x rules]) group of columns a table on this page draws.

    A page often sets two tables, and their columns are not the same width — the
    rules that bracket a row are the ones whose own y-span covers it, never a
    neighbouring table's, which is why the group carries its y span with it.
    """
    groups: list[tuple[float, float, list[float]]] = []
    for probe in sorted({ry + h / 2 for _x, ry, h in rules(pdf, page)}, reverse=True):
        covering = [(x, ry, h) for x, ry, h in rules(pdf, page)
                    if ry - 2 <= probe <= ry + h + 2]
        if not covering:
            continue
        y_lo = min(ry for _x, ry, _h in covering)
        y_hi = max(ry + h for _x, ry, h in covering)
        xs = sorted({x for x, _ry, _h in covering})
        if (y_lo, y_hi) not in {(g[0], g[1]) for g in groups}:
            groups.append((y_lo, y_hi, xs))
    return groups


def cell_band(pdf: str, page: int, code: str) -> tuple[float, float, float, tuple[float, float]] | None:
    """(lo, hi, y, y_span) of the cell whose first line begins with `code`."""
    want = F.blob(code)
    for y_lo, y_hi, xs in row_bands(pdf, page):
        for i in range(len(xs) - 1):
            lo, hi = xs[i], xs[i + 1]
            for y, t in F.page_lines(pdf, page, lo + 1.5, hi - 1.5):
                if not (y_lo - 2 <= y <= y_hi + 2):
                    continue
                lead = F.line_code(t)
                if lead and F.blob(lead) == want:
                    return lo, hi, y, (y_lo, y_hi)
    return None


def cell_text(pdf: str, page: int, lo: float, hi: float, code: str,
              y_span: tuple[float, float] | None = None) -> str | None:
    """The cell's text: from the line that starts with `code` to the next block."""
    lines = F.page_lines(pdf, page, lo + 1.5, hi - 1.5)
    if y_span:
        lines = [(y, t) for y, t in lines if y_span[0] - 2 <= y <= y_span[1] + 2]
    want = F.blob(code)
    start = None
    for i, (y, t) in enumerate(lines):
        lead = F.line_code(t)
        if lead and F.blob(lead) == want:
            start = i
            break
    if start is None:
        return None
    out = [lines[start][1]]
    for _y, t in lines[start + 1:]:
        if F.line_code(t) or F.BLOCK_HEADING.match(t) or STOP_LINE.match(t):
            break
        out.append(t)
    return F.tidy(F.strip_code_prefix(" ".join(out)))


# what the print sets in the *next* cell of the row in the prints whose table does
# not draw a rule between the indicator and its exemplars: the read stops there
CELL_TAIL = re.compile(r"\s*(?:•|\u2022|\d+\.\s|Learners?\s+(?:are|is|should|will)\b"
                       r"|In\s+groups\b|Teacher\b|Let\s+learners\b|Guide\s+learners\b)")
CELL_LEAD = re.compile(r"^\s*(?:•|\u2022|\d+\.\s)")
# the page footer is printed inside the last cell of the table it follows
FOOTER = re.compile(r"\s*(?:©\s*)?(?:NaCCA|NACCA)\b.*$|\s*Ministry of Education.*$")
# the content-standard cell of some prints leads with the strand's own label
CELL_LABEL = re.compile(r"^\s*[A-Z][A-Za-z'’&\- ]{2,30}:\s*")


def read_text(text: str | None) -> str | None:
    """The indicator the cell carries, with the exemplar cell's own text taken off."""
    if not text:
        return None
    if CELL_LEAD.match(text):
        return None                     # the read began inside the exemplar, not the row
    text = FOOTER.sub("", text)
    text = CELL_LABEL.sub("", text)
    cut = CELL_TAIL.search(text)
    if cut and cut.start() > 0:
        text = text[:cut.start()]
    text = text.strip(" .;,•")
    return text or None


def plausibly_text(text: str | None) -> bool:
    """A read is text, not a code or a label, and says enough to be worth writing."""
    if not text:
        return False
    if is_label(text) or CODE_SHAPED.match(text):
        return False
    words = [w for w in re.split(r"\s+", text) if re.search(r"[A-Za-z]", w)]
    return len(words) >= 3 and len(F.blob(text)) >= 12


def block_headings(pdf: str, page: int, y: float) -> tuple[str, str]:
    """(strand, sub-strand) headings in force above `y` on this page.

    A table's heading is set once, at the top of the block, so the page a row
    continues on carries only the sub-strand (`Sub-strand 2: Myself`) — the strand is
    taken from the nearest page above that prints one.
    """
    strand = sub = ""
    for ly, x, t in visual_lines(pdf, page):
        if ly <= y - 1.0 or x > 620:
            continue
        m = STRAND_HEAD.match(t)
        if m:
            name = m.group(2).strip()
            # the owop B5 print heads its sub-strands `Strand 1: Nature of God`
            # while the strand above it is `STRAND 1: ALL ABOUT US` — NaCCA sets
            # strand names in caps, so a mixed-case `Strand n:` is the sub-strand
            if name.isupper():
                strand = f"{m.group(1)}. {name}"
            else:
                sub = f"{m.group(1)}. {name}"
            continue
        m = SUB_HEAD.match(t)
        if m:
            sub = f"{m.group(1)}. {m.group(2).strip()}"
    if strand:
        return strand, sub
    for back in range(1, 4):
        if page - back < 0:
            break
        for ly, x, t in visual_lines(pdf, page - back):
            m = STRAND_HEAD.match(t)
            if m:
                strand = f"{m.group(1)}. {m.group(2).strip()}"
                break
        if strand:
            break
    return strand, sub


def grade_of(parts_code: str) -> tuple[str, str]:
    """('B4.1.2.1.1') -> ('1', '2')  (the strand and sub-strand components)."""
    bits = [b for b in re.split(r"[.\s]+", parts_code) if b]
    strand = bits[1] if len(bits) > 1 else ""
    sub = bits[2] if len(bits) > 2 else ""
    return strand, sub


def name_ok(name: str) -> bool:
    plain = re.sub(r"^[\d.\s]+", "", name).strip()
    return bool(plain) and not CODE_SHAPED.match(name) and not is_label(name) \
        and len(F.blob(plain)) >= 4


def row_y(pdf: str, page: int, code: str) -> float | None:
    """The y of the line that begins with `code`, for the block-heading lookup."""
    want = F.blob(code)
    for y, _x, t in visual_lines(pdf, page):
        lead = F.line_code(t)
        if lead and F.blob(lead) == want:
            return y
    return None


def read_record(pdf: str, page: int, code: str, cs_code: str) -> dict:
    """What the print sets for this record — every field, with the evidence."""
    out: dict = {"page": page, "ind_desc": None, "cs_desc": None,
                 "strand": None, "sub_strand": None, "notes": []}
    band = cell_band(pdf, page, code)
    if band is None:
        out["notes"].append("no row begins with this code in the print")
        return out
    lo, hi, y, span = band
    ind = read_text(cell_text(pdf, page, lo, hi, code, span))
    if plausibly_text(ind):
        out["ind_desc"] = ind
    else:
        out["notes"].append("the row's indicator cell does not read as text")

    # the content standard sits in the column immediately left of the indicator;
    # the row may straddle a page break, so the nearest pages above are tried too
    for back in range(0, 4):
        pg = page - back
        if pg < 0:
            break
        cs_band = cell_band(pdf, pg, cs_code)
        if cs_band is None:
            continue
        c_lo, c_hi, _cy, c_span = cs_band
        if back == 0 and c_lo >= lo - 1:
            # the band found *is* the indicator column (a page sets two tables of
            # different widths, so comparing the right edge alone trips over the
            # narrower one); the CS column always begins to the left of the indicator
            continue
        text = read_text(cell_text(pdf, pg, c_lo, c_hi, cs_code, c_span))
        if plausibly_text(text):
            out["cs_desc"] = text
            out["cs_page"] = pg
            break
    if out["cs_desc"] is None:
        out["notes"].append("no content-standard cell begins with cs_code")

    strand, sub = block_headings(pdf, page, y)
    want_strand, want_sub = grade_of(code)
    if strand and name_ok(strand) and grade_of(code)[0] == strand.split(".")[0].strip():
        out["strand"] = strand
    if sub and name_ok(sub) and sub.split(".")[0].strip() == want_sub:
        out["sub_strand"] = sub
    return out


def wanted_fields(record: dict) -> list[str]:
    """Which fields of this record are placeholders the print can replace.

    A record qualifies only when one of its two description fields is a label: the
    whole of `owop_B4`–`B6` and the older reference copies are label-form throughout,
    and in those files the strand / sub-strand names are placeholders too.  Widening
    the strand pass to every record whose `strand` merely *looks* code-shaped would
    rewrite ~1,400 records across the dataset from a heading the row may not be under,
    so it stays out (TODO P1-12 records the shape).
    """
    out = []
    if is_label(str(record.get("ind_desc", ""))):
        out.append("ind_desc")
    if is_label(str(record.get("cs_desc", ""))):
        out.append("cs_desc")
    if out:
        # the strand and sub-strand names go with them, but only in the files whose
        # text is placeholder-shaped throughout.  A code-shaped `sub_strand` on its
        # own is not enough to act on: 1,743 subject-grade+sub-strand pairs across the
        # dataset are still named by their code, and the block heading verifies for
        # only 400 of them with the prints this script knows (TODO P1-12 has the
        # measurement and what is missing).
        if CODE_SHAPED.match(str(record.get("strand", ""))):
            out.append("strand")
        if CODE_SHAPED.match(str(record.get("sub_strand", ""))):
            out.append("sub_strand")
    return out


def scan() -> tuple[list[dict], list[dict], dict]:
    fill: list[dict] = []
    refused: list[dict] = []
    tally = {"files": {}, "records": 0}
    for layer, root in (("curriculum", CURRICULUM), ("reference", REFERENCE)):
        for path in sorted(root.glob("*_curriculum_db_clean.json")):
            parsed = X.subject_grade(path.name)
            if not parsed:
                continue
            subject, grade = parsed
            pdf = X.print_for(subject, grade)
            data = json.loads(path.read_text())
            entries: list[dict] = []
            for code, record in data.items():
                if not isinstance(record, dict):
                    continue
                fields = wanted_fields(record)
                if not fields:
                    continue
                entry = {"layer": layer, "file": path.name, "code": code,
                         "fields": fields, "values": {}, "refused": [],
                         "strand_num": grade_of(code)[0], "sub_num": grade_of(code)[1]}
                if not pdf:
                    entry["refused"].append((None, "no print for this subject-grade"))
                    entries.append(entry)
                    continue
                pages = F.pages_of(pdf, code)
                if not pages:
                    entry["refused"].append((None, "the code is in no row of the print"))
                    entries.append(entry)
                    continue
                if set(fields) <= {"strand", "sub_strand"}:
                    # nothing to read out of a cell: the block's heading is what the
                    # record needs, and that costs one pass over the page's lines
                    y = row_y(pdf, pages[0], code)
                    read = {"page": pages[0], "strand": None, "sub_strand": None,
                            "notes": []}
                    if y is None:
                        read["notes"].append("no row begins with this code")
                    else:
                        strand, sub = block_headings(pdf, pages[0], y)
                        want_strand, want_sub = grade_of(code)
                        if strand and name_ok(strand) \
                                and strand.split(".")[0].strip() == want_strand:
                            read["strand"] = strand
                        if sub and name_ok(sub) and sub.split(".")[0].strip() == want_sub:
                            read["sub_strand"] = sub
                else:
                    read = read_record(pdf, pages[0], code, record.get("cs_code", ""))
                entry.update({"print": pdf, "page": read.get("page"),
                              "cs_page": read.get("cs_page")})
                for field in fields:
                    value = read.get(field)
                    if value:
                        entry["values"][field] = value
                    else:
                        entry["refused"].append((field, "; ".join(read["notes"])
                                                 or "the print's cell did not verify"))
                entries.append(entry)

            # the strand and sub-strand names are properties of the block, not of the
            # row: the heading is printed once, at the top of the block, and the rows
            # that continue on the next page do not repeat it.  So a name proven for
            # any row of a block is the name of every row in it — and a block whose
            # name the print never gave stays a placeholder rather than a guess.
            for key, field in ((lambda e: e["strand_num"], "strand"),
                               (lambda e: (e["strand_num"], e["sub_num"]), "sub_strand")):
                names: dict = {}
                for e in entries:
                    value = e["values"].get(field)
                    if value:
                        names[key(e)] = value
                for e in entries:
                    if field not in e["fields"] or field in e["values"]:
                        continue
                    value = names.get(key(e))
                    if value:
                        e["values"][field] = value
                        e["refused"] = [r for r in e["refused"] if r[0] != field]

            for e in entries:
                if e["values"]:
                    fill.append({"layer": e["layer"], "file": e["file"], "code": e["code"],
                                 "print": e.get("print", ""), "page": e.get("page"),
                                 "cs_page": e.get("cs_page"), "values": e["values"],
                                 "before": {f: data[e["code"]].get(f) for f in e["values"]}})
                    tally["records"] += 1
                    tally["files"][f"{layer}/{path.name}"] = \
                        tally["files"].get(f"{layer}/{path.name}", 0) + 1
                for field, reason in e["refused"]:
                    refused.append({"layer": e["layer"], "file": e["file"],
                                    "code": e["code"], "field": field or "",
                                    "reason": reason})
    return fill, refused, tally


def strand_names(data: dict) -> dict[str, str]:
    """strand number -> the print's own name, as the database now records it."""
    names: dict[str, str] = {}
    for code, rec in data.items():
        if not isinstance(rec, dict):
            continue
        label = re.sub(r"^\s*\d+\s*[.):-]?\s*", "", str(rec.get("strand", "")).strip())
        label = re.sub(r"\s+", " ", label).strip()
        if label and not CODE_SHAPED.match(label) and not is_label(label):
            names.setdefault(grade_of(code)[0], label)
    return names


def refresh_summary(path: Path, data: dict) -> list[dict]:
    """Give the summary the strand names its database now carries, nothing else.

    The summary holds a per-strand breakdown; only the names can go stale here (the
    counts are re-derived by the inventory), and only for a strand the database has
    named.  When the summary's own name is the code restated (`B4.1`), the summary
    was written while the database was still placeholder-shaped — that is the case
    this repairs.
    """
    summary = path.with_name(path.name.replace("_curriculum_db_clean.json",
                                               "_curriculum_summary.json"))
    if not summary.exists():
        return []
    payload = json.loads(summary.read_text())
    names = strand_names(data)
    changed = []
    for row in payload.get("strands", []):
        no = re.sub(r"^[BK]?\d*\.", "", str(row.get("code", ""))) or row.get("code", "")
        if str(no) not in names:
            continue
        current = str(row.get("name", ""))
        if not (CODE_SHAPED.match(current) or current == row.get("code")
                or not current.strip()):
            continue
        if current == names[str(no)]:
            continue
        changed.append({"summary": summary.name, "strand": row.get("code"),
                        "before": current, "after": names[str(no)]})
        row["name"] = names[str(no)]
    if changed:
        summary.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    return changed


def merge(old: dict, fill: list[dict], refused: list[dict]) -> dict:
    """The artifact after this run, keeping every earlier write."""
    written: dict[tuple, dict] = {}
    for e in old.get("written", []):
        written[(e["layer"], e["file"], e["code"], e["field"])] = e
    for e in fill:
        for field, after in e["values"].items():
            key = (e["layer"], e["file"], e["code"], field)
            if key in written and written[key]["after"] == after:
                continue
            written[key] = {"layer": e["layer"], "file": e["file"], "code": e["code"],
                            "field": field, "before": e["before"].get(field, ""),
                            "after": after, "print": e["print"], "page": e["page"],
                            "cs_page": e.get("cs_page")}
    return {"written": sorted(written.values(),
                              key=lambda e: (e["layer"], e["file"], e["code"], e["field"])),
            "refused": [{"layer": e["layer"], "file": e["file"], "code": e["code"],
                         "field": e.get("field", ""), "reason": e["reason"]}
                        for e in refused] or old.get("refused", []),
            "applied": old.get("applied", {"files": {}, "fields": 0})}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write the text the print sets")
    ap.add_argument("--details", action="store_true", help="print every record found")
    args = ap.parse_args()

    fill, refused, tally = scan()
    n_fields = sum(len(e["values"]) for e in fill)
    print(f"{len(fill)} record(s) / {n_fields} field(s) the print's own words can fill")
    for name, count in sorted(tally["files"].items()):
        print(f"  {name:58s} {count:3d}")
    print(f"{len(refused)} field(s) left as they are")
    for e in refused[:12] if not args.details else refused:
        print(f"  {e['layer']}/{e['file']} {e['code']}"
              f"{' ' + e['field'] if e.get('field') else ''}: {e['reason']}")
    if args.details:
        for e in fill:
            print(f"  … {e['layer']}/{e['file']} {e['code']} p{e['page']}")
            for field, value in e["values"].items():
                print(f"      {field}: {value!r}")

    artifact = AUDIT / "label_form_text.json"
    old: dict = {}
    if artifact.exists():
        try:
            old = json.loads(artifact.read_text())
        except ValueError:
            old = {}
    audit = merge(old, fill, refused)

    if args.apply and fill:
        by_file: dict[tuple[str, str], list[dict]] = {}
        for entry in fill:
            by_file.setdefault((entry["layer"], entry["file"]), []).append(entry)
        for (layer, name), entries in by_file.items():
            path = (CURRICULUM if layer == "curriculum" else REFERENCE) / name
            data = json.loads(path.read_text())
            before = audit["applied"]["files"].get(f"{layer}/{name}", {}).get("fields", 0)
            written = 0
            for entry in entries:
                record = data.get(entry["code"])
                if not isinstance(record, dict):
                    continue
                for field, value in entry["values"].items():
                    if record.get(field) != value:
                        record[field] = value
                        written += 1
            path.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
            audit["applied"]["files"][f"{layer}/{name}"] = {
                "records": len(entries),
                "fields": before + written,
                "written_this_run": written,
            }
            audit["applied"]["fields"] += written
            print(f"  wrote {written} field(s) into {layer}/{name}")
    if args.apply:
        # the summaries hold a per-strand breakdown, and a strand the database has
        # only now named still reads as its code there — kept in step here, once per
        # file this pass ever wrote, so a re-run repairs a summary the writethrough
        # missed instead of leaving the two layers disagreeing
        touched = sorted({(e["layer"], e["file"]) for e in audit["written"]})
        for layer, name in touched:
            path = (CURRICULUM if layer == "curriculum" else REFERENCE) / name
            if not path.exists():
                continue
            for change in refresh_summary(path, json.loads(path.read_text())):
                audit.setdefault("summaries", []).append({**change, "layer": layer})
                print(f"  summary {change['summary']}: strand {change['strand']} "
                      f"{change['before']!r} -> {change['after']!r}")
    AUDIT.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(audit, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
