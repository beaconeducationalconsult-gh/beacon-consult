# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Split by pages
pages = text.split("=== PAGE ")

# Let's map each page's content
# Term 1: pages 1 to 11
# Term 2: pages 12 to 22
# Term 3: pages 23 to 32

term_pages = {
    1: list(range(1, 12)),
    2: list(range(12, 23)),
    3: list(range(23, 33))
}

# Let's check how many pages are in each term
print("Term 1 pages:", len(term_pages[1]))
print("Term 2 pages:", len(term_pages[2]))
print("Term 3 pages:", len(term_pages[3]))

# Let's see if we can find lines with "B1." which usually starts Content Standards or Indicators.
# Indicators start with "B1.1.", "B1.2.", "B1.3.", "B1.4.", "B1.5." etc.
for term_idx, p_nums in term_pages.items():
    print(f"\n=================== TERM {term_idx} ===================")
    for p_num in p_nums:
        p_text = pages[p_num]
        print(f"--- Page {p_num} (Length: {len(p_text)}) ---")
        # Let's look for indicators
        indicators = re.findall(r"B1\.\d+\.\d+\.\d+\.\d+|B1\.\d+\.\d+\.\d+|B1\.\d+\.\d+", p_text)
        print("Found indicators:", list(set(indicators)))
