# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re

with open("science_raw_text.txt") as f:
    text = f.read()

# Split by TERM
# TERM 1 starts at "TERM 1"
# TERM 2 starts at "TERM 2"
# TERM 3 starts at "TERM 3"

term_parts = re.split(r"TERM \d", text)
print(f"Term parts found: {len(term_parts)}")

# Note: term_parts[0] is the intro/metadata
# term_parts[1] is Term 1
# term_parts[2] is Term 2
# term_parts[3] is Term 3

# For each term, let's find the weeks.
# Within each term's text, let's search for "Wk" or week rows.
# Actually, let's search for the indicators in order and associate them with weeks.
# In Term 1, we have Weeks 1 to 12.
# Let's see: on Page 1 to 11 (Term 1):
# Let's search for lines containing week numbers and see how they map.
# In the text, we have Page boundaries.
# Let's map page numbers to Term and Week:
# Term 1:
# Page 1: Week 1
# Page 2: Week 2
# Page 3: Week 3
# Page 4: Week 4, Week 5 (starts with "4" and then "5")
# Page 5: Week 6
# Page 6: Week 7
# Page 7: Week 8
# Page 8: Week 9
# Page 9: Week 10
# Page 10: Week 11, Week 12 (starts with "11" and then "12")
# Page 11: Week 12 (rest of Week 12)

# Let's write a script that parses each page, finds the week numbers, and then finds the indicators associated with those weeks!
