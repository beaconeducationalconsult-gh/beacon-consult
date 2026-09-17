import json
from collections import defaultdict

# Load Ghanaian Language B1 curriculum DB
with open('ghanaian_language_curriculum_db_clean.json') as f:
    cur_db = json.load(f)

print(f"Loaded {len(cur_db)} Ghanaian Language B1 indicators")

# Group indicators by strand
strand_map = defaultdict(list)
for code, meta in cur_db.items():
    # code like B1.1.1.1.1 -> strand B1.1
    parts = code.split('.')
    strand_key = f"{parts[0]}.{parts[1]}"
    # map strand number
    # B1.1 Oral, B1.2 Reading, B1.4 Writing, B1.5 Grammar, B1.6 Extensive
    strand_map[strand_key].append(code)

# Sort each strand list
for k in strand_map:
    strand_map[k] = sorted(strand_map[k])

print("Strand breakdown:")
for sk in sorted(strand_map):
    print(sk, len(strand_map[sk]), strand_map[sk][:3])

# Map strand codes to weekday and strand_num
# Monday B1.1 Oral
# Tuesday B1.2 Reading
# Wednesday B1.4 Writing
# Thursday B1.5 Grammar
# Friday B1.6 Extensive
week_plan = [
    ("Monday", "B1.1", 1),
    ("Tuesday", "B1.2", 2),
    ("Wednesday", "B1.3", 3),
    ("Thursday", "B1.5", 4),
    ("Friday", "B1.6", 5),
]

# Build 36 weeks x 5 days = 180 lessons
# Cycle through indicators in each strand
from itertools import cycle, islice

strand_iters = {}
strand_pos = {}
for strand_code, codes in strand_map.items():
    # repeat list to cover 36 lessons
    # We'll just cycle
    strand_iters[strand_code] = cycle(codes)
    strand_pos[strand_code] = 0

lessons_raw = []
lesson_num = 1
for term in [1,2,3]:
    for week in range(1,13):
        for day_name, strand_code, strand_num in week_plan:
            # get next indicator
            ind_code = next(strand_iters[strand_code])
            # track how many times we've used this indicator
            strand_pos[strand_code] = strand_pos.get(strand_code, 0) + 0  # not needed
            lessons_raw.append({
                "lesson_num": lesson_num,
                "term": term,
                "week": week,
                "day": day_name,
                "strand_num": strand_num,
                "strand_code": strand_code,
                "ind_code": ind_code,
                "is_revision": False  # will compute later if needed
            })
            lesson_num += 1

print(f"Generated {len(lessons_raw)} raw lessons")

# Now enrich
# Count total occurrences per indicator to compute session numbers
from collections import Counter
ind_counts = Counter([l["ind_code"] for l in lessons_raw])
print("Indicator usage sample:", list(ind_counts.items())[:5])

ind_current = Counter()

def get_ghanaian_activities(ind_code, meta, session_num, total_sessions, day_name, is_revision=False):
    strand = meta.get("strand","")
    sub_strand = meta.get("sub_strand","")
    ind_desc = meta.get("ind_desc","")
    keywords = meta.get("keywords","ghanaian-language, reading, writing")
    # session title
    if is_revision:
        session_title = f"Session {session_num} of {total_sessions} — Revision & Practice"
        perf_indicator = f"By the end of the lesson, learners will be able to review and consolidate: {ind_desc.lower()}"
    else:
        if session_num == 1:
            session_title = f"Session {session_num} of {total_sessions} — Introduction"
            perf_indicator = f"By the end of the lesson, learners will be able to demonstrate basic understanding of: {ind_desc.lower()}"
        elif session_num == total_sessions:
            session_title = f"Session {session_num} of {total_sessions} — Consolidation & Assessment"
            perf_indicator = f"By the end of the lesson, learners will be able to apply independently: {ind_desc.lower()}"
        else:
            session_title = f"Session {session_num} of {total_sessions} — Practice & Deepening"
            perf_indicator = f"By the end of the lesson, learners will be able to practice: {ind_desc.lower()}"
    # Starter by strand type
    if "Oral" in strand or day_name=="Monday":
        starter = [
            "Greet learners warmly in Ghanaian Language (Mother Tongue). Sing 'Good Morning' with actions and smiles.",
            "Lead a 2-minute phonological warm-up: clap syllables, recite a familiar rhyme or tongue twister.",
            f"NEW TODAY: State lesson focus: 'Today we will practice {sub_strand.lower()}.'",
            f"Write key vocabulary on the board: {keywords.split(',')[0].strip()}. Pupils echo chorally, then individually."
        ]
        main = [
            "ACTIVITY 1 (Modelling – 5 min): Teacher models clear pronunciation, gestures, and turn-taking. Uses big pictures / realia to set context.",
            "ACTIVITY 2 (Guided Practice – 5 min): Pupils repeat in chorus, then pairs. Teacher circulates, correcting pronunciation gently, encouraging Mother Tongue bridging where needed.",
            "ACTIVITY 3 (Pair / Group Talk – 7 min): In mixed-ability pairs, pupils practise the target language function (greeting, describing, storytelling, listening and responding) using picture prompts / sentence frames.",
            "ACTIVITY 4 (Share & Feedback – 3 min): 2–3 pairs perform to class. Teacher praises, recasts errors positively, reinforces key vocabulary."
        ]
        plenary = [
            "Whole class recites the key expression / rhyme together with actions.",
            "Ask: 'What new words did we learn today?' – 2–3 pupils respond.",
            "Homework: 'Practise telling your family what we learned, in Ghanaian Language (Mother Tongue).'",
            "Preview tomorrow: Reading adventure!"
        ]
    elif "Reading" in strand or day_name=="Tuesday":
        starter = [
            "Greet learners. Quick phonics / alphabet drill: show letter cards, pupils say sound and an example word.",
            "Sing the 'Alphabet Song' or a Jolly Phonics action song.",
            f"NEW TODAY: 'We are reading about {sub_strand.lower()}.'",
            "Do a picture walk: show the big book cover / chart, pupils predict what will happen."
        ]
        main = [
            "ACTIVITY 1 (Modelling – 5 min): Teacher reads aloud with expression, tracking print left-to-right, pointing to words. Models blending / sight-word recognition as appropriate.",
            "ACTIVITY 2 (Shared Reading – 5 min): Echo reading – teacher reads a sentence, pupils echo. Choral reading of key repeated phrases.",
            "ACTIVITY 3 (Guided / Pair Reading – 7 min): Pupils read in pairs / small groups using decodable readers / big books / sentence strips. Teacher listens in, supports struggling readers.",
            "ACTIVITY 4 (Comprehension Check – 3 min): Ask 3 literal questions (who/what/where). Pupils answer orally, then thumbs-up self-assess."
        ]
        plenary = [
            "Pupils retell the main idea in 1–2 sentences – think-pair-share.",
            "Review 3 new sight words / vocabulary – flashcard rapid drill.",
            "Homework: 'Read the mini-book / take-home sheet to an older sibling / parent.'",
            "Preview: tomorrow we will write!"
        ]
    elif "Writing" in strand or day_name=="Wednesday":
        starter = [
            "Greet learners. Finger-gym warm-up: air-write letters, stretch fingers, trace in sand trays.",
            "Quick review: show 3 printed words, pupils read chorally.",
            f"NEW TODAY: 'Today we will write – {sub_strand.lower()}.'",
            "Model correct pencil grip and sitting posture – 30 seconds practice."
        ]
        main = [
            "ACTIVITY 1 (Modelling – 5 min): Teacher thinks aloud and models writing on board / chart – letter formation / copying a sentence / composing 2–3 simple sentences, as per indicator.",
            "ACTIVITY 2 (Guided Writing – 5 min): Pupils trace / copy / complete cloze sentences in their exercise books. Teacher circulates, supporting grip, spacing, left-to-right direction.",
            "ACTIVITY 3 (Independent / Pair Writing – 7 min): Pupils write independently – draw and label, copy from board, or write 2 own sentences using word bank. Early finishers illustrate.",
            "ACTIVITY 4 (Share – 3 min): 2–3 pupils show work on visualiser / hold up books. Peer applause. Teacher highlights good letter formation / capitals / full stops."
        ]
        plenary = [
            "Pupils read aloud what they wrote – partner first, then 2 volunteers to class.",
            "Quick editing chant: 'Capital – finger space – full stop!'",
            "Homework: 'Copy 5 key words neatly at home, draw a picture.'",
            "Preview: Grammar fun tomorrow!"
        ]
    elif "Grammar" in strand or "Writing Conventions" in strand or day_name=="Thursday":
        starter = [
            "Greet learners. Quick grammar action game: 'Stand up if you hear a naming word / doing word.'",
            "Review yesterday's writing – spot 1 capital and 1 full stop together.",
            f"NEW TODAY: 'We are learning grammar – {sub_strand.lower()}.'",
            f"Introduce target structure / convention: '{keywords.split(',')[0].strip()}'. Model orally with gestures."
        ]
        main = [
            "ACTIVITY 1 (Modelling – 5 min): Teacher explicitly models the grammar / convention point using sentences on board, colour-coding (e.g., nouns in blue, verbs in red, capital letters circled).",
            "ACTIVITY 2 (Guided Practice – 5 min): Whole-class oral substitution drills / sentence building with word cards / pocket chart. Pairs practise.",
            "ACTIVITY 3 (Written Application – 7 min): Pupils complete 4–6 short exercises in books – underline, circle, fill blanks, match, rewrite with correct punctuation/capitalisation.",
            "ACTIVITY 4 (Peer Check – 3 min): Swap books with partner, tick correct answers using green crayon. Teacher reviews 2 items whole-class."
        ]
        plenary = [
            "Choral recitation of grammar rule / song – e.g., 'A noun names a person, place, animal or thing! Clap clap!'",
            "Exit ticket orally: each row answers 1 quick question as they line up.",
            "Homework: 'Find 3 examples at home – write in homework book.'",
            "Preview: Friday library / extensive reading celebration!"
        ]
    else:  # Extensive Reading / Friday
        starter = [
            "Greet learners joyfully – 'It's Reading Friday!' Play library stamp – pupils pretend to check out a book.",
            "2-minute book talk: Teacher shows 3 colour books, pupils vote which to read by raising hands.",
            "Review library rules chant: 'Quiet voices – turn pages gently – respect books!'",
            f"NEW TODAY: '{sub_strand}' – free choice extensive reading."
        ]
        main = [
            "ACTIVITY 1 (Read Aloud – 5 min): Teacher reads a big picture book / African story with big expression, pausing for predictions.",
            "ACTIVITY 2 (Paired / Independent Reading – 10 min): Pupils choose level-appropriate readers from classroom library box. Read silently / whisper-read / buddy-read. Teacher conferences with 3–4 target readers.",
            "ACTIVITY 3 (Response – 5 min): Pupils draw their favourite character / scene and write 1–2 sentences: 'I liked ___ because ___.' OR complete a simple reading log sticker.",
        ]
        plenary = [
            "Reading circle share: 3 pupils show their drawing and say 1 sentence about their book.",
            "Celebrate: class reading cheer – 'We are readers! Yes we are!'",
            "Homework: 'Read 10 minutes at home. Ask a family member to sign your reading log.'",
            "Preview next week: new Oral Language theme!"
        ]
        # adjust main to 4 activities for consistency
        main.append("ACTIVITY 4 (Library routine – 3 min): Pupils return books neatly, choose next week's take-home reader, teacher stamps reading logs.")

    return {
        "session_title": session_title,
        "perf_indicator": perf_indicator,
        "starter": starter,
        "main": main,
        "plenary": plenary
    }

enriched=[]
for l in lessons_raw:
    code=l["ind_code"]
    meta=cur_db.get(code)
    if not meta:
        # fallback – try find similar?
        meta=list(cur_db.values())[0]
    ind_current[code]+=1
    session_num=ind_current[code]
    total_sessions=ind_counts[code]
    act=get_ghanaian_activities(code, meta, session_num, total_sessions, l["day"], l.get("is_revision",False))
    # RPK mapping
    strand_name=meta.get("strand","Ghanaian Language")
    rpk_map={
        "Oral Language": "Learners have sung songs, recited rhymes, told stories in Mother Tongue and KG English, and can greet and respond to simple instructions.",
        "Reading": "Learners can recognise most upper- and lower-case letters, some common sight words, and have listened to stories read aloud in KG.",
        "Writing": "Learners can hold a pencil, trace patterns, copy letters, and write their own names from KG.",
        "Using Writing Conventions / Grammar Usage": "Learners use simple sentences orally in everyday interaction and are familiar with basic classroom Ghanaian Language.",
        "Extensive Reading": "Learners enjoy picture books, story time, and looking at print in their environment."
    }
    # find best rpk key
    rpk = "Learners have prior exposure to oral English, print awareness, and Mother Tongue literacy from KG and home."
    for k,v in rpk_map.items():
        if k.lower() in strand_name.lower():
            rpk=v
            break
    enriched.append({
        "lesson_num": l["lesson_num"],
        "term": l["term"],
        "week": l["week"],
        "day": l["day"],
        "strand_num": l["strand_num"],
        "strand_name": meta.get("strand", strand_name),
        "sub_strand": meta.get("sub_strand",""),
        "cs_code": meta.get("cs_code",""),
        "cs_desc": meta.get("cs_desc",""),
        "ind_code": code,
        "ind_desc": meta.get("ind_desc",""),
        "is_revision": l.get("is_revision",False),
        "session_title": act["session_title"],
        "perf_indicator": act["perf_indicator"],
        "competencies": meta.get("competencies","Communication and Collaboration; Creativity and Innovation; Critical Thinking and Problem Solving; Cultural Identity and Global Citizenship; Personal Development and Leadership"),
        "resources": meta.get("resources","Big book; word cards; flashcards; pictures; Manila charts; markers; exercise books; pencils"),
        "keywords": meta.get("keywords","ghanaian-language, oral, reading, writing"),
        "rpk": rpk,
        "starter": act["starter"],
        "main": act["main"],
        "plenary": act["plenary"],
        "assessment": meta.get("assessment","Observation; oral questions; written class exercise")
    })

print(f"Enriched {len(enriched)} Ghanaian Language B1 lessons")
with open("ghanaian_language_lessons_enriched.json","w",encoding="utf-8") as out:
    json.dump(enriched,out,indent=2,ensure_ascii=False)
print("Saved to ghanaian_language_lessons_enriched.json")
