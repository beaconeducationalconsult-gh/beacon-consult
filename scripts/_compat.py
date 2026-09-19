"""Compatibility shim for the legacy one-shot scripts.

Before the restructure, data files sat next to the scripts in the repo
root (under `tools/`, which no longer exists) and every script opened them by bare
filename::

    with open("math_b4_lessons_enriched.json") as f:

Those files now live in data/lessons/, data/curriculum/ and so on. Rather
than rewriting ~150 scripts (most of which are one-shot generators that
have already done their job), importing this module makes bare filenames
resolve against the data directories again.

Only *reads* are redirected. Writes pass through untouched, so a script
that writes Basic1_Mathematics_Lesson_Plans_Full_Year.docx still writes it
to the current directory rather than accidentally reading a data file of
the same name.

Usage, at the very top of a legacy script::

    from _compat import open_compat; open_compat()
"""

import builtins
import sys
from pathlib import Path

_original_open = builtins.open


def open_compat():
    """Redirect bare-filename reads to the data directories."""
    from _paths import find_data

    def _open(file, mode="r", *args, **kwargs):
        if (
            isinstance(file, str)
            and isinstance(mode, str)
            and "r" in mode
            and "/" not in file
            and "\\" not in file
        ):
            resolved = find_data(file)
            if resolved is not None:
                file = str(resolved)
        return _original_open(file, mode, *args, **kwargs)

    builtins.open = _open


def _bootstrap():
    """Make `data/` importable no matter where this is called from."""
    here = Path(__file__).resolve().parent  # <root>/scripts
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))


_bootstrap()
