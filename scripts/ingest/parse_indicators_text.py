# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's search for lines containing codes like B1.x.x.x or B1.x.x.x.x
lines = text.split("\n")
codes_found = []
for idx, line in enumerate(lines):
    match = re.search(r"\b(B1\.\d+\.\d+\.\d+\.\d+|B1\.\d+\.\d+\.\d+)\b", line)
    if match:
        code = match.group(1)
        # print some context around it
        start = max(0, idx - 1)
        end = min(len(lines), idx + 3)
        context = " | ".join([lines[i].strip() for i in range(start, end) if lines[i].strip()])
        codes_found.append((code, context))

print(f"Total codes found: {len(codes_found)}")
for code, context in codes_found[:30]:
    print(f"{code:15s} : {context[:150]}")
