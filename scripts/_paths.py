"""Single source of truth for where the curriculum data lives.

Every tool that reads or writes curriculum data should import from here
rather than hard-coding a path. Before the restructure, 154 scripts
referenced data files by bare filename and only worked when run from the
repo root; this module is what makes the layout movable.

Usage::

    from _paths import CURRICULUM, LESSONS, find_data
"""

from pathlib import Path

# Repository root (this file lives in <root>/scripts/)
ROOT = Path(__file__).resolve().parent.parent

DATA = ROOT / "data"

CURRICULUM = DATA / "curriculum"  # *_curriculum_db_clean.json + *_summary.json
LESSONS = DATA / "lessons"  # *_lessons_enriched.json
SOURCES = DATA / "sources"  # source NaCCA PDFs
RAW = DATA / "raw"  # text extracted from those PDFs
INDICATORS = DATA / "indicators"  # indicator extracts
AUDIT = DATA / "audit"  # audit results
MISC = DATA / "misc"  # parsed-lesson intermediates
BOOKS = DATA / "books"  # sample generated documents
REFERENCE = DATA / "reference"  # second copy, formerly app/data/

APP = ROOT / "app"
APP_CURRICULUM = APP / "public" / "curriculum"  # build output, gitignored

# Curriculum databases exist in two places: the primary set in
# data/curriculum/ and a second, partly-divergent copy in data/reference/.
# Order is significant — CURRICULUM is checked first, which reproduces the
# historical behaviour (repo root was searched before app/data/).
DB_SEARCH = [CURRICULUM, REFERENCE]

# Every directory a data file might reasonably live in.
ALL_DATA_DIRS = (
    CURRICULUM,
    LESSONS,
    SOURCES,
    RAW,
    INDICATORS,
    AUDIT,
    MISC,
    BOOKS,
    REFERENCE,
)


def find_data(name, *extra_dirs):
    """Locate a data file by bare filename across the known directories.

    Returns a Path, or None if the file is nowhere to be found. This is the
    tolerant replacement for the old bare `open("file.json")` calls, which
    only ever worked from the repo root.
    """
    for base in (*extra_dirs, *ALL_DATA_DIRS):
        p = base / name
        if p.exists():
            return p
    return None


def open_data(name, *extra_dirs, **kwargs):
    """Open a data file by bare filename, wherever it lives."""
    p = find_data(name, *extra_dirs)
    if p is None:
        raise FileNotFoundError(
            f"{name!r} not found in any data directory "
            f"({', '.join(str(d) for d in (*extra_dirs, *ALL_DATA_DIRS))})"
        )
    return open(p, **kwargs)
