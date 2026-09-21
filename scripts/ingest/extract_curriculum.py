# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's split by PAGE
pages = text.split("=== PAGE ")
print(f"Total pages extracted: {len(pages)-1}")

# Let's see what is on Page 12 (Term 2) and Page 23 (Term 3)
for p_idx in [11, 22]: # 0-based page index for page 12 and 23
    p_text = pages[p_idx+1]
    lines = p_text.split("\n")
    print(f"\n--- Page {p_idx+1} (first 20 lines) ---")
    for line in lines[:20]:
        print(line)
