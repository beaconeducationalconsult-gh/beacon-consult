# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

pages = text.split("=== PAGE ")

for idx in range(1, len(pages)):
    lines = [l.strip() for l in pages[idx].split("\n") if l.strip()]
    print(f"\n--- PAGE {idx} ---")
    print(f"Header: {lines[0] if lines else 'None'}")
    found_wk_lines = []
    for line in lines:
        if re.search(r"^\d+$", line) or re.search(r"^\bWk\b", line, re.IGNORECASE) or "Week" in line or "Wk" in line:
            found_wk_lines.append(line)
    print("Week/Wk/Number lines (first 10):")
    for fl in found_wk_lines[:10]:
        print("  ", fl[:120])
