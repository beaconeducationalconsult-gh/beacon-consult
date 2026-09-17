# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
with open("science_raw_text.txt") as f:
    text = f.read()

pages = text.split("=== PAGE ")
print("=== PAGE 11 FULL ===")
print(pages[11])
