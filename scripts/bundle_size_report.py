#!/usr/bin/env python3
"""Report what the committed curriculum bundle costs, and fail if it outgrows its budget (P2-6).

`public/curriculum/` is a **build output that is committed to git**. That is a
decision, not an accident — Vercel deploys the repository, the app is an
offline-first PWA whose files *are* the product, and a deploy that had to fetch
its curriculum from somewhere else would add a credential and a failure mode to
every release. The cost is that 39 MB lives in history, so it needs a guard rail:
this script prints the size, compares it with what the last commit held, shows
the offenders, and fails when the bundle grows past a budget nobody agreed to.

The budget is deliberately generous (80 MB by default) because the bundle grows
with the curriculum, not with carelessness — the point is that a jump is
*noticed*, not that the bundle is small. Override with `BUNDLE_BUDGET_MB`.

    python3 scripts/bundle_size_report.py             # print, fail over budget
    BUNDLE_BUDGET_MB=150 python3 scripts/bundle_size_report.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "public" / "curriculum"
DEFAULT_BUDGET_MB = 80.0

# The bundle is regenerated wholesale; anything above this is worth naming.
TOP_N = 5


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def human(size: int) -> str:
    return f"{size / 1e6:.1f} MB" if size >= 1e6 else f"{size / 1e3:.0f} KB"


def committed_sizes() -> dict[str, int]:
    """Blob sizes in the last commit, straight from the tree — no checkout needed."""
    out = git("ls-tree", "-r", "-l", "HEAD", "public/curriculum")
    sizes = {}
    for line in out.splitlines():
        meta, _, path = line.partition("\t")
        parts = meta.split()
        if len(parts) >= 4 and parts[1] == "blob" and parts[3].isdigit():
            sizes[path] = int(parts[3])
    return sizes


def main() -> int:
    if not BUNDLE.exists():
        sys.exit(f"No bundle at {BUNDLE} — run `make build-curriculum`.")
    budget_mb = float(os.environ.get("BUNDLE_BUDGET_MB", DEFAULT_BUDGET_MB))

    files = sorted(p for p in BUNDLE.rglob("*") if p.is_file())
    tracked = {p.relative_to(ROOT).as_posix(): p.stat().st_size for p in files}
    total = sum(tracked.values())

    by_dir: dict[str, list[int]] = {}
    for path, size in tracked.items():
        key = "/".join(Path(path).relative_to("public/curriculum").parts[:-1]) or "."
        entry = by_dir.setdefault(key, [0, 0])
        entry[0] += 1
        entry[1] += size

    print(f"public/curriculum/ — {len(files)} files · {human(total)}")
    for key in sorted(by_dir, key=lambda k: -by_dir[k][1]):
        count, size = by_dir[key]
        print(f"  {key:24} {count:4} files  {human(size):>10}")

    print(f"\n  largest files:")
    for path, size in sorted(tracked.items(), key=lambda kv: -kv[1])[:TOP_N]:
        print(f"    {human(size):>10}  {path.removeprefix('public/curriculum/')}")

    previous = committed_sizes()
    if previous:
        committed_total = sum(previous.values())
        delta = total - committed_total
        change = "no change" if delta == 0 else f"{'+' if delta > 0 else '-'}{human(abs(delta))}"
        print(f"\n  last commit: {human(committed_total)} · this checkout: {human(total)} ({change})")

    commits = len(git("log", "--oneline", "--", "public/curriculum").splitlines())
    print(f"  history: {commits} commit(s) have touched the bundle; "
          f".git is {human(sum(f.stat().st_size for f in (ROOT / '.git').rglob('*') if f.is_file()))}")

    mb = total / 1e6
    if mb > budget_mb:
        print(f"\nBUDGET EXCEEDED: {mb:.1f} MB > {budget_mb:.0f} MB (BUNDLE_BUDGET_MB).")
        print("The bundle is committed on purpose (see docs/curriculum-data.md, "
              "\"Does the bundle belong in git?\"). If the growth is intended, raise the "
              "budget in the Makefile with the reason, or move the bundle to a release "
              "artefact and teach the build to fetch it.")
        return 1
    print(f"\nwithin budget ({mb:.1f} MB of {budget_mb:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
