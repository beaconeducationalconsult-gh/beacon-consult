# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's find Term 1 text
term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
t1_text = text[term_1_start:term_2_start]

# Find all 5-part indicators in Term 1 and their positions
matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t1_text))
print(f"Found {len(matches)} indicators in Term 1.")

# Let's inspect the first 3 entries' blocks
for i in range(3):
    start_pos = matches[i].start()
    end_pos = matches[i+1].start() if i+1 < len(matches) else len(t1_text)
    block = t1_text[start_pos:end_pos]
    print(f"\n--- ENTRY {i+1} (Code: {matches[i].group(1)}) ---")
    print(block[:600])
    print("-" * 50)
