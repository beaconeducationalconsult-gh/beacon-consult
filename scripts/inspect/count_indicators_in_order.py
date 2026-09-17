# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

terms_text = {}
term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
term_3_start = text.find("TERM 3")
teacher_notes_start = text.find("NOTES FOR THE TEACHER")

terms_text[1] = text[term_1_start:term_2_start]
terms_text[2] = text[term_2_start:term_3_start]
terms_text[3] = text[term_3_start:teacher_notes_start if teacher_notes_start != -1 else len(text)]

for t_id, t_text in terms_text.items():
    # Find all indicators of form B1.X.X.X.X
    inds = re.findall(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t_text)
    print(f"Term {t_id}: Total indicators found: {len(inds)}")
    print(f"First 10: {inds[:10]}")
    print(f"Last 10: {inds[-10:]}")
