#!/usr/bin/env python3
"""Generate 180 full-year daily lesson plans for Basic 7 Core-4 subjects (CCP/JHS):
Mathematics, Science, English, Ghanaian Language. Uses verified B7 DBs (CCP).
Scheduling: English/Ghanaian have 6 strands -> alternating Wed/Fri slots;
Extensive-Reading sessions get a dedicated reading-period template.
Output: {subject}_b7_lessons_enriched.json
"""
import json
from collections import defaultdict, Counter
from itertools import cycle

DBDIR = 'data/curriculum'
DAYS5 = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

subjects = [
    {"key": "math", "sid": "mathematics", "name": "Mathematics",
     "plan": [("Monday", "B7.1"), ("Tuesday", "B7.2"), ("Wednesday", "B7.3"),
              ("Thursday", "B7.4"), ("Friday", "B7.1")]},
    {"key": "science", "sid": "science", "name": "Integrated Science",
     "plan": [("Monday", "B7.1"), ("Tuesday", "B7.2"), ("Wednesday", "B7.3"),
              ("Thursday", "B7.4"), ("Friday", "B7.5")]},  # 5 strands = 5 days
    {"key": "english", "sid": "english-language", "name": "English Language",
     "plan": [("Monday", "B7.1"), ("Tuesday", "B7.2"), ("Wednesday", "B7.3"),
              ("Thursday", "B7.4"), ("Friday", "B7.5")]},  # Friday = Literature reading period
    {"key": "ghanaian", "sid": "ghanaian-language", "name": "Ghanaian Language",
     "plan": [("Monday", "B7.1"), ("Tuesday", "B7.2"), ("Wednesday", ["B7.3", "B7.6"]),
              ("Thursday", "B7.4"), ("Friday", "B7.5")]},  # odd wk: Writing, even: Extensive
]

GH_STRAND_NAMES = {
    "B7.1": "1. CUSTOMS AND INSTITUTIONS",
    "B7.2": "2. LISTENING AND SPEAKING",
    "B7.3": "3. READING",
    "B7.4": "4. LANGUAGE AND USAGE",
    "B7.5": "5. COMPOSITION WRITING",
    "B7.6": "6. LITERATURE",
}

RPK = {
    "math": "Learners handled numbers up to 1,000,000, fractions, decimals, integers, shapes and data through primary school (B1-B6).",
    "science": "Learners studied living things, materials, cycles, systems, energy and their environment through B1-B6 practical activities.",
    "english": "Learners can hold conversations, read varied texts and write structured paragraphs; they know songs, folktales, poems and stories from primary school.",
    "ghanaian": "Learners speak the local language daily and know its songs, proverbs, folktales and customs from primary school and home."
}

READERS_EN = ["a Ghanaian folktale", "a poem from the class anthology", "a short drama scene",
              "a chapter of a story book", "a myth or legend", "an excerpt from a children's novel"]
READERS_GH = ["Ananses\u025bm (folk tale book)", "a poem collection", "a short story in the local language",
              "a class chart story", "a picture book", "a children's magazine"]

def reading_period(session_num, reader_list, lang_note=""):
    reader = reader_list[(session_num - 1) % len(reader_list)]
    return {
        "starter": [
            "Greet learners; 1-minute 'book talk': teacher shows and names a book from the class collection.",
            "Quick recall: learners mention one thing they read last time.",
            f"NEW TODAY: Everyone reads {reader} quietly.",
            "Set reading rules: eyes on text, quiet lips, note new words.",
        ],
        "main": [
            "ACTIVITY 1 (Silent reading \u2013 7 min): Learners read {r} individually; teacher listens to 2-3 learners read aloud in turn.".format(r=reader),
            "ACTIVITY 2 (Pair read \u2013 5 min): Pairs take turns reading short passages aloud to each other; partners help with hard words.",
            "ACTIVITY 3 (Respond to text \u2013 5 min): Learners answer 3 quick questions: 'What was it about? Who was in it? Which part did you like?'",
            f"ACTIVITY 4 (Record \u2013 3 min): Learners write the title and one sentence about {reader} in their reading log{lang_note}.",
        ],
        "plenary": [
            "2-3 learners share their favourite part with the class.",
            "Teacher displays the reading log and praises consistent readers.",
            "Homework: read one page to a family member and retell it.",
            "Encourage learners to borrow a book for the week.",
        ], "reader": reader,
    }

def get_act(key, meta, session_num, total_sessions, day, week, group=None):
    ind = meta.get("ind_desc", "")
    ind_l = ind[0].lower() + ind[1:] if ind else ""
    ss = str(meta.get("sub_strand", "")).replace("Sub-strand ", "").lower()
    if session_num == 1:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Introduction"
    elif session_num == total_sessions:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Consolidation"
    else:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Practice"

    # dedicated Extensive Reading period
    if group == "B7.5" and key == "english":
        rp = reading_period(session_num, READERS_EN if key == "english" else READERS_GH,
                            "" if key == "english" else " in the local language")
        perf_indicator = "By the end of the lesson, learners will be able to: read independently for pleasure and information, and keep a reading log."
        return {"session_title": f"Weekly Reading Period \u2014 {rp['reader'].capitalize()}",
                "perf_indicator": perf_indicator, "starter": rp["starter"],
                "main": rp["main"], "plenary": rp["plenary"]}

    if key == "math":
        starter = [
            "Greet learners; mental maths drill: quick facts on the board (30 seconds).",
            "Quick 'number of the day': place value, factors or estimation warm-up with number cards.",
            f"NEW TODAY (Week {week}): Today we {ind_l}",
            "Share the lesson goal in child-friendly words; write key words on the board.",
        ]
        main = [
            f"ACTIVITY 1 (Concrete \u2013 5 min): Teacher models with manipulatives (number chart, bottle tops, base-ten materials) \u2013 {ind_l}",
            "ACTIVITY 2 (Guided \u2013 5 min): Learners work in pairs with manipulatives; teacher moves round to support struggling learners.",
            f"ACTIVITY 3 (Pictorial \u2013 5 min): Learners draw/match/solve on the board or in exercise books related to sub-strand {ss}.",
            "ACTIVITY 4 (Abstract/Share \u2013 5 min): 2\u20133 pairs solve one example on the board; class agrees on the rule/answer.",
        ]
        plenary = [
            "Quick-fire oral quiz: 3 questions on today's skill (thumbs up/down, show me on fingers).",
            "One learner explains today's rule in their own words.",
            "Homework: solve 3 similar examples in the exercise book.",
            "Preview: link today's skill to the next lesson.",
        ]
    elif key == "science":
        starter = [
            "Greet learners with the science song; recap last lesson in one sentence.",
            "Show real object / picture / chart related to today's topic; ask 'What do you notice?'",
            f"NEW TODAY (Week {week}): We {ind_l}",
            "Introduce key science words; learners repeat chorally.",
        ]
        main = [
            f"ACTIVITY 1 (Observe/Demonstrate \u2013 5 min): Teacher demonstrates or shows specimens \u2013 {ind_l}",
            "ACTIVITY 2 (Explore \u2013 5 min): Groups observe with senses/hand lens and record simple findings in exercise books.",
            f"ACTIVITY 3 (Do \u2013 5 min): Hands-on task: sort, match, draw or build a model (local TLMs: bottles, cartons, sand) on {ss}.",
            "ACTIVITY 4 (Share \u2013 5 min): Groups present findings; teacher corrects misconceptions and states the science idea.",
        ]
        plenary = [
            "Learners state one new thing they discovered today.",
            "Oral quick check: 2 'what/why' questions.",
            "Homework: observe something at home related to the lesson and report tomorrow.",
            "Preview next Science lesson.",
        ]
    elif key == "english":
        starter = [
            "Greet learners; 1-minute phonics/rhyme warm-up (clap syllables, sing a familiar song).",
            "Revise last lesson's new words with word cards.",
            f"NEW TODAY (Week {week}): Today's focus \u2013 {ind_l}",
            "Introduce and drill 3\u20135 new words (say, spell, meaning).",
        ]
        main = [
            f"ACTIVITY 1 (Model \u2013 5 min): Teacher models the skill using chart/picture/big book \u2013 {ind_l}",
            "ACTIVITY 2 (Guided \u2013 5 min): Whole class practises together (read aloud, repeat, discuss pictures).",
            f"ACTIVITY 3 (Pair/Group practice \u2013 5 min): Pairs do the task (role-play, sentence building, shared writing); teacher supports.",
            "ACTIVITY 4 (Produce & share \u2013 5 min): 2\u20133 learners demonstrate; class gives feedback; teacher highlights good language use.",
        ]
        plenary = [
            "Exit question: every learner says one word/sentence learnt today.",
            "Choral repetition of the key words/song once more.",
            "Homework: practise today's words/sentences with a family member.",
            "Preview next English lesson.",
        ]
    else:  # ghanaian
        starter = [
            "Greet learners in the local language; sing a familiar local song together.",
            "Revise last lesson's new words with word/picture cards.",
            f"NEW TODAY (Week {week}): Nn\u025b adwuma \u2013 {ind_l}",
            "Introduce 3\u20135 new words (say, meaning, use in a sentence).",
        ]
        main = [
            f"ACTIVITY 1 (Model \u2013 5 min): Teacher models the skill (talk, read aloud, write on board) \u2013 {ind_l}",
            "ACTIVITY 2 (Guided \u2013 5 min): Whole class practises: repeat, answer questions, read or copy together.",
            f"ACTIVITY 3 (Pair/Group \u2013 5 min): Pairs/groups do the task in the local language (dialogue, word building, sentence or composition writing) on {ss}.",
            "ACTIVITY 4 (Share \u2013 5 min): Groups present; teacher praises good usage and corrects errors gently.",
        ]
        plenary = [
            "Exit question: each learner says one new word/sentence in the local language.",
            "Recite today's rhyme/song once more.",
            "Homework: use today's words at home and tell a family member what was learnt.",
            "Preview next Ghanaian Language lesson.",
        ]
    perf_indicator = f"By the end of the lesson, learners will be able to: {ind_l}"
    return {"session_title": session_title, "perf_indicator": perf_indicator,
            "starter": starter, "main": main, "plenary": plenary}

def slot_group(slot, week):
    """slot is a string (fixed) or [odd_week_code, even_week_code]."""
    if isinstance(slot, list):
        return slot[0] if week % 2 == 1 else slot[1]
    return slot

def build_one(subj):
    path = f"{DBDIR}/{subj['sid']}_B7_curriculum_db_clean.json"
    with open(path) as f:
        cur_db = json.load(f)
    codes = sorted(cur_db.keys(), key=lambda x: [int(p) for p in x.replace('B', '').split('.')])
    strand_groups = defaultdict(list)
    for code in codes:
        p = code.split('.')
        strand_groups[f"{p[0]}.{p[1]}"].append(code)
    strand_groups = {k: sorted(v) for k, v in strand_groups.items()}
    if "patterns" in subj:
        needed = {slot_group(s, w) for pat in subj["patterns"] for _, s in pat for w in range(1, 13)}
    else:
        needed = {slot_group(s, w) for _, s in subj["plan"] for w in range(1, 13)}
    missing = needed - set(strand_groups)
    assert not missing, f"{subj['key']}: strands missing in DB: {missing}"
    strand_iters = {sc: cycle(strand_groups[sc]) for sc in strand_groups}
    lessons_raw = []
    n = 1
    for term in (1, 2, 3):
        for week in range(1, 13):
            week_slots = subj["patterns"][(week - 1) % 3] if "patterns" in subj else subj["plan"]
            for day_name, slot in week_slots:
                sc = slot_group(slot, week)
                ind_code = next(strand_iters[sc])
                lessons_raw.append({"lesson_num": n, "term": term, "week": week, "day": day_name,
                                    "strand_num": int(sc.split('.')[1]), "ind_code": ind_code})
                n += 1
    assert len(lessons_raw) == 180
    ind_counts = Counter(l["ind_code"] for l in lessons_raw)
    ind_current = Counter()
    enriched = []
    for l in lessons_raw:
        code = l["ind_code"]
        meta = cur_db[code]
        ind_current[code] += 1
        grp = f"B7.{code.split('.')[1]}"
        act = get_act(subj["key"], meta, ind_current[code], ind_counts[code], l["day"], l["week"], group=grp)
        if subj["key"] == "ghanaian":
            strand_name = GH_STRAND_NAMES.get(grp, meta.get("strand", ""))
        else:
            strand_name = meta.get("strand", "")
        enriched.append({
            "lesson_num": l["lesson_num"], "term": l["term"], "week": l["week"], "day": l["day"],
            "strand_num": l["strand_num"], "strand_name": strand_name,
            "sub_strand": meta.get("sub_strand", ""), "cs_code": meta.get("cs_code", ""),
            "cs_desc": meta.get("cs_desc", ""), "ind_code": code,
            "ind_desc": meta.get("ind_desc", ""), "is_revision": False,
            "session_title": act["session_title"], "perf_indicator": act["perf_indicator"],
            "competencies": meta.get("competencies", ""),
            "resources": meta.get("resources", ""), "keywords": meta.get("keywords", ""),
            "rpk": RPK[subj["key"]],
            "starter": act["starter"], "main": act["main"], "plenary": act["plenary"],
            "assessment": meta.get("assessment", "Oral questions; class exercise; teacher observation"),
        })
    out = f"{subj['key']}_b7_lessons_enriched.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=1, ensure_ascii=False)
    dist = Counter(l["ind_code"] for l in lessons_raw)
    top, lo = dist.most_common(1)[0], dist.most_common()[-1]
    print(f"OK {subj['name']}: {len(enriched)} lessons | {len(dist)} indicators used | spread {lo[1]}..{top[1]}")

if __name__ == "__main__":
    for s in subjects:
        build_one(s)
