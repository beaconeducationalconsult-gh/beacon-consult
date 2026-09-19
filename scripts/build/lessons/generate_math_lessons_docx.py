# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Load the clean math curriculum database and parsed raw math lessons
with open("math_curriculum_db_clean.json") as f:
    cur_db = json.load(f)

with open("math_parsed_lessons_raw.json") as f:
    raw_lessons = json.load(f)

print(f"Loaded {len(cur_db)} unique indicators and {len(raw_lessons)} raw lessons.")

# Let's group the 144 raw lessons by week
# Since there are 4 indicators per week:
# - index 0 is Strand 1 (Number)
# - index 1 is Strand 2 (Algebra)
# - index 2 is Strand 3 (Geometry)
# - index 3 is Strand 4 (Data)
weeks_data = {}
for l in raw_lessons:
    term_id = l["term"]
    wk_id = l["week"]
    strand_num = l["strand_num"]
    
    key = (term_id, wk_id)
    if key not in weeks_data:
        weeks_data[key] = {}
    weeks_data[key][strand_num] = l

print(f"Grouped raw lessons into {len(weeks_data)} weeks.")

# Detailed activities generator for Mathematics
def get_math_activities(ind_code, is_revision, day, session_type):
    meta = cur_db.get(ind_code, {
        "strand": "1. NUMBER",
        "sub_strand": "1. Number: Counting, Representation, Cardinality & Ordinality",
        "ind_desc": "Use number names, counting sequences and how to count to find out 'how many?'",
        "competencies": "Critical Thinking & Problem Solving; Communication & Collaboration",
        "resources": "Counters; number cards",
        "keywords": "number, count",
        "assessment": "Class exercise; teacher observation"
    })
    
    ind_desc = meta["ind_desc"]
    resources = meta["resources"]
    keywords = meta["keywords"]
    strand = meta["strand"]
    sub_strand = meta["sub_strand"]
    
    # Session title and performance indicator
    if session_type == "session_1":
        session_title = "Session 1 of 2 — Introduction & Concrete Modelling"
        perf_indicator = f"By the end of the lesson, learners should be able to identify and model the concept of: {ind_desc.lower()}"
    elif session_type == "session_2":
        session_title = "Session 2 of 2 — Practice, Representation & Application"
        perf_indicator = f"By the end of the lesson, learners should be able to practice and represent: {ind_desc.lower()}"
    else:
        # Single session indicators (Algebra, Geometry, Data)
        if is_revision:
            session_title = "Session 1 of 1 — Weekly Revision & Consolidation"
            perf_indicator = f"By the end of the lesson, learners should be able to review and demonstrate: {ind_desc.lower()}"
        else:
            session_title = "Session 1 of 1 — Full Concept Exploration"
            perf_indicator = f"By the end of the lesson, learners should be able to explore and solve tasks on: {ind_desc.lower()}"

    # Starters
    if "NUMBER" in strand:
        if session_type == "session_1":
            starter = [
                "Greet learners warmly. Lead the class in a fun number song like '1, 2, Buckle My Shoe' or 'Ten Green Bottles' with clapping.",
                "Have pupils do a quick oral counting exercise from 1 to 20, first forwards and then backwards.",
                "NEW TODAY: State the lesson focus: 'Today we will begin learning about " + sub_strand.lower() + " using real counters.'",
                "Write today's key words on the board: '" + keywords.split(",")[0].strip() + "' and read it aloud together."
            ]
        else:
            starter = [
                "Greet learners. Stand in a circle and play a quick game of 'Mental Math Buzz' where we count and clap on even numbers.",
                "Review yesterday's work: ask 2-3 pupils to show a number of counters on their desk.",
                "NEW TODAY: State the focus: 'Today we are going to practice writing and representing our " + sub_strand.lower() + ".'",
                "Write the key words '" + ", ".join(keywords.split(",")[:2]) + "' on the board and pronounce them."
            ]
    elif "ALGEBRA" in strand:
        starter = [
            "Greet learners warmly. Lead the class in a body pattern clap: 'Clap, Clap, Stamp, Clap, Clap, Stamp.' Have pupils join in.",
            "Ask: 'What comes next in our clapping pattern?' (Call on 2-3 pupils).",
            "NEW TODAY: State the focus: 'Today we are going to create and extend beautiful patterns of shapes and numbers.'",
            "Write the keyword '" + keywords.split(",")[0].strip() + "' on the board and read it aloud."
        ]
    elif "GEOMETRY" in strand:
        starter = [
            "Greet learners. Stand up and sing 'This is a circle, this is a square' to a popular local primary school tune.",
            "Have pupils look around the room and point to one round object and one flat object.",
            "NEW TODAY: Introduce today's focus: 'Today we are starting our study of " + sub_strand.lower() + ".'",
            "Write today's key term '" + keywords.split(",")[0].strip() + "' on the board and read it together."
        ]
    else:  # DATA
        starter = [
            "Greet learners warmly. Ask pupils: 'How many boys are in the front row? Let's count them together.'",
            "Show three different colored blocks and say: 'Let's see which color our class likes best!'",
            "NEW TODAY: Introduce today's lesson: 'Today we are learning how to collect, organize and represent our own data.'",
            "Write today's key word '" + keywords.split(",")[0].strip() + "' on the board and read it aloud."
        ]

    # Main Activities
    if "NUMBER" in strand:
        if session_type == "session_1":
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher models. Displays concrete counters (stones, bottle caps) or ten-frames. Shows how to count, add, subtract or partition a whole group clearly.",
                "ACTIVITY 2 (Guided Concrete Practice - 5 min): Pupils work in small groups. Teacher gives each group a bundle of counters and guides them to repeat the count, addition, or subtraction.",
                "ACTIVITY 3 (Group Discovery - 7 min): Groups solve simple concrete puzzles (e.g. making groups of 5, matching coins to values, or folding paper to show halves).",
                "ACTIVITY 4 (Review - 3 min): Teacher monitors groups, correcting hand placements on counters, and reinforcing mathematical vocabulary."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher reviews yesterday's concrete concepts and shows how to represent them on the board using drawings (circles, tallies, number lines, symbols).",
                "ACTIVITY 2 (Guided Pictorial Practice - 5 min): Pupils draw circles in their books to match number cards or symbols (<, >, =). Teacher guides them to use place value and counting strategies.",
                "ACTIVITY 3 (Individual Practice - 7 min): Pupils complete a series of simple pictorial math tasks in their notebooks (e.g., adding two groups, counting halves, writing missing numbers).",
                "ACTIVITY 4 (Sharing & Discussion - 3 min): Selected pupils show their notebook drawings on the board. Class applauds, and teacher summarizes key math patterns."
            ]
    elif "ALGEBRA" in strand:
        main = [
            "ACTIVITY 1 (Modelling - 5 min): Teacher uses colored blocks (or drawings) to create an ABAB repeating pattern: 'Red triangle, blue circle, red triangle, blue circle.' Demonstrates finding the core pattern.",
            "ACTIVITY 2 (Guided Practice - 5 min): Pupils use pattern cards and colored counters on their desks to duplicate and extend the teacher's pattern. Teacher checks their placements.",
            "ACTIVITY 3 (Group Creative Task - 7 min): In small groups, pupils create their own repeating patterns with 3 or 4 elements using seeds, bottle caps, or drawings. They explain their pattern to other groups.",
            "ACTIVITY 4 (Peer Review - 3 min): Groups walk around to view other tables' patterns, trying to identify and correct any errors. Teacher commends great peer sharing."
        ]
    elif "GEOMETRY" in strand:
        main = [
            "ACTIVITY 1 (Modelling - 5 min): Teacher displays real 3D shapes (sphere, cylinder, cube) or 2D cut-outs (triangle, rectangle). Models describing attributes: 'This is a cube. It has flat faces and corners.'",
            "ACTIVITY 2 (Guided Exploration - 5 min): Pupils hold shape models, touch the edges, faces, and corners. For position/measurement, pupils follow instructions (e.g. 'Put the block behind your box').",
            "ACTIVITY 3 (Group Sorting / Comparison - 7 min): Groups sort a mixture of 2D/3D shapes by attributes (defining vs. non-defining) or compare pairs of objects (longer/shorter, heavier/lighter).",
            "ACTIVITY 4 (Reflection & Feedback - 3 min): Selected pupils stand up and describe their shape or comparison to the class: 'My pencil is longer than my crayon.' Teacher reinforces geometric terms."
        ]
    else:  # DATA
        main = [
            "ACTIVITY 1 (Modelling - 5 min): Teacher models gathering data. Asks 10 pupils their favorite fruit (mango, banana, orange). Writes tally marks on the blackboard and counts them.",
            "ACTIVITY 2 (Guided Representation - 5 min): Teacher guides pupils to draw simple squares/circles to represent each vote in a neat pictograph on the board. Class counts the total data points.",
            "ACTIVITY 3 (Group Data Collection - 7 min): In small groups, pupils collect data on their own (e.g., color of pencils, type of shoes) and organize it into a small pictograph using cut-out picture cards.",
            "ACTIVITY 4 (Comparison Discussion - 3 min): Groups compare categories in their data (e.g., 'Most pencils are yellow, least are blue'). Teacher checks and validates their tallying and comparisons."
        ]

    # Plenaries
    if "NUMBER" in strand:
        if session_type == "session_1":
            plenary = [
                "Whole class sings a joyful counting song together with body actions.",
                "Ask: 'What did we learn to count or do today?' (Have 2-3 pupils explain).",
                "Homework: 'Find 10 small objects at home (seeds, bottle caps) and count them to your parents.'",
                "Preview tomorrow's lesson: we will write and draw our numbers!"
            ]
        else:
            plenary = [
                "Whole class recites a consolidated number rhyme or does a mental math flash drill.",
                "Ask: 'Who can tell me what symbol or number we drew today?' (Call on 2-3 pupils).",
                "Homework: 'Complete today's notebook drawing at home and show it to your family.'",
                "Preview tomorrow's exciting lesson on Algebra and Patterns."
            ]
    elif "ALGEBRA" in strand:
        plenary = [
            "Whole class does a fun clapping and stomping pattern together.",
            "Ask: 'What is a pattern?' (Call on 2-3 pupils to describe in their own words).",
            "Homework: 'Look for patterns in your home (on fabrics, mats, walls) and draw them in your notebook.'",
            "Preview tomorrow's lesson on Geometry and Shapes."
        ]
    elif "GEOMETRY" in strand:
        plenary = [
            "Whole class sings today's shape song with physical movements.",
            "Ask: 'What shape or position did we study today?' (Have 2-3 pupils describe).",
            "Homework: 'Find two shapes or compare two objects in your kitchen and tell your parents which is bigger/longer.'",
            "Preview tomorrow's lesson on Data and charts."
        ]
    else:  # DATA
        plenary = [
            "Whole class counts today's data charts and celebrates with a rhythmic clap.",
            "Ask: 'Why do we collect data?' (Call on 2-3 pupils to share why charts are useful).",
            "Homework: 'Ask 5 family members if they like tea or juice better. Tally their answers.'",
            "Preview next week's exciting mathematics adventure."
        ]

    return {
        "session_title": session_title,
        "perf_indicator": perf_indicator,
        "starter": starter,
        "main": main,
        "plenary": plenary
    }

# Build the 180 enriched math lessons list
enriched_math_lessons = []
global_lesson_num = 1

days_mapping = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Sort week keys so we iterate chronologically
for term_id in [1, 2, 3]:
    for wk_id in range(1, 13):
        key = (term_id, wk_id)
        if key not in weeks_data:
            print(f"Warning: missing week data for Term {term_id}, Week {wk_id}")
            continue
            
        week_strands = weeks_data[key]
        
        # 1. Monday (Strand 1 - Number, Session 1)
        strand1_meta = week_strands[1]
        act_mon = get_math_activities(strand1_meta["ind_code"], strand1_meta["is_revision"], "Monday", "session_1")
        
        # 2. Tuesday (Strand 1 - Number, Session 2)
        act_tue = get_math_activities(strand1_meta["ind_code"], strand1_meta["is_revision"], "Tuesday", "session_2")
        
        # 3. Wednesday (Strand 2 - Algebra, Session 1 of 1)
        strand2_meta = week_strands[2]
        act_wed = get_math_activities(strand2_meta["ind_code"], strand2_meta["is_revision"], "Wednesday", "single")
        
        # 4. Thursday (Strand 3 - Geometry, Session 1 of 1)
        strand3_meta = week_strands[3]
        act_thu = get_math_activities(strand3_meta["ind_code"], strand3_meta["is_revision"], "Thursday", "single")
        
        # 5. Friday (Strand 4 - Data, Session 1 of 1)
        strand4_meta = week_strands[4]
        act_fri = get_math_activities(strand4_meta["ind_code"], strand4_meta["is_revision"], "Friday", "single")
        
        # Combine all days into the list
        days_acts = [
            (1, "Monday", strand1_meta, act_mon, "session_1"),
            (1, "Tuesday", strand1_meta, act_tue, "session_2"),
            (2, "Wednesday", strand2_meta, act_wed, "single"),
            (3, "Thursday", strand3_meta, act_thu, "single"),
            (4, "Friday", strand4_meta, act_fri, "single")
        ]
        
        for strand_num, day_name, meta, act, sess_type in days_acts:
            rpk_map = {
                "1. NUMBER": "Learners have used informal counting sequences at home and in KG to count their fingers, toys, or food items.",
                "2. ALGEBRA": "Learners have observed simple patterns on clothing, floors, and in daily clapping sequences.",
                "3. GEOMETRY AND MEASUREMENT": "Learners have seen flat and solid objects at home and are familiar with words like big, small, up, and down.",
                "4. DATA": "Learners have sorted toys or grouped objects by color or size in informal play."
            }
            rpk = rpk_map.get(meta["strand_name"], "Learners have basic everyday experiences related to this mathematics topic.")
            
            enriched_math_lessons.append({
                "lesson_num": global_lesson_num,
                "term": term_id,
                "week": wk_id,
                "day": day_name,
                "strand_num": strand_num,
                "strand_name": meta["strand_name"],
                "sub_strand": meta["sub_strand"],
                "cs_code": meta["cs_code"],
                "cs_desc": meta["cs_desc"],
                "ind_code": meta["ind_code"],
                "ind_desc": meta["ind_desc"],
                "is_revision": meta["is_revision"],
                "session_title": act["session_title"],
                "perf_indicator": act["perf_indicator"],
                "competencies": cur_db.get(meta["ind_code"], {}).get("competencies", "Critical Thinking & Problem Solving; Communication & Collaboration"),
                "resources": cur_db.get(meta["ind_code"], {}).get("resources", "Counters; number cards"),
                "keywords": cur_db.get(meta["ind_code"], {}).get("keywords", "number"),
                "rpk": rpk,
                "starter": act["starter"],
                "main": act["main"],
                "plenary": act["plenary"],
                "assessment": cur_db.get(meta["ind_code"], {}).get("assessment", "Class exercise; teacher observation")
            })
            global_lesson_num += 1

print(f"Generated {len(enriched_math_lessons)} enriched math lessons successfully.")

# Save enriched lessons to JSON
with open("math_lessons_enriched.json", "w") as f:
    json.dump(enriched_math_lessons, f, indent=4)
print("Saved enriched math lessons to math_lessons_enriched.json")
