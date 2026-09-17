# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's find every occurrence of the pattern:
# Week number followed by Strand and Indicator.
# Or let's scan page by page and search for the indicator codes.
# Let's search for "B1.x.x.x.x" codes in the order they appear.

pages = text.split("=== PAGE ")
weeks_data = {}

# We know there are 36 weeks in total across 3 terms.
# Let's see: on each page, what weeks are mentioned and what indicators are found?
for page_num in range(1, len(pages)):
    p_text = pages[page_num]
    # Find all indicators of the form B1.x.x.x.x
    inds = re.findall(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", p_text)
    # Let's find what weeks are mentioned on this page
    # Look for lines that contain "Wk" or numbers at the beginning, or let's use a simple heuristic:
    # We can search for the week number in the table
    # Let's print the page number, its title/header, and the unique indicators found
    lines = [l.strip() for l in p_text.split("\n") if l.strip()]
    header = lines[0] if lines else ""
    print(f"Page {page_num:2d} | Header: {header[:50]:50s} | Indicators: {sorted(list(set(inds)))}")
