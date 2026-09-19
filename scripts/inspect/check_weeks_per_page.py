# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

pages = text.split("=== PAGE ")

for i in range(1, len(pages)):
    p_text = pages[i]
    lines = [line.strip() for line in p_text.split("\n") if line.strip()]
    weeks_found = []
    for line in lines[:30]: # Look in first 30 lines
        if line.isdigit() and 1 <= int(line) <= 12:
            weeks_found.append(int(line))
        m = re.search(r"\bWk\s+(\d+)|\bWeek\s+(\d+)", line, re.IGNORECASE)
        if m:
            weeks_found.append(int(m.group(1) or m.group(2)))
    
    weeks_found = sorted(list(set(weeks_found)))
    print(f"Page {i:2d}: Title Line: '{lines[0][:60]}' | Weeks found: {weeks_found}")
