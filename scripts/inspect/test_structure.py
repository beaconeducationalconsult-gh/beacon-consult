# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
t1_text = text[term_1_start:term_2_start]

matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t1_text))

for i in range(10): # Let's print details for the first 10 entries
    ind_pos = matches[i].start()
    next_ind_pos = matches[i+1].start() if i+1 < len(matches) else len(t1_text)
    prev_ind_pos = matches[i-1].start() if i > 0 else 0
    
    pre_text = t1_text[prev_ind_pos:ind_pos]
    post_text = t1_text[ind_pos:next_ind_pos]
    
    # Let's see: from pre_text, find Content Standard code B1.x.x.x (4 parts)
    # We look backwards or find all 4-part codes
    cs_matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+)\b", pre_text))
    cs_code = cs_matches[-1].group(1) if cs_matches else "N/A"
    
    # Print summary
    print(f"Entry {i+1:2d} | CS: {cs_code:10s} | Ind: {matches[i].group(1):12s} | Pre-len: {len(pre_text):3d} | Post-len: {len(post_text):3d}")
