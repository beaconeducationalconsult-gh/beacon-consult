# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's see how many terms we have.
# Split by TERM 1, TERM 2, TERM 3
terms = {}
term_split = re.split(r"TERM (\d)\s+·\s+Weeks \d+–\d+", text)
# Wait, let's look at the result of splitting
print("Term split length:", len(term_split))
# If it split correctly, term_split[1] is '1', term_split[2] is Term 1 text, term_split[3] is '2', etc.
if len(term_split) >= 7:
    terms[1] = term_split[2]
    terms[2] = term_split[4]
    terms[3] = term_split[6]
else:
    # Let's search using a simpler split or regex
    print("Trying alternative term split...")
    term_1_start = text.find("TERM 1")
    term_2_start = text.find("TERM 2")
    term_3_start = text.find("TERM 3")
    teacher_notes_start = text.find("NOTES FOR THE TEACHER")
    
    if term_1_start != -1 and term_2_start != -1 and term_3_start != -1:
        terms[1] = text[term_1_start:term_2_start]
        terms[2] = text[term_2_start:term_3_start]
        terms[3] = text[term_3_start:teacher_notes_start if teacher_notes_start != -1 else len(text)]

for term_id, term_text in terms.items():
    print(f"Term {term_id} text length: {len(term_text)}")

# Let's write a python script to scan Term 1 for week markers and print them.
