# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json
from collections import defaultdict

with open("science_parsed_lessons_raw.json") as f:
    lessons = json.load(f)

counts = defaultdict(int)
for l in lessons:
    counts[l["ind_code"]] += 1

print("Indicator frequencies across 180 lessons:")
for k, v in sorted(counts.items()):
    print(f"  {k} : {v:2d} times")
