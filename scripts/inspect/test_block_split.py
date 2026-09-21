# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
t1_text = text[term_1_start:term_2_start]

matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t1_text))

for i in range(10):
    ind_pos = matches[i].start()
    next_ind_pos = matches[i+1].start() if i+1 < len(matches) else len(t1_text)
    block = t1_text[ind_pos:next_ind_pos]
    
    # Let's search for "Mon–\nFri" or "Mon–" or "Mon-Fri" or "Mon" in the block to split
    split_match = re.search(r"\bMon[–-]\s*Fri\b|\bMon–\b|\bMon-\b", block)
    if split_match:
        details_block = block[:split_match.start()]
        next_metadata = block[split_match.start():]
    else:
        details_block = block
        next_metadata = ""
        
    print(f"\n--- ENTRY {i+1} Details (Code: {matches[i].group(1)}) ---")
    print(repr(details_block[:200]) + " ... " + repr(details_block[-200:]))
