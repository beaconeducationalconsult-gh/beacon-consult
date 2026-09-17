# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import re
import json
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# Load the clean curriculum database and parsed raw lessons
with open("science_curriculum_db_clean.json") as f:
    cur_db = json.load(f)

with open("science_parsed_lessons_raw.json") as f:
    raw_lessons = json.load(f)

print(f"Loaded {len(cur_db)} unique indicators and {len(raw_lessons)} raw lessons.")

strand_names = {
    1: "DIVERSITY OF MATTER",
    2: "CYCLES",
    3: "SYSTEMS",
    4: "FORCES AND ENERGY",
    5: "HUMANS AND THE ENVIRONMENT"
}

# Keep track of counts of each indicator to determine accurate session numbers
ind_counts = {}
for l in raw_lessons:
    code = l["ind_code"]
    ind_counts[code] = ind_counts.get(code, 0) + 1

# A dict to track current occurrence of each indicator as we iterate
ind_current_counts = {}

# Detailed activities generator for each of the 31 unique indicators
def get_lesson_activities(ind_code, is_revision, session_num, total_sessions):
    meta = cur_db.get(ind_code, {
        "strand": "1. DIVERSITY OF MATTER",
        "sub_strand": "1. Living and Non-Living Things",
        "ind_desc": "Observe and describe different kinds of things in the environment.",
        "competencies": "Critical Thinking & Problem Solving; Communication & Collaboration",
        "resources": "Plant specimens; pictures; schoolyard walk",
        "keywords": "observe, describe, things, environment",
        "assessment": "Observation worksheet; teacher observation rubric"
    })
    
    ind_desc = meta["ind_desc"]
    resources = meta["resources"]
    keywords = meta["keywords"]
    strand = meta["strand"]
    sub_strand = meta["sub_strand"]
    
    # Session title and performance indicator
    if is_revision:
        session_title = f"Session {session_num} of {total_sessions} — Revision & Consolidation"
        perf_indicator = f"By the end of the lesson, learners should be able to review, practice, and consolidate their understanding of: {ind_desc.lower()}"
    else:
        if session_num == 1:
            session_title = f"Session 1 of {total_sessions} — Introduction"
            perf_indicator = f"By the end of the lesson, learners should be able to identify and state the basic concepts of: {ind_desc.lower()}"
        elif session_num == total_sessions:
            session_title = f"Session {session_num} of {total_sessions} — Consolidation & Assessment"
            perf_indicator = f"By the end of the lesson, learners should be able to demonstrate mastery of: {ind_desc.lower()}"
        else:
            session_title = f"Session {session_num} of {total_sessions} — Practice & Deepening"
            perf_indicator = f"By the end of the lesson, learners should be able to explain and practice: {ind_desc.lower()}"

    # Starters
    if "DIVERSITY" in strand:
        if is_revision:
            starter = [
                "Greet learners warmly. Begin with a local call-and-response song about the natural world around us.",
                "Play a 3-minute game of 'I Spy' where pupils spot a living or non-living thing in the classroom.",
                "Review key words from previous sessions: " + ", ".join(keywords.split(",")[:3]) + ".",
                "NEW TODAY: State the lesson focus: 'Today we are going to review and show what we know about " + sub_strand.lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners warmly and sing a happy Mother-Tongue science rhyme.",
                "Show a real-world specimen (like a green plant, or a clean stone) and ask: 'What do you see? Touch it and describe it.'",
                "NEW TODAY: State the lesson focus: 'Today we will begin exploring " + sub_strand.lower() + ".'",
                "Write the key word '" + keywords.split(",")[0].strip() + "' on the board and read it together."
            ]
    elif "CYCLES" in strand:
        if is_revision:
            starter = [
                "Greet learners. Recite a fun weather poem together: 'Sunny, rainy, cloudy, windy, we love all weather!' with physical gestures.",
                "Ask: 'What changes did you see in the sky on your way to school today?'",
                "Review yesterday's lesson: the recurring natural events in our immediate environment.",
                "NEW TODAY: State today's focus: 'We will practice and show what we have learned about " + sub_strand.lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners. Stand in a circle and mimic the sun rising (stretch up high) and rain falling (wiggle fingers down).",
                "Ask a quick question: 'What is the main source of light when we walk outside in the morning?'",
                "NEW TODAY: State today's focus: 'We are starting our study of " + sub_strand.lower() + ".'",
                "Write today's key term: '" + keywords.split(",")[0].strip() + "' on the board and pronounce it together."
            ]
    elif "SYSTEMS" in strand:
        if is_revision:
            starter = [
                "Greet learners warmly. Sing 'Head, Shoulders, Knees and Toes' together with rapid physical actions.",
                "Play 'Simon Says' to identify and touch external body parts quickly.",
                "Recall why we need our body parts to work interdependently to play and learn.",
                "NEW TODAY: State today's focus: 'We will practice identifying and describing our " + sub_strand.lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners warmly. Sing the 'Five Senses Song' or 'This is My Body' with appropriate active movements.",
                "Have pupils look at their hands and wiggle their fingers. Ask: 'What do our hands help us do?'",
                "NEW TODAY: State today's focus: 'Today we will learn about " + sub_strand.lower() + ".'",
                "Write the keyword '" + keywords.split(",")[0].strip() + "' on the board and pronounce it together."
            ]
    elif "FORCES" in strand:
        if is_revision:
            starter = [
                "Greet learners warmly. Recite the active rhyme 'Push and Pull' or do a simple action song.",
                "Have pupils stand up, push their chairs in, and then pull them out. Ask: 'What forces did we just use?'",
                "Recall how energy and forces make objects move or make work easier.",
                "NEW TODAY: State today's focus: 'We will review and consolidate our understanding of " + sub_strand.lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners. Rub hands together quickly until they feel warm. Ask: 'What do you feel? Where did the warmth come from?'",
                "Demonstrate pushing a toy block or ball. Ask: 'Why did it move?'",
                "NEW TODAY: Introduce today's lesson: 'Today we will begin learning about " + sub_strand.lower() + ".'",
                "Write the keyword '" + keywords.split(",")[0].strip() + "' on the board and read it aloud."
            ]
    else:  # HUMANS AND THE ENVIRONMENT
        if is_revision:
            starter = [
                "Greet learners. Sing an active hygiene song like 'This is the way we wash our hands/brush our teeth.'",
                "Do a quick 'clean fingers check' or 'teeth check' in pairs to encourage good hygiene.",
                "Recall why keeping clean and disposing of waste is important to stay healthy.",
                "NEW TODAY: State today's focus: 'Today we are going to practice and show how we maintain " + sub_strand.lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners warmly. Show a hygiene tool (e.g., a real soap bar or a clean toothbrush) and ask: 'Who used this today?'",
                "Sing a joyful song about personal cleanliness and health with actions.",
                "NEW TODAY: Introduce the lesson: 'Today we will learn about " + sub_strand.lower() + ".'",
                "Write the keyword '" + keywords.split(",")[0].strip() + "' on the board and pronounce it together."
            ]

    # Main Activities
    if "DIVERSITY" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Interactive Review - 5 min): Teacher displays living and non-living objects (or cards). Pupils call out 'Living!' or 'Non-living!' in unison and explain why.",
                "ACTIVITY 2 (Pair sorting - 5 min): In pairs, pupils sort physical specimens (leaves, twigs, plastic pens, stones) on their desks. Teacher checks and guides.",
                "ACTIVITY 3 (Group Challenge - 7 min): Groups are given cards of natural and man-made materials. They play a race game to sort them into correct trays.",
                "ACTIVITY 4 (Consolidation - 3 min): Teacher clarifies any misconceptions, reviews the key term '" + keywords.split(",")[0].strip() + "', and praises excellent team effort."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher leads a safe walk into the schoolyard or school garden. Teacher points to a living plant and a non-living stone, describing how they look and feel.",
                "ACTIVITY 2 (Guided Discovery - 5 min): Pupils work in small groups with hand lenses to observe leaves, tree barks, soil, or ants. They describe their observations to their peers.",
                "ACTIVITY 3 (Drawing & Sorting - 7 min): Pupils return to the classroom and draw 2 living things and 2 non-living things in their notebooks, coloring them.",
                "ACTIVITY 4 (Discussion & Sharing - 3 min): Selected pupils show their drawings to the class and describe one feature. Teacher reinforces concepts using mother tongue where necessary."
            ]
    elif "CYCLES" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Weather/Day-Night Recap - 5 min): Teacher displays weather symbols on the board. Pupils match them to words (sunny, rainy, cloudy, windy) and discuss how they change.",
                "ACTIVITY 2 (Interactive Demonstration - 5 min): Teacher uses a globe/ball and flashlight to demonstrate the repeating day and night cycle. Pupils take turns holding the light.",
                "ACTIVITY 3 (Worksheet / Matching - 7 min): Pupils complete a matching worksheet, matching day/night to activities (e.g., sleeping at night, playing during the day) or matching weather to clothing.",
                "ACTIVITY 4 (Review - 3 min): Teacher corrects common errors on the worksheets and summarizes the natural cycle of " + sub_strand.lower() + "."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher demonstrates. E.g., for day and night, teacher explains that the sun provides light. E.g., for rain, teacher uses a sponge to show how clouds hold water.",
                "ACTIVITY 2 (Guided Outdoor Observation - 5 min): Pupils go outside to observe the clouds, wind direction, or feel the sun's warmth. They record their findings using simple weather symbols.",
                "ACTIVITY 3 (Group Creative Task - 7 min): In small groups, pupils construct simple paper fans or draw weather symbols on cardboard, coloring them.",
                "ACTIVITY 4 (Sharing & Discussion - 3 min): Pupils hold up their drawings. Teacher asks: 'What do we do on a rainy day? What about a sunny day?' Pupils share their thoughts."
            ]
    elif "SYSTEMS" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Body Parts Game - 5 min): Play an accelerated game of 'Simon Says' or point to body parts to test speed and accuracy. Pupils clap for correct answers.",
                "ACTIVITY 2 (Senses Exploration - 5 min): In small groups, pupils explore different sense objects (rough stone, smelling flower, hearing bell, tasting safely). They identify which body part is responsible.",
                "ACTIVITY 3 (Human Body Chart - 7 min): In small groups, pupils paste labels (eyes, ears, hand, chest, shoulders, leg) onto a large blank outline of a human body.",
                "ACTIVITY 4 (Feedback & Review - 3 min): Each group displays their body chart. Teacher provides positive feedback and reinforces vocabulary: " + ", ".join(keywords.split(",")[:3]) + "."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher points to their own external body parts (eyes, ears, nose, hands, chest) and states their appropriate names, describing their functions.",
                "ACTIVITY 2 (Guided Peer Identification - 5 min): Pupils sit in pairs, look at each other, and identify body parts. They chant together: 'These are my eyes, these are my ears.'",
                "ACTIVITY 3 (Senses Activity - 7 min): Teacher sets up simple stations for sight, hearing, touch, and smell. Pupils rotate in pairs to guess objects, identifying the body part used.",
                "ACTIVITY 4 (Active Game - 3 min): Play 'Simon Says touch your knees, shoulders, toes, chest.' Teacher monitors to ensure all pupils can correctly identify their body parts."
            ]
    elif "FORCES" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Forces/Energy Recap - 5 min): Teacher displays a toy machine, ramp, or electronic device. Pupils call out what force or energy it uses or how it helps us.",
                "ACTIVITY 2 (Hands-on Ramps/Cars - 5 min): In small groups, pupils roll toy cars on smooth and rough surfaces to observe movement. They describe which surface has less resistance.",
                "ACTIVITY 3 (Practical Investigation - 7 min): Pupils use simple materials (balloons, cardboard, rubber bands) to explore pushes, pulls, and energy. They draw their findings in their notebooks.",
                "ACTIVITY 4 (Review & Reflection - 3 min): Teacher observes groups, asks probing questions about simple machines or forces, and corrects any misconceptions."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher demonstrates a concept. E.g., for forces, teacher pushes a chair and pulls a drawer. E.g., for simple machines, shows how a ramp (inclined plane) makes work easier.",
                "ACTIVITY 2 (Guided Exploration - 5 min): Pupils test pushing and pulling various classroom objects (books, bottles, blocks, pencil cases) and state whether it was a push or a pull.",
                "ACTIVITY 3 (Group Active Experiment - 7 min): In small groups, pupils explore simple sources of energy (feeling warm sunlight, safely touching warm objects, observing a glowing torch/circuit).",
                "ACTIVITY 4 (Sharing - 3 min): Pupils explain their findings: 'A push moves things away, a pull brings things closer.' Teacher writes these summaries on the board."
            ]
    else:  # HUMANS AND THE ENVIRONMENT
        if is_revision:
            main = [
                "ACTIVITY 1 (Cleanliness Review - 5 min): Teacher shows pictures of dirty hands, healthy skin, clean teeth. Pupils discuss why personal hygiene keeps us healthy and free from scabies or decay.",
                "ACTIVITY 2 (Roleplay & Practice - 5 min): In small groups, pupils practice the 6-step handwashing technique using a real bar of soap and clean basins (or dry run) or roleplay brushing teeth.",
                "ACTIVITY 3 (Surroundings Cleanup - 7 min): Pupils play a cleanup game, picking up safe trash (paper, plastic) in the classroom/schoolyard and sorting it into correct organic/inorganic bins.",
                "ACTIVITY 4 (Reflection - 3 min): Teacher highlights the importance of clean surroundings, clean air, and clean water. Commends pupils for their cleanup work."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher demonstrates. E.g., for handwashing, models the 6 steps with real soap and running water from a tippy-tap. E.g., for teeth, models correct brushing steps on a model.",
                "ACTIVITY 2 (Guided Active Practice - 5 min): Pupils take turns at the washing station to practice the 6 standard handwashing steps, or practice brushing techniques in pairs.",
                "ACTIVITY 3 (Creative Group Poster - 7 min): In small groups, pupils color a hygiene poster representing bathing, handwashing, or waste disposal, and label key items using crayons.",
                "ACTIVITY 4 (Hygiene Demonstration - 3 min): A pupil is selected to demonstrate correct handwashing or teeth-cleaning steps to the class. Teacher prompts and class praises."
            ]

    # Plenaries
    if is_revision:
        plenary = [
            "Whole class recites a consolidated science rhyme or sings today's theme song with active physical movements.",
            "Ask: 'Who can tell me one important rule we revised today?' (Call on 2-3 pupils, especially those needing support).",
            "Homework: 'Go home and show your family what we revised today. Help keep your home clean or practice your science words.'",
            "Preview tomorrow's exciting lesson on the next strand."
        ]
    else:
        plenary = [
            "Whole class sings today's theme song with active physical movements.",
            "Ask: 'What did we discover today?' (Have 2-3 pupils share their findings).",
            "Homework: 'Tell your parents or older sibling what you observed today. Show them your drawing/poster.'",
            "Preview tomorrow's lesson on " + (strand_names[2] if "DIVERSITY" in strand else strand_names[1]) + "."
        ]

    return {
        "session_title": session_title,
        "perf_indicator": perf_indicator,
        "starter": starter,
        "main": main,
        "plenary": plenary
    }

# Build the final enriched lessons list
enriched_lessons = []
for idx, l in enumerate(raw_lessons):
    code = l["ind_code"]
    is_rev = l["is_revision"]
    
    # Get current occurrence index
    ind_current_counts[code] = ind_current_counts.get(code, 0) + 1
    session_num = ind_current_counts[code]
    total_sessions = ind_counts[code]
    
    # Get base metadata from cur_db
    meta = cur_db.get(code, {
        "strand": "1. DIVERSITY OF MATTER",
        "sub_strand": "1. Living and Non-Living Things",
        "cs_code": "B1.1.1.1",
        "cs_desc": "Show understanding of physical features and life processes of living things and use this understanding to classify them",
        "ind_desc": "Observe and describe different kinds of things in the environment.",
        "competencies": "Critical Thinking & Problem Solving; Communication & Collaboration",
        "resources": "Plant specimens; pictures; schoolyard walk",
        "keywords": "observe, describe, things, environment",
        "assessment": "Observation worksheet; teacher observation rubric"
    })
    
    # Generate detailed starter, main, plenary
    act = get_lesson_activities(code, is_rev, session_num, total_sessions)
    
    # Relevant Previous Knowledge (RPK)
    rpk_map = {
        "1. DIVERSITY OF MATTER": "Learners have seen various plants, animals, and non-living objects in their school and home environment.",
        "2. CYCLES": "Learners experience day and night daily, and see rain, sun, wind, and clouds in their daily lives.",
        "3. SYSTEMS": "Learners are aware of their own body, hands, eyes, nose, and mouth, and use them daily.",
        "4. FORCES AND ENERGY": "Learners have played with moving toys, felt heat, and seen lights and electrical appliances at home.",
        "5. HUMANS AND THE ENVIRONMENT": "Learners have engaged in personal hygiene practices like bathing, handwashing, and teeth-brushing at home."
    }
    rpk = rpk_map.get(meta["strand"], "Learners have basic everyday experiences related to this science topic.")
    
    enriched_lessons.append({
        "lesson_num": l["lesson_num"],
        "term": l["term"],
        "week": l["week"],
        "day": l["day"],
        "strand_num": l["strand_num"],
        "strand_name": meta["strand"],
        "sub_strand": meta["sub_strand"],
        "cs_code": meta["cs_code"],
        "cs_desc": meta["cs_desc"],
        "ind_code": code,
        "ind_desc": meta["ind_desc"],
        "is_revision": is_rev,
        "session_title": act["session_title"],
        "perf_indicator": act["perf_indicator"],
        "competencies": meta["competencies"],
        "resources": meta["resources"],
        "keywords": meta["keywords"],
        "rpk": rpk,
        "starter": act["starter"],
        "main": act["main"],
        "plenary": act["plenary"],
        "assessment": meta["assessment"]
    })

print(f"Enriched {len(enriched_lessons)} lessons successfully.")

# Save enriched lessons to JSON
with open("science_lessons_enriched.json", "w") as f:
    json.dump(enriched_lessons, f, indent=4)
print("Saved enriched lessons to science_lessons_enriched.json")
