# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's write a Python parser that scans the text and matches indicators and content standards.
# Let's see how many content standards are there in total and what their text is.
# We will search for matches like B1.1.1.1, B1.1.1.2, B1.1.2.1, etc.
# And indicators like B1.1.1.1.1, etc.

# Let's extract all matches of:
# (CS Code, CS Text, Ind Code, Ind Text, Competencies, Resources, Keywords, Assessment)
# Wait, let's write a script that does a very detailed regex or text search to find the blocks for each Week.
# Let's look at how the pages are structured and see if we can do page-based extraction.

pages = text.split("=== PAGE ")
print("Total pages:", len(pages) - 1)

for idx in range(1, len(pages)):
    p_text = pages[idx]
    print(f"\n--- PAGE {idx} ---")
    # Find all indicators in this page
    indicators = re.findall(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", p_text)
    print(f"Indicators on Page {idx}: {list(set(indicators))}")
