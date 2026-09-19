# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2]))
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

# Let's count occurrences of each indicator to assign accurate Session numbers
ind_counts = {}
for l in raw_lessons:
    code = l["ind_code"]
    ind_counts[code] = ind_counts.get(code, 0) + 1

# Let's write a helper function to generate detailed lesson plan activities
def get_lesson_activities(ind_code, is_revision, session_num, total_sessions, day_of_week):
    # Retrieve base metadata
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
    
    # We will dynamically generate age-appropriate, hands-on, playful primary activities!
    if is_revision:
        session_title = f"Session {session_num} of {total_sessions} — Revision & Practice"
        perf_indicator = f"By the end of the lesson, learners should be able to review, practice and consolidate their understanding of: {ind_desc.lower()}"
    else:
        if session_num == 1:
            session_title = f"Session 1 of {total_sessions} — Introduction"
            perf_indicator = f"By the end of the lesson, learners should be able to demonstrate an introductory understanding of: {ind_desc.lower()}"
        elif session_num == total_sessions:
            session_title = f"Session {session_num} of {total_sessions} — Consolidation & Assessment"
            perf_indicator = f"By the end of the lesson, learners should be able to apply and demonstrate mastery of: {ind_desc.lower()}"
        else:
            session_title = f"Session {session_num} of {total_sessions} — Deepening & Group Practice"
            perf_indicator = f"By the end of the lesson, learners should be able to practice and describe: {ind_desc.lower()}"

    # Generate Starter based on Strand
    strand = meta["strand"]
    if "DIVERSITY" in strand:
        if is_revision:
            starter = [
                "Greet learners warmly and sing 'Good Morning' or a local Mother-Tongue science song.",
                "Play a quick 2-minute guessing game: 'I am thinking of a living thing that flies...' to review previous lessons.",
                "Review key words from yesterday: " + ", ".join(keywords.split(",")[:3]) + ".",
                "NEW TODAY: State the lesson focus: 'Today we will practice what we know about " + meta["sub_strand"].lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners warmly. Begin with a local call-and-response song about nature and things around us.",
                "Hold up a real object (e.g., a green leaf or a clean stone) and ask: 'What do you see? Tell your partner.'",
                "NEW TODAY: State the lesson focus: 'Today we are going to explore " + meta["sub_strand"].lower() + ".'",
                "Write the word '" + keywords.split(",")[0].strip() + "' on the board and pronounce it together."
            ]
    elif "CYCLES" in strand:
        if is_revision:
            starter = [
                "Greet learners and sing a lively weather song like 'Rain, Rain, Go Away' or 'The Sun is Shining.'",
                "Ask pupils to look out of the window and describe today's weather in 2 words.",
                "Review yesterday's key concept: how day/night or weather changes occur recurrently.",
                "NEW TODAY: State the focus: 'Today we will revise and show what we have learned about " + meta["sub_strand"].lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners. Stand in a circle and do a quick stretch mimicking the rising sun or falling rain.",
                "Ask a quick question: 'What did you see in the sky when you woke up this morning?'",
                "NEW TODAY: State today's focus: 'We are learning about the natural cycle of " + meta["sub_strand"].lower() + ".'",
                "Introduce today's key term: '" + keywords.split(",")[0].strip() + "' and have pupils echo it."
            ]
    elif "SYSTEMS" in strand:
        if is_revision:
            starter = [
                "Greet learners. Sing 'Head, Shoulders, Knees and Toes' with rapid actions to warm up.",
                "Play 'Simon Says' touching different body parts or mimicking sense organs (eyes, nose, ears).",
                "Quickly review why our body parts work together to help us eat, run and see.",
                "NEW TODAY: State the focus: 'Today we are practicing identifying our " + meta["sub_strand"].lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners warmly. Sing the 'Five Senses Song' or 'This is My Body' with appropriate actions.",
                "Have pupils point to their nose, eyes and ears. Ask: 'What do they do?'",
                "NEW TODAY: Introduce today's lesson: 'Today we will learn about " + meta["sub_strand"].lower() + ".'",
                "Write the key words on the board: " + ", ".join(keywords.split(",")[:2]) + ". Read aloud together."
            ]
    elif "FORCES" in strand:
        if is_revision:
            starter = [
                "Greet learners. Recite the active rhyme 'Push and Pull' or do a simple action song.",
                "Have pupils stand up, push their chairs in, and then pull them out. Ask: 'What did we just do?'",
                "Quickly recall that force is a push or a pull that causes motion.",
                "NEW TODAY: State the focus: 'Today we are practicing and consolidating our learning on " + meta["sub_strand"].lower() + ".'"
            ]
        else:
            starter = [
                "Greet learners warmly. Rub hands together quickly until they feel warm. Ask: 'What do you feel?'",
                "Demonstrate pushing a toy car across the table. Ask: 'Why did it move?'",
                "NEW TODAY: Introduce the focus: 'Today we are starting our study of " + meta["sub_strand"].lower() + ".'",
                "Introduce today's keywords: '" + keywords.split(",")[0].strip() + "' and describe its meaning."
            ]
    else:  # HUMANS AND THE ENVIRONMENT
        if is_revision:
            starter = [
                "Greet learners warmly. Sing a hygiene action song like 'This is the way we wash our hands/brush our teeth.'",
                "Do a quick 'clean fingers check' or 'teeth check' in pairs to encourage good hygiene practices.",
                "Briefly recall why keeping clean is important to fight off germs and diseases.",
                "NEW TODAY: State the focus: 'We are practicing and demonstrating how we keep our body and environment clean.'"
            ]
        else:
            starter = [
                "Greet learners warmly. Show a hygiene tool (e.g., a real soap bar or a clean toothbrush) and ask: 'Who used this today?'",
                "Sing a joyful song about bathing or washing hands with actions.",
                "NEW TODAY: Introduce the lesson: 'Today we will learn about " + meta["sub_strand"].lower() + ".'",
                "Write the keyword '" + keywords.split(",")[0].strip() + "' on the board and pronounce it together."
            ]

    # Generate Main Activities based on Strand and Session
    if "DIVERSITY" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Interactive Recap - 5 min): Teacher holds up living and non-living cards. Pupils call out 'Living!' or 'Non-living!' in unison and state why.",
                "ACTIVITY 2 (Pair Game - 5 min): Pupils work in pairs. One names a local material or object, the other classifies it as natural or man-made. They take turns.",
                "ACTIVITY 3 (Practical Sorting - 7 min): Provide small trays with stones, leaves, twigs, and paper scraps. Pupils sort them into 'Natural' and 'Man-made' or 'Living' and 'Non-living' bins.",
                "ACTIVITY 4 (Review & Consolidation - 3 min): Teacher reviews sorted trays, correcting misconceptions, and praising cooperative group work."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher leads pupils to look out of the window or walks them safely into the schoolyard. Teacher models observing: 'I see a green plant. It is alive because it grows.'",
                "ACTIVITY 2 (Guided Exploration - 5 min): Pupils use hand lenses (or close observation) to examine trees, soil, insects, or classroom objects. Teacher guides their vocabulary (roots, stem, leaves, smooth, rough).",
                "ACTIVITY 3 (Drawing & Sorting - 7 min): In small groups, pupils draw 2 living things and 2 non-living things they observed. Teacher walks around, helping pupils label their drawings using keywords.",
                "ACTIVITY 4 (Sharing & Discussion - 3 min): Selected pupils display their drawings to the class and describe one feature. Teacher reinforces concepts in English and Mother Tongue."
            ]
    elif "CYCLES" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Weather/Day-Night Recap - 5 min): Teacher displays a large weather chart or day-night card. Pupils point to symbols and describe the current weather conditions or sky features.",
                "ACTIVITY 2 (Flashlight Demo - 5 min): Teacher invites 2 pupils to act as Earth and Sun. Using a flashlight, they demonstrate the day and night rotation. Class reviews why this occurs repeatedly.",
                "ACTIVITY 3 (Worksheet / Drawing - 7 min): Pupils complete a simple matching worksheet (e.g., matching sun to day, moon to night, or matching umbrella to rainy weather).",
                "ACTIVITY 4 (Peer Discussion - 3 min): Pupils swap drawings/worksheets with a partner, checking each other's work and talking about their favorite weather."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher demonstrates a concept. E.g., for Day/Night, shines a flashlight on a globe/ball in a dimmed room, showing that the sun provides light to only one half of the Earth.",
                "ACTIVITY 2 (Guided Discovery - 5 min): For plants/seeds/weather, teacher shows real plant growth charts or takes pupils to observe the sky. Pupils describe what they see (clouds, sun, dry/wet soil).",
                "ACTIVITY 3 (Group Work - 7 min): In small groups, pupils construct a paper windmill or draw weather symbols (sunny, rainy, cloudy, windy) on cardboards, coloring them with crayons.",
                "ACTIVITY 4 (Reflection - 3 min): Ask: 'What would happen if we had no sun?' or 'Why do we need rain?' Pupils discuss in small groups and share answers."
            ]
    elif "SYSTEMS" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Body Parts Challenge - 5 min): Teacher points to their elbow, chest, or toes. Pupils call out the correct name. Increase speed to make it a fun, playful game.",
                "ACTIVITY 2 (Sense Station Exploration - 5 min): In small groups, pupils rotate through senses stations: smelling flower/soap, feeling rough stone/smooth leaf, hearing a bell, seeing colored cards.",
                "ACTIVITY 3 (Drawing & Labelling - 7 min): Pupils draw an outline of a human body in pairs and paste pre-cut labels (eyes, ears, hand, leg, mouth) onto the correct parts.",
                "ACTIVITY 4 (Interactive Feedback - 3 min): Teacher calls on groups to show their body chart. Class applauds correct placements and corrects any mislabelled parts."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher points to external body parts (eyes, ears, hands, chest) and describes their function: 'These are my eyes. They help me see the beautiful world.'",
                "ACTIVITY 2 (Guided Identification - 5 min): Pupils look in small mirrors (or look at their partner) and name parts. They chant the names together: 'Eyes, Ears, Nose, Mouth, Hands, Legs!'",
                "ACTIVITY 3 (Pair Activity - 7 min): Pupils sit in pairs. One points to a body part, and the other must call out its appropriate name and state what we use it for (e.g., 'These are hands, we use them to write').",
                "ACTIVITY 4 (Active Game - 3 min): Play 'Simon Says' touch your chin, shoulders, knees, toes, or chest. Teacher monitors to see if all learners can correctly identify the parts."
            ]
    elif "FORCES" in strand:
        if is_revision:
            main = [
                "ACTIVITY 1 (Interactive Recap - 5 min): Teacher reviews the concepts of energy, forces or machines. Holds up a toy machine or ramp and asks: 'How does this make our work easier?'",
                "ACTIVITY 2 (Hands-on Friction / Movement - 5 min): In small groups, pupils roll toy cars down a smooth ramp and a rough ramp. They observe which car goes faster and discuss why.",
                "ACTIVITY 3 (Practical Challenge - 7 min): Give small groups simple materials (springs, rubber bands, cardboard). Pupils explore pushing and pulling to observe shape changes or movement.",
                "ACTIVITY 4 (SBA Observation - 3 min): Teacher observes groups, using the rubric to assess their teamwork, problem-solving skills, and understanding of the forces involved."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher demonstrates. E.g., for pushing/pulling, teacher pushes a heavy box and pulls a drawer. E.g., for simple machines, teacher shows how a ramp helps lift a heavy toy wheelbarrow.",
                "ACTIVITY 2 (Guided Experimentation - 5 min): Pupils test pushing and pulling various classroom objects (pencils, books, bottles, chairs). They describe whether it requires a 'push' or a 'pull' to move them.",
                "ACTIVITY 3 (Group Discovery - 7 min): In small groups, pupils explore different sources of energy or heat (e.g., safely touching warm objects, observing a glowing torch, feeling a simple battery-circuit light up).",
                "ACTIVITY 4 (Sharing & Discussion - 3 min): Selected pupils explain to the class: 'I pushed the toy car and it rolled fast' or 'Electricity makes the television light up.' Teacher validates."
            ]
    else:  # HUMANS AND THE ENVIRONMENT
        if is_revision:
            main = [
                "ACTIVITY 1 (Hygiene Review - 5 min): Teacher shows pictures of healthy skin, clean teeth, and dirty hands. Pupils discuss what happens when we neglect hygiene (germs, scabies, tooth decay).",
                "ACTIVITY 2 (Roleplay & Practice - 5 min): In pairs, pupils roleplay brushing their teeth (using a clean toothbrush without water/paste) or demonstrate washing hands with a real bar of soap and dry basins.",
                "ACTIVITY 3 (Interactive Sorting - 7 min): Class plays a waste sorting game. Teacher lays out paper scraps, plastic bottles, and organic peels. Pupils sort them into 'Clean Surroundings' bins.",
                "ACTIVITY 4 (Feedback & Reflection - 3 min): Teacher reviews sorted trash and highlights the importance of personal hygiene and clean surrounding air and water."
            ]
        else:
            main = [
                "ACTIVITY 1 (Modelling - 5 min): Teacher models. E.g., for bathing, teacher uses a hygiene poster or a doll to show correct steps. E.g., for handwashing, teacher models the 6-step handwashing technique with real soap and running water.",
                "ACTIVITY 2 (Guided Practice - 5 min): For handwashing, pupils take turns at the tippy-tap station practicing the 6 steps (wet, soap, rub palms, back of hands, fingers, rinse, air dry). For other topics, they practice in pairs.",
                "ACTIVITY 3 (Group Creative Task - 7 min): In small groups, pupils draw a poster representing 'Our Clean Classroom' or color a worksheet of a child brushing teeth/bathing. They label key items.",
                "ACTIVITY 4 (Hygiene Demonstration - 3 min): A pupil is selected to demonstrate the handwashing steps or teeth-cleaning steps to the class. Teacher prompts and class praises."
            ]

    # Generate Plenary based on Strand and Session
    if is_revision:
        plenary = [
            "Whole class recites a consolidated science rhyme or sings today's theme song one more time.",
            "Ask: 'Who can tell me one important rule we revised today?' (Call on 2-3 pupils, especially those needing support).",
            "Homework: 'Go home and show your family what we revised. Help keep your home clean or practice your science words.'",
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

# Let's test the generator for Lesson #1
test_act = get_lesson_activities("B1.1.1.1.1", False, 1, 5, "Monday")
print("\nGenerated Test Starter:")
for line in test_act["starter"]:
    print(" -", line)
