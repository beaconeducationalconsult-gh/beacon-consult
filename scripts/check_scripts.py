#!/usr/bin/env python3
"""Check that the scripts in this repository still point at code that exists (P2-8).

Most of `scripts/` is a graveyard of one-shot generators from the days when the
tooling lived in `tools/` and the data files sat in the repository root. They are kept
because they document how a database was built — which means they must at least be
*readable*: a script that cannot import its own compatibility shim is documentation
that lies.

Three faults are checked, all of them found in this tree on 2026-09-19:

* a file that does not compile;
* a file that imports `_compat` without first putting the directory that holds it on
  `sys.path` — every one of the 130 legacy scripts did this through a
  `parents[2] / "tools"` path that stopped existing when `tools/` was folded up;
* a file that uses `Path` (or `sys`) at module level without importing it.

Nothing is executed — the check is static, so it needs no third-party packages and
can run in CI next to `make inventory`. Usage: `python3 scripts/check_scripts.py`.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSERT = re.compile(r"path\.insert\(0,\s*(?P<expr>.*)\)\s*$")
PARENTS = re.compile(r"parents\[(\d+)\]")
WATCHED = ("Path", "sys")


def imported_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
    return names


def check(path: Path) -> list[str]:
    rel = path.relative_to(ROOT)
    if rel.name == "_compat.py":          # the shim itself is what the others import
        return []
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError as exc:
        return [f"{rel}: does not compile: {exc}"]

    problems: list[str] = []
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines, start=1):
        if not line.strip().startswith("from _compat import"):
            continue
        inserted = None
        for above in reversed(lines[: i - 1]):
            match = INSERT.search(above)
            if match:
                inserted = match.group("expr")
                break
        if not inserted:
            problems.append(f"{rel}:{i}: imports _compat with nothing on sys.path")
            continue
        depth = PARENTS.search(inserted)
        if "resolve().parents" in inserted and depth:
            here = path.resolve().parent
            for _ in range(int(depth.group(1))):
                here = here.parent
        else:
            problems.append(f"{rel}:{i}: cannot resolve the inserted path {inserted!r}")
            continue
        if not (here / "_compat.py").exists():
            problems.append(f"{rel}:{i}: _compat.py is not in {here.relative_to(ROOT)}")

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    have = imported_names(tree)
    for name in WATCHED:
        if name in used and name not in have:
            problems.append(f"{rel}: uses {name} at module level without importing it")
    return problems


def main() -> int:
    targets = sorted(ROOT.joinpath("scripts").rglob("*.py"))
    targets += sorted(ROOT.joinpath("seed").rglob("*.py")) if ROOT.joinpath("seed").exists() else []
    problems: list[str] = []
    for path in targets:
        problems.extend(check(path))
    for problem in problems:
        print(problem)
    print(f"{len(targets)} script(s) checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
