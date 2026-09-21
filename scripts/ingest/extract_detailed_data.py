# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

with open("science_raw_text.txt") as f:
    text = f.read()

# Split by Term
term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
term_3_start = text.find("TERM 3")
teacher_notes_start = text.find("NOTES FOR THE TEACHER")

terms_text = {
    1: text[term_1_start:term_2_start],
    2: text[term_2_start:term_3_start],
    3: text[term_3_start:teacher_notes_start if teacher_notes_start != -1 else len(text)]
}

# Standard patterns for each strand
strand_names = {
    1: "DIVERSITY OF MATTER",
    2: "CYCLES",
    3: "SYSTEMS",
    4: "FORCES AND ENERGY",
    5: "HUMANS AND THE ENVIRONMENT"
}

sub_strand_names = {
    1: "Living and Non-Living Things",
    2: "Earth Science",
    3: "The Human Body Systems",
    4: "Sources and Forms of Energy",
    5: "Personal Hygiene and Sanitation"
}

# Let's inspect some text around the first few indicators in Term 1 to write a robust regex or split method.
print("=== SAMPLE TEXT AROUND B1.1.1.1.1 IN TERM 1 ===")
pos = terms_text[1].find("B1.1.1.1.1")
print(terms_text[1][max(0, pos-100):pos+500])
