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

# Let's inspect Entry 1
ind_pos = matches[0].start()
next_ind_pos = matches[1].start()
pre_text = t1_text[0:ind_pos]
post_text = t1_text[ind_pos:next_ind_pos]

print("=== PRE_TEXT ===")
print(repr(pre_text))
print("=== POST_TEXT ===")
print(repr(post_text))
