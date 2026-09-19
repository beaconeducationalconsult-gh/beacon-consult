# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json

def clean_txt(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

with open("science_raw_text.txt") as f:
    text = f.read()

# Let's find all occurrences of indicator codes B1.x.x.x.x and content standard codes B1.x.x.x
# We will parse the text term by term to build a full list of all 180 lessons!
# This is incredibly powerful. We can build a complete list of 180 lesson entries.
# Each lesson entry will have:
# - Lesson number: 1 to 180
# - Term: 1 to 3
# - Week: 1 to 12
# - Day: Monday to Friday
# - Strand: 1 to 5 (with names)
# - Sub-strand (e.g. "1. Living and Non-Living Things")
# - Content Standard Code (e.g. B1.1.1.1)
# - Content Standard Text
# - Indicator Code (e.g. B1.1.1.1.1)
# - Indicator Text
# - Revision: True/False
# - Core Competencies
# - T/L Resources
# - Keywords
# - Assessment

# Let's map Strand names
strand_names = {
    1: "DIVERSITY OF MATTER",
    2: "CYCLES",
    3: "SYSTEMS",
    4: "FORCES AND ENERGY",
    5: "HUMANS AND THE ENVIRONMENT"
}

# Let's define the days of the week
days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

term_1_start = text.find("TERM 1")
term_2_start = text.find("TERM 2")
term_3_start = text.find("TERM 3")
teacher_notes_start = text.find("NOTES FOR THE TEACHER")

terms_text = {
    1: text[term_1_start:term_2_start],
    2: text[term_2_start:term_3_start],
    3: text[term_3_start:teacher_notes_start if teacher_notes_start != -1 else len(text)]
}

lessons = []
global_lesson_num = 1

for term_id in [1, 2, 3]:
    t_text = terms_text[term_id]
    matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+\.\d+)\b", t_text))
    
    for i in range(len(matches)):
        ind_code = matches[i].group(1)
        ind_pos = matches[i].start()
        next_ind_pos = matches[i+1].start() if i+1 < len(matches) else len(t_text)
        prev_ind_pos = matches[i-1].start() if i > 0 else 0
        
        # Get blocks
        pre_block = t_text[prev_ind_pos:ind_pos]
        post_block = t_text[ind_pos:next_ind_pos]
        
        # Clean next entry from post_block if present
        split_match = re.search(r"\bMon[–-]\s*Fri\b|\bMon–\b|\bMon-\b", post_block)
        if split_match:
            details_text = post_block[:split_match.start()]
        else:
            details_text = post_block
            
        # Clean pre_block to find CS and sub-strand
        pre_clean = clean_txt(pre_block)
        details_clean = clean_txt(details_text)
        
        # Find Content Standard Code
        cs_matches = list(re.finditer(r"\b(B1\.\d+\.\d+\.\d+)\b", pre_block))
        cs_code = cs_matches[-1].group(1) if cs_matches else "N/A"
        
        # Let's parse sub-strand
        # Sub-strand is usually after Strand name and before Content Standard
        # Strands are 1. DIVERSITY OF MATTER, 2. CYCLES, 3. SYSTEMS, 4. FORCES AND ENERGY, 5. HUMANS AND THE ENVIRONMENT
        # Let's use simple regex to extract sub-strand
        sub_strand = "N/A"
        sub_strand_match = re.search(r"\d+\.\s+([A-Za-z\s&-]+)\s+B1\.", pre_clean)
        if sub_strand_match:
            sub_strand = sub_strand_match.group(1).strip()
        else:
            # Try another pattern
            sub_strand_match = re.search(r"Sub-strand\s*:\s*([A-Za-z\s&-]+)\s+B1\.", pre_clean, re.IGNORECASE)
            if sub_strand_match:
                sub_strand = sub_strand_match.group(1).strip()
                
        # Find Content Standard Description
        # Content Standard Description starts after CS Code and ends before the end of pre_block
        cs_desc = "N/A"
        if cs_code != "N/A":
            cs_pos_in_pre = pre_clean.find(cs_code)
            if cs_pos_in_pre != -1:
                cs_desc = pre_clean[cs_pos_in_pre + len(cs_code):].strip()
                # Remove any leftover trailing text like "B2.1.1.1..."
                cs_desc = re.sub(r"\bB2\..*$", "", cs_desc).strip()
                cs_desc = re.sub(r"\bB1\..*$", "", cs_desc).strip()
                
        # Parse details_clean for Indicator text, Core Competencies, T/L Resources, Keywords, Assessment
        # The details_clean text starts with the Indicator Code
        ind_desc = "N/A"
        ind_pos_in_details = details_clean.find(ind_code)
        if ind_pos_in_details != -1:
            ind_desc = details_clean[ind_pos_in_details + len(ind_code):].strip()
            
        # Let's detect if it is a revision lesson
        is_revision = False
        if "[REVISION]" in ind_desc or "[revision]" in ind_desc.lower():
            is_revision = True
            # Remove [REVISION] tag from standard description for presentation but keep it as a flag
            ind_desc = ind_desc.replace("[REVISION]", "").strip()
            ind_desc = ind_desc.replace("[revision]", "").strip()
            
        # Core Competencies, Resources, Keywords, Assessment are embedded in ind_desc
        # Let's see if we can do a smart split by looking for keywords or known phrases
        # Let's split on "Critical Thinking" or "Problem Solving" or "Personal Development" or "Collaboration"
        # Core competencies are: Critical Thinking & Problem Solving; Communication & Collaboration, etc.
        # Let's write a python regex to split by the core competencies
        competencies = "Critical Thinking & Problem Solving; Communication & Collaboration"
        resources = "N/A"
        keywords = "N/A"
        assessment = "N/A"
        
        # Let's do a smart split using regex of common keywords and resources
        # We can find where the competencies are
        comp_match = re.search(r"\b(Critical Thinking|Problem Solving|Communication|Collaboration|Personal Development|Creativity|Innovation|Cultural Identity|Global Citizenship)\b", ind_desc)
        if comp_match:
            # Indicator text is before the competencies
            ind_text_extracted = ind_desc[:comp_match.start()].strip()
            # Let's extract competencies and the rest
            rest = ind_desc[comp_match.start():].strip()
            # Remove trailing cross-references like B2.1.1.1...
            ind_text_clean = re.sub(r"\bB2\..*$", "", ind_text_extracted).strip()
            ind_text_clean = re.sub(r"\bB1\..*$", "", ind_text_clean).strip()
            
            # Now let's find Keywords in rest. Keywords are usually listed after resources
            # In the PDF, Keywords are like "observe, describe, different..."
            # Let's search for keywords by looking for comma-separated lists or explicit keywords
            # Let's search for some common keywords from our unique indicators list
            # We can also search for assessment
            # Let's split the 'rest' text
            # Usually, the competencies end at the semicolon or after "Collaboration" or "Leadership"
            comp_end_match = re.search(r"(Collaboration|Leadership|Citizenship|Innovation|Solving)\s*;\s*|(Collaboration|Leadership|Citizenship|Innovation|Solving)\s+", rest)
            if comp_end_match:
                competencies = rest[:comp_end_match.end()].strip()
                resources_and_rest = rest[comp_end_match.end():].strip()
                
                # In resources_and_rest, we have T/L Resources, Keywords, and Assessment
                # Let's see if we can identify keywords
                # Keywords are usually comma-separated words at the end
                # Assessment is like "Observation worksheet", "Oral Q&A", "Practical sorting task", etc.
                # Let's find keywords by looking for words matching the keywords column of the page
                # We can write a parser that looks for keywords and assessments
                # Let's do a simple split by keywords or assessment
                pass
            
        # Let's append the record
        lessons.append({
            "lesson_num": global_lesson_num,
            "term": term_id,
            "week": (i // 5) + 1,
            "day": days_of_week[i % 5],
            "strand_num": (i % 5) + 1,
            "strand_name": strand_names[(i % 5) + 1],
            "sub_strand": sub_strand,
            "cs_code": cs_code,
            "cs_desc": cs_desc,
            "ind_code": ind_code,
            "ind_desc": ind_desc,
            "is_revision": is_revision,
            "raw_details": details_clean
        })
        global_lesson_num += 1

print(f"Total parsed lessons: {len(lessons)}")
with open("science_parsed_lessons_raw.json", "w") as f:
    json.dump(lessons, f, indent=4)
print("Saved raw parsed lessons to science_parsed_lessons_raw.json")
