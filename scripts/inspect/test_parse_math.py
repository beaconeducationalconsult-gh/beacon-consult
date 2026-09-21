# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("math_raw_text.txt") as f:
    text = f.read()

pages = text.split("=== PAGE ")
print("Total pages in Math raw:", len(pages) - 1)

# Let's see what terms exist and how indicators of form B1.x.x.x.x are found in order
# Let's count them!
term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
term_3_start = text.find("TERM 3")
notes_start = text.find("NOTES FOR THE TEACHER")

terms_text = {
    1: text[term_1_start:term_2_start],
    2: text[term_2_start:term_3_start],
    3: text[term_3_start:notes_start if notes_start != -1 else len(text)]
}

for term_id, t_text in terms_text.items():
    inds = re.findall(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t_text)
    print(f"Term {term_id}: found {len(inds)} indicators in order.")
    print("  First 5:", inds[:5])
    print("  Last 5:", inds[-5:])
