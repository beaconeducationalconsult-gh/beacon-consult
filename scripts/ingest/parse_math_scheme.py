# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

def parse_math_scheme():
    with open("math_raw_text.txt") as f:
        text = f.read()

    # Split by Term
    term_1_start = text.find("TERM 1")
    term_2_start = text.find("TERM 2")
    term_3_start = text.find("TERM 3")
    notes_start = text.find("NOTES FOR THE TEACHER")

    terms_text = {
        1: text[term_1_start:term_2_start],
        2: text[term_2_start:term_3_start],
        3: text[term_3_start:notes_start if notes_start != -1 else len(text)]
    }

    lessons = []
    global_idx = 1

    # Standard patterns for each of the 4 strands
    strand_names = {
        1: "NUMBER",
        2: "ALGEBRA",
        3: "GEOMETRY AND MEASUREMENT",
        4: "DATA"
    }

    for term_id in [1, 2, 3]:
        t_text = terms_text[term_id]
        
        # We search for the 5-part indicators (B1.x.x.x.x)
        matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t_text))
        print(f"Term {term_id} has {len(matches)} indicators.")
        
        for i in range(len(matches)):
            ind_code = matches[i].group(1)
            ind_pos = matches[i].start()
            next_ind_pos = matches[i+1].start() if i+1 < len(matches) else len(t_text)
            prev_ind_pos = matches[i-1].start() if i > 0 else 0
            
            # Extract blocks
            pre_block = t_text[prev_ind_pos:ind_pos]
            post_block = t_text[ind_pos:next_ind_pos]
            
            # Clean next entry from post_block if present
            split_match = re.search(r"\bMon[–-]\s*Fri\b|\bMon–\b|\bMon-\b", post_block)
            if split_match:
                details_text = post_block[:split_match.start()]
            else:
                details_text = post_block
                
            # Find Content Standard Code
            cs_matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+)\b", pre_block))
            cs_code = cs_matches[-1].group(1) if cs_matches else "N/A"
            
            # Sub-strand
            sub_strand = "N/A"
            pre_clean = re.sub(r'\s+', ' ', pre_block).strip()
            sub_strand_match = re.search(r"\d+\.\s+([A-Za-z\s&,-:]+)\s+B1\.", pre_clean)
            if sub_strand_match:
                sub_strand = sub_strand_match.group(1).strip()
                
            # Content Standard Description
            cs_desc = "N/A"
            if cs_code != "N/A":
                cs_pos_in_pre = pre_clean.find(cs_code)
                if cs_pos_in_pre != -1:
                    cs_desc = pre_clean[cs_pos_in_pre + len(cs_code):].strip()
                    cs_desc = re.sub(r"\bB2\..*$", "", cs_desc).strip()
                    cs_desc = re.sub(r"\bB1\..*$", "", cs_desc).strip()
            
            # Indicator text
            details_clean = re.sub(r'\s+', ' ', details_text).strip()
            ind_desc = "N/A"
            ind_pos_in_details = details_clean.find(ind_code)
            if ind_pos_in_details != -1:
                ind_desc = details_clean[ind_pos_in_details + len(ind_code):].strip()
                
            # Is Revision?
            is_revision = False
            if "[REVISION]" in ind_desc or "[revision]" in ind_desc.lower():
                is_revision = True
                ind_desc = ind_desc.replace("[REVISION]", "").strip()
                ind_desc = ind_desc.replace("[revision]", "").strip()
                
            lessons.append({
                "term": term_id,
                "week": (i // 4) + 1,
                "strand_num": (i % 4) + 1,
                "strand_name": strand_names[(i % 4) + 1],
                "sub_strand": sub_strand,
                "cs_code": cs_code,
                "cs_desc": cs_desc,
                "ind_code": ind_code,
                "ind_desc": ind_desc,
                "is_revision": is_revision,
                "raw_details": details_clean
            })
            
    print(f"Total parsed math lessons: {len(lessons)}")
    with open("math_parsed_lessons_raw.json", "w") as f:
        json.dump(lessons, f, indent=4)
    print("Saved raw math parsed lessons to math_parsed_lessons_raw.json")

parse_math_scheme()
