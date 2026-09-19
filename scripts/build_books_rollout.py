#!/usr/bin/env python3
"""Roll the book generator out subject by subject, and keep a manifest of what exists (P3-1).

`seed/build_book_skeleton.py` builds one subject-grade: a textbook and a workbook
skeleton whose chapters, units, topics and lessons mirror the NaCCA codes, with
every gap written as an AUTHOR-TODO box rather than invented prose. This script is
the part that turns one working generator into a rollout:

  * it enumerates the **served** subject-grades (`public/curriculum/`), so the
    books offered keep step with the curriculum the portal actually contains and
    a subject-grade cannot be "done" for books but missing from the app;
  * it runs the generator per subject-grade and reports each one — built, already
    present, or failed with the generator's own reason;
  * it writes `data/books_manifest.json`, because `books/` is gitignored: without
    a manifest nobody can tell which books were generated, how big they are, or
    whether a `-v2` revision exists beside the canonical one;
  * `--publish` zips a subject-grade's two documents into `dist/books/` — one
    file to send a pilot school.

Report first: with no flags it changes nothing.

    python3 scripts/build_books_rollout.py                       # what exists / what is missing
    python3 scripts/build_books_rollout.py --subject mathematics --grade B1 --generate
    python3 scripts/build_books_rollout.py --generate            # the whole rollout
    python3 scripts/build_books_rollout.py --manifest            # refresh the manifest only
    python3 scripts/build_books_rollout.py --subject mathematics --grade B1 --publish
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "public" / "curriculum"
BOOKS = ROOT / "books"
DIST = ROOT / "dist" / "books"
MANIFEST = ROOT / "data" / "books_manifest.json"
GENERATOR = ROOT / "seed" / "build_book_skeleton.py"

# The pilot the ticket names first; the report prints it at the top.
PILOT = ("mathematics", "B1")

STRUCTURE_RE = re.compile(r"structure:\s+(\d+) chapters · (\d+) units · (\d+) topics · (\d+) lessons")
KINDS = ("textbook", "workbook")


def served_pairs() -> list[dict]:
    """Every subject-grade the portal serves, in grade then subject order."""
    grades = json.loads((BUNDLE / "grades.json").read_text(encoding="utf-8"))
    pairs = []
    for grade in grades:
        gid = grade["id"]
        for subject in json.loads((BUNDLE / f"{gid.lower()}_subjects.json").read_text(encoding="utf-8")):
            pairs.append({
                "subject": subject["id"],
                "subjectName": subject.get("name", subject["id"]),
                "grade": gid,
                "indicators": subject.get("counts", {}).get("indicators"),
                "hasSchedule": bool(subject.get("hasSchedule")),
            })
    return pairs


def content_hash(path: Path) -> str:
    """A hash of what the document *says*, not of its zip bytes.

    Word documents are zips, and python-docx does not promise byte-identical
    archives across runs: regenerating a book here produced the same parts inside
    a different container. A manifest whose hashes changed on every run would
    tell nobody anything, so this hashes each part's name and contents instead.
    """
    digest = hashlib.sha256()
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            digest.update(name.encode("utf-8"))
            digest.update(hashlib.sha256(archive.read(name)).digest())
    return digest.hexdigest()[:16]


def books_for(subject: str, grade: str) -> dict[str, list[dict]]:
    """What is on disk for one subject-grade, canonical first, `-v2` after."""
    out = {kind: [] for kind in KINDS}
    folder = BOOKS / grade
    if not folder.exists():
        return out
    for kind in KINDS:
        for path in sorted(folder.glob(f"{subject}-{kind}-skeleton*.docx")):
            out[kind].append({
                "file": path.name,
                "bytes": path.stat().st_size,
                "contentHash": content_hash(path),
                "revision": int(m.group(1)) if (m := re.search(r"-v(\d+)\.docx$", path.name)) else 1,
            })
    return out


def run_generator(subject: str, grade: str, out: Path | None = None) -> tuple[bool, str, dict]:
    """One subject-grade through `seed/build_book_skeleton.py`."""
    command = [sys.executable, str(GENERATOR), subject, grade]
    if out is not None:
        command += ["--out", str(out)]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        return False, output, {}
    match = STRUCTURE_RE.search(output)
    counts = {}
    if match:
        counts = dict(zip(("chapters", "units", "topics", "lessons"), (int(n) for n in match.groups())))
    if "no schedule" in output:
        counts["schedule"] = False
    return True, output, counts


def measure(subject: str, grade: str) -> dict:
    """Build a subject-grade into a temporary directory just to read its structure.

    Books generated before the rollout existed have no counts recorded, and the
    counts are the part of the manifest that says a book covers the whole year.
    Measuring costs about half a second per subject-grade, writes nothing anyone
    keeps, and doubles as a check that the generator still builds that pair.
    """
    with tempfile.TemporaryDirectory() as tmp:
        ok, _, counts = run_generator(subject, grade, out=Path(tmp))
    return counts if ok else {}


def write_manifest(pairs: list[dict], structure: dict, generated: bool, measure_missing: bool = False) -> dict:
    books = []
    for pair in pairs:
        found = books_for(pair["subject"], pair["grade"])
        if not any(found[kind] for kind in KINDS):
            continue
        key = f"{pair['subject']}|{pair['grade']}"
        counts = structure.get(key) or {}
        if measure_missing and not counts:
            counts = measure(pair["subject"], pair["grade"])
            structure[key] = counts
        books.append({
            "subject": pair["subject"],
            "subjectName": pair["subjectName"],
            "grade": pair["grade"],
            "hasSchedule": pair["hasSchedule"],
            "indicators": pair["indicators"],
            "structure": counts,
            "documents": {kind: found[kind] for kind in KINDS},
            "revisions": max((d["revision"] for kind in KINDS for d in found[kind]), default=1),
        })
    manifest = {
        "generatedBy": "scripts/build_books_rollout.py",
        "generator": "seed/build_book_skeleton.py",
        "what": ("Book skeletons: a textbook and a workbook per subject-grade, one lesson per "
                 "indicator, with every unwritten section marked as an AUTHOR-TODO box. The "
                 "documents themselves are gitignored build outputs — this manifest is what the "
                 "repository records about them."),
        "contentHash": ("sha256 over a document's parts, not over its zip container: python-docx does "
                        "not promise byte-identical archives, so a hash of the file's bytes would "
                        "change on every run and mean nothing. A changed contentHash means the "
                        "document's content changed."),
        "pilot": {"subject": PILOT[0], "grade": PILOT[1]},
        "pairs": len(books),
        "documents": sum(len(found) for book in books for found in book["documents"].values()),
        "kilobytes": sum(d["bytes"] for book in books for found in book["documents"].values() for d in found) // 1024,
        "withRevisions": [f"{b['subject']} {b['grade']}" for b in books if b["revisions"] > 1],
        "books": books,
    }
    if generated:
        manifest["note"] = "updated by a --generate run"
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest


def publish(subject: str, grade: str) -> Path | None:
    """Zip one subject-grade's documents into dist/books/ — one file per pilot school."""
    found = books_for(subject, grade)
    documents = [BOOKS / grade / d["file"] for kind in KINDS for d in found[kind]]
    if not documents:
        return None
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"{subject}-{grade}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for document in documents:
            archive.write(document, arcname=document.name)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--subject", action="append", help="subject id (default: every served one)")
    ap.add_argument("--grade", action="append", help="grade id (default: every served one)")
    ap.add_argument("--generate", action="store_true", help="run the generator for the selection")
    ap.add_argument("--manifest", action="store_true",
                    help="write data/books_manifest.json and stop (measuring any subject-grade "
                         "whose structure was never recorded)")
    ap.add_argument("--publish", action="store_true", help="zip the selection's documents into dist/books/")
    args = ap.parse_args()

    if not BUNDLE.exists():
        sys.exit(f"No served bundle at {BUNDLE} — run `make build-curriculum`.")

    pairs = served_pairs()
    if args.subject:
        wanted = {s.lower() for s in args.subject}
        pairs = [p for p in pairs if p["subject"].lower() in wanted]
    if args.grade:
        wanted = {g.upper() for g in args.grade}
        pairs = [p for p in pairs if p["grade"].upper() in wanted]
    pairs.sort(key=lambda p: (p["grade"], p["subject"]))
    if not pairs:
        sys.exit("No subject-grade matches those filters.")

    structure: dict[str, dict] = {}
    if MANIFEST.exists():  # keep what earlier runs measured
        for book in json.loads(MANIFEST.read_text(encoding="utf-8")).get("books", []):
            structure[f"{book['subject']}|{book['grade']}"] = book.get("structure") or {}

    has_pilot = any((p["subject"], p["grade"]) == PILOT for p in pairs)
    print(f"{len(pairs)} served subject-grade(s)"
          + (f" · the pilot is {PILOT[0]} {PILOT[1]} (printed first)" if has_pilot else ""))
    print(f"  {'subject':18} {'grade':4} {'sched':5} {'ind':4}  documents")
    built = already = failed = 0
    failures = []
    for pair in sorted(pairs, key=lambda p: (0 if (p["subject"], p["grade"]) == PILOT else 1,
                                             p["grade"], p["subject"])):
        key = f"{pair['subject']}|{pair['grade']}"
        label = f"  {pair['subject']:18} {pair['grade']:4} {'yes' if pair['hasSchedule'] else 'no':5} " \
                f"{pair['indicators'] if pair['indicators'] is not None else '—':>4}  "

        if args.generate and not books_for(pair["subject"], pair["grade"])["textbook"]:
            ok, output, counts = run_generator(pair["subject"], pair["grade"])
            if ok:
                built += 1
                structure[key] = counts
                print(label + f"built — {counts.get('chapters', '?')} chapters · {counts.get('lessons', '?')} lessons")
            else:
                failed += 1
                failures.append((key, output.splitlines()[-1] if output else "no output"))
                print(label + f"FAILED — {output.splitlines()[-1] if output else 'no output'}")
            continue

        found = books_for(pair["subject"], pair["grade"])
        names = [d["file"] + (f" (rev {d['revision']})" if d["revision"] > 1 else "") for kind in KINDS for d in found[kind]]
        if names:
            already += 1
            print(label + ", ".join(names))
        else:
            print(label + "— not generated")

    if args.publish:
        for pair in pairs:
            out = publish(pair["subject"], pair["grade"])
            if out:
                print(f"  published {out.relative_to(ROOT)}")

    if args.manifest or args.generate or args.publish:
        manifest = write_manifest(served_pairs(), structure, args.generate, measure_missing=True)
        print(f"\nmanifest: {manifest['pairs']} subject-grade(s), {manifest['documents']} documents, "
              f"{manifest['kilobytes']} KB → {MANIFEST.relative_to(ROOT)}")

    print(f"\nbuilt {built} · already present {already} · failed {failed}")
    if failures:
        for key, reason in failures:
            print(f"  x {key}: {reason}")
        return 1
    if not (args.generate or args.publish or args.manifest):
        print("report only — pass --generate to build the missing books")
    return 0


if __name__ == "__main__":
    sys.exit(main())
