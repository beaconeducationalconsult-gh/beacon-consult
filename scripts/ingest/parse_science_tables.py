# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

with open("science_raw_text.txt") as f:
    text = f.read()

pages = text.split("=== PAGE ")

# We want to identify for each term and week, which 5 indicators are listed.
# Let's write a regular expression to find all rows of the table.
# Since the PDF is parsed line-by-line, the table structure might be somewhat jumbled,
# but let's see how each page lists weeks.
# On Page 1, we have Weeks 1-12 of Term 1.
# On Page 12, we have Weeks 1-12 of Term 2.
# On Page 23, we have Weeks 1-12 of Term 3.

# Let's search for "B1.\d.\d.\d" in the text and print lines around them
lines = text.split("\n")
print(f"Total lines: {len(lines)}")

# Let's inspect Page 1 and 2 to see the exact text flow around indicators
print("\n--- SAMPLE PAGE 1 TEXT FLOW ---")
print("\n".join(pages[1].split("\n")[:40]))
