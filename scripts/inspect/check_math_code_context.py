# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
with open("math_raw_text.txt") as f:
    text = f.read()

import re
matches = list(re.finditer(r"B1\.1\.2\.1\.1", text))
print("B1.1.2.1.1 matches:", len(matches))
for i, m in enumerate(matches):
    print(f"\nMatch {i+1}:")
    print(text[max(0, m.start()-100):m.end()+400])
