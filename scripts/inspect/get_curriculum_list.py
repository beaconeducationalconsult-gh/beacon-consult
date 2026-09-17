# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

def parse_science_curriculum():
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

    curriculum = []
    global_lesson_num = 1

    # Let's map Strand names and Sub-strand names
    strand_map = {
        "1": "DIVERSITY OF MATTER",
        "2": "CYCLES",
        "3": "SYSTEMS",
        "4": "FORCES AND ENERGY",
        "5": "HUMANS AND THE ENVIRONMENT"
    }

    # Let's extract indicators in order for each term
    for term_id in [1, 2, 3]:
        t_text = terms_text[term_id]
        
        # We know there are exactly 60 indicators of the form B1.x.x.x.x in each term
        matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t_text))
        print(f"Term {term_id} has {len(matches)} indicators.")
        
        # For each indicator, let's extract details
        for i in range(len(matches)):
            ind_code = matches[i].group(1)
            ind_pos = matches[i].start()
            next_ind_pos = matches[i+1].start() if i+1 < len(matches) else len(t_text)
            prev_ind_pos = matches[i-1].start() if i > 0 else 0
            
            # Extract post_text (contains details)
            post_text = t_text[ind_pos:next_ind_pos]
            # Extract pre_text (contains metadata like content standard)
            pre_text = t_text[prev_ind_pos:ind_pos]
            
            # Find Content Standard code B1.x.x.x (4 parts)
            cs_matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+)\b", pre_text))
            cs_code = cs_matches[-1].group(1) if cs_matches else "N/A"
            
            # Let's clean up post_text and split into fields
            # Core competencies are usually after the indicator text and end before T/L Resources
            # Let's find some standard markers like "Critical Thinking", "Problem Solving", "Personal Development"
            # Since table columns are: Core Competencies | T/L Resources | Keywords | Assessment
            # Let's look for known keywords and assessments in the post_text
            
            # Let's clean the block text
            block_lines = [l.strip() for l in post_text.split("\n") if l.strip()]
            
            # The first line is the indicator code
            # The next few lines represent the indicator description until we reach Core Competencies
            # Core Competencies usually contain "Critical Thinking", "Problem Solving", "Collaboration", "Creativity", "Innovation", "Personal Development", "Cultural Identity", "Global Citizenship"
            # Resources are schoolyard, specimens, mirrors, soap, tap, etc.
            # Keywords are observe, identify, etc.
            # Assessment is class exercise, sorting, test, etc.
            
            curriculum.append({
                "term": term_id,
                "week": (i // 5) + 1,
                "strand_num": (i % 5) + 1,
                "strand_name": strand_map[str((i % 5) + 1)],
                "cs_code": cs_code,
                "ind_code": ind_code,
                "raw_post_text": post_text[:400]
            })
            
    # Print the first 10 items in Term 1
    print("\nFirst 10 items in Term 1:")
    for item in curriculum[:10]:
        print(f"Wk {item['week']} Day {item['strand_num']}: Strand: {item['strand_name']}, CS: {item['cs_code']}, Ind: {item['ind_code']}")

parse_science_curriculum()
