#!/usr/bin/env python3
"""Generate 180 full-year daily lesson plans (3 terms x 12 weeks x 5 days)
for Basic 2 Core-4 subjects: Mathematics, Science, English, Ghanaian Language.
Uses the verified B2 curriculum DBs (authentic NaCCA indicator/CS text).
Output: {subject}_b2_lessons_enriched.json
"""
import json
from collections import defaultdict, Counter
from itertools import cycle

DBDIR = 'data/curriculum'

subjects = [
    {"key": "math", "sid": "mathematics", "name": "Mathematics",
     "week_plan": [("Monday", "B2.1", 1), ("Tuesday", "B2.2", 2), ("Wednesday", "B2.3", 3),
                   ("Thursday", "B2.4", 4), ("Friday", "B2.1", 1)]},
    {"key": "science", "sid": "science", "name": "Integrated Science",
     "week_plan": [("Monday", "B2.1", 1), ("Tuesday", "B2.2", 2), ("Wednesday", "B2.3", 3),
                   ("Thursday", "B2.4", 4), ("Friday", "B2.5", 5)]},
    {"key": "english", "sid": "english-language", "name": "English Language",
     "week_plan": [("Monday", "B2.1", 1), ("Tuesday", "B2.2", 2), ("Wednesday", "B2.4", 3),
                   ("Thursday", "B2.5", 4), ("Friday", "B2.6", 5)]},
    {"key": "ghanaian", "sid": "ghanaian-language", "name": "Ghanaian Language",
     "week_plan": [("Monday", "B2.1", 1), ("Tuesday", "B2.2", 2), ("Wednesday", "B2.3", 3),
                   ("Thursday", "B2.5", 4), ("Friday", "B2.6", 5)]},
]

# Twi/English bilingual strand names for Ghanaian (mirrors Basic 1 style)
GH_STRAND_NAMES = {
    "B2.1": "1. NTI - Listening and Speaking / Oral Language",
    "B2.2": "2. AKENKAN - Reading",
    "B2.3": "3. ATWER\u0190 - Writing",
    "B2.5": "5. ATWER\u0190 HO NHYEHY\u0190E / Grammar Usage",
    "B2.6": "6. AKENKAN TR\u0190W - Extensive Reading",
}

RPK = {
    "math": "Learners count everyday objects (bottle tops, stones, coins), sing number songs and recite counting rhymes from KG.",
    "science": "Learners observe plants, animals, weather and everyday materials at home and in the school environment daily.",
    "english": "Learners use simple spoken English at home and school, sing familiar songs and listen to short stories.",
    "ghanaian": "Learners speak the local language at home, sing local songs, recite rhymes and tell simple stories.",
}

def get_act(key, meta, session_num, total_sessions, day, week):
    ind = meta.get("ind_desc", "")
    ind_l = ind[0].lower() + ind[1:] if ind else ""
    ss = str(meta.get("sub_strand", "")).replace("Sub-strand ", "").lower()
    if session_num == 1:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Introduction"
    elif session_num == total_sessions:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Consolidation"
    else:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Practice"

    if key == "math":
        starter = [
            "Greet learners; mental maths drill: count forwards/backwards in 1s, 2s, 5s or 10s (30 seconds).",
            f"Quick 'number of the day': learners say the number before/after using bottle tops or number cards.",
            f"NEW TODAY (Week {week}): Today we {ind_l}",
            "Share lesson goal in child-friendly words; write key words on the board.",
        ]
        main = [
            f"ACTIVITY 1 (Concrete \u2013 5 min): Teacher models with real objects (bottle tops, stones, sticks) \u2013 {ind_l}",
            "ACTIVITY 2 (Guided \u2013 5 min): Learners work in pairs with manipulatives; teacher moves round to support struggling learners.",
            f"ACTIVITY 3 (Pictorial \u2013 5 min): Draw/match on the board or in exercise books related to sub-strand {ss}.",
            "ACTIVITY 4 (Abstract/Share \u2013 5 min): 2\u20133 pairs solve one example on the board; class agrees on the rule/answer.",
        ]
        plenary = [
            "Quick-fire oral quiz: 3 questions on today's skill (thumbs up/down, show me on fingers).",
            "Ask one learner to explain today's rule in their own words.",
            "Homework: solve 3 similar examples in exercise book / count objects at home.",
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
            "ACTIVITY 2 (Explore \u2013 5 min): Groups observe with senses/hand lens, record simple findings in exercise books.",
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
            "Greet learners; 1-minute phonics/ rhyme warm-up (clap syllables, sing a familiar song).",
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
            f"ACTIVITY 3 (Pair/Group \u2013 5 min): Pairs/groups do the task in the local language (dialogue, word building, sentence writing) on {ss}.",
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

def build_one(subj):
    path = f"{DBDIR}/{subj['sid']}_B2_curriculum_db_clean.json"
    with open(path) as f:
        cur_db = json.load(f)
    codes = sorted(cur_db.keys(), key=lambda x: [int(p) for p in x.replace('B', '').split('.')])
    strand_groups = defaultdict(list)
    for code in codes:
        parts = code.split('.')
        strand_groups[f"{parts[0]}.{parts[1]}"].append(code)
    missing = {s for _, s, _ in subj["week_plan"]} - set(strand_groups)
    assert not missing, f"{subj['key']}: week_plan strands missing in DB: {missing}"
    strand_iters = {sc: cycle(sorted(strand_groups[sc])) for sc in strand_groups}
    # 180 lessons
    lessons_raw = []
    n = 1
    for term in (1, 2, 3):
        for week in range(1, 13):
            for day_name, strand_code, strand_num in subj["week_plan"]:
                ind_code = next(strand_iters[strand_code])
                lessons_raw.append({"lesson_num": n, "term": term, "week": week, "day": day_name,
                                    "strand_num": strand_num, "ind_code": ind_code})
                n += 1
    assert len(lessons_raw) == 180
    ind_counts = Counter(l["ind_code"] for l in lessons_raw)
    ind_current = Counter()
    enriched = []
    for l in lessons_raw:
        code = l["ind_code"]
        meta = cur_db[code]
        ind_current[code] += 1
        act = get_act(subj["key"], meta, ind_current[code], ind_counts[code], l["day"], l["week"])
        strand_name = (GH_STRAND_NAMES.get(f"B2.{code.split('.')[1]}")
                       if subj["key"] == "ghanaian" else meta.get("strand", ""))
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
    out = f"{subj['key']}_b2_lessons_enriched.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=1, ensure_ascii=False)
    print(f"OK {subj['name']}: {len(enriched)} lessons -> {out}")
    return out

if __name__ == "__main__":
    for s in subjects:
        build_one(s)
