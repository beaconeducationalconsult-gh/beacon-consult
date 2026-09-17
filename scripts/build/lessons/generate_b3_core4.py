#!/usr/bin/env python3
"""Generate 180 full-year daily lesson plans for Basic 3 Core-4 subjects:
Mathematics, Science, English, Ghanaian Language. Uses verified B3 DBs.
Output: {subject}_b3_lessons_enriched.json
"""
import json
from collections import defaultdict, Counter
from itertools import cycle

DBDIR = 'data/curriculum'

subjects = [
    {"key": "math", "sid": "mathematics", "name": "Mathematics",
     "week_plan": None,  # dynamic: Tue alternates B3.2 (odd weeks) / B3.1 (even weeks)
     },
    {"key": "science", "sid": "science", "name": "Integrated Science",
     "week_plan": [("Monday", "B3.1", 1), ("Tuesday", "B3.2", 2), ("Wednesday", "B3.3", 3),
                   ("Thursday", "B3.4", 4), ("Friday", "B3.5", 5)]},
    {"key": "english", "sid": "english-language", "name": "English Language",
     # group keys; special case: official-typo B3.3.13.1.1 scheduled with Writing (B3.4)
     "week_plan": [("Monday", "B3.1", 1), ("Tuesday", "B3.2", 2), ("Wednesday", "B3.4", 3),
                   ("Thursday", "B3.5", 4), ("Friday", "B3.6", 5)],
     "group_override": {"B3.3.13.1.1": "B3.4"},
     },
    {"key": "ghanaian", "sid": "ghanaian-language", "name": "Ghanaian Language",
     "week_plan": [("Monday", "B3.1", 1), ("Tuesday", "B3.2", 2), ("Wednesday", "B3.3", 3),
                   ("Thursday", "B3.5", 4), ("Friday", "B3.6", 5)]},
]

GH_STRAND_NAMES = {
    "B3.1": "1. NTI - Listening and Speaking / Oral Language",
    "B3.2": "2. AKENKAN - Reading",
    "B3.3": "3. ATWER\u0190 - Writing",
    "B3.5": "5. ATWER\u0190 HO NHYEHY\u0190E / Grammar Usage",
    "B3.6": "6. AKENKAN TR\u0190W - Extensive Reading",
}

RPK = {
    "math": "Learners count everyday objects (bottle tops, stones, coins) and used number charts and manipulatives in Basic 1 and 2.",
    "science": "Learners observed plants, animals, weather and everyday materials in Basic 1 and 2; they explore their environment daily.",
    "english": "Learners can sing songs, recite rhymes, read simple words and write simple sentences from Basic 1 and 2.",
    "ghanaian": "Learners speak the local language at home and learned songs, rhymes, reading and writing basics in Basic 1 and 2.",
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
            "Greet learners; mental maths drill: count forwards/backwards in 10s, 50s, 100s or 1000s (30 seconds).",
            "Quick 'number of the day': learners read and build the number with place-value cards/bottle tops.",
            f"NEW TODAY (Week {week}): Today we {ind_l}",
            "Share the lesson goal in child-friendly words; write key words on the board.",
        ]
        main = [
            f"ACTIVITY 1 (Concrete \u2013 5 min): Teacher models with manipulatives (bottle tops, number chart, base-ten materials) \u2013 {ind_l}",
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

def group_key(subj, code, meta):
    if subj["key"] == "english":
        ov = subj.get("group_override", {})
        if code in ov:
            return ov[code]
        cs = meta.get("cs_code", "")
        if cs:
            return '.'.join(cs.split('.')[:2])
    parts = code.split('.')
    return f"{parts[0]}.{parts[1]}"

def build_one(subj):
    path = f"{DBDIR}/{subj['sid']}_B3_curriculum_db_clean.json"
    with open(path) as f:
        cur_db = json.load(f)
    codes = sorted(cur_db.keys(), key=lambda x: [int(p) for p in x.replace('B', '').split('.')])
    strand_groups = defaultdict(list)
    for code in codes:
        strand_groups[group_key(subj, code, cur_db[code])].append(code)
    strand_groups = {k: sorted(v) for k, v in strand_groups.items()}
    lessons_raw = []
    n = 1
    if subj["week_plan"] is None:  # math: dynamic Tuesday
        math_iters = {sc: cycle(codes_list) for sc, codes_list in strand_groups.items()}
        for term in (1, 2, 3):
            for week in range(1, 13):
                tue = "B3.2" if week % 2 == 1 else "B3.1"
                plan = [("Monday", "B3.1", 1), ("Tuesday", tue, 2 if tue == "B3.2" else 1),
                        ("Wednesday", "B3.3", 3), ("Thursday", "B3.4", 4), ("Friday", "B3.1", 1)]
                for day_name, strand_code, strand_num in plan:
                    ind_code = next(math_iters[strand_code])
                    lessons_raw.append({"lesson_num": n, "term": term, "week": week, "day": day_name,
                                        "strand_num": strand_num, "ind_code": ind_code})
                    n += 1
    else:
        missing = {s for _, s, _ in subj["week_plan"]} - set(strand_groups)
        assert not missing, f"{subj['key']}: week_plan strands missing in DB: {missing}"
        strand_iters = {sc: cycle(strand_groups[sc]) for sc in strand_groups}
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
        if subj["key"] == "ghanaian":
            strand_name = GH_STRAND_NAMES.get(f"B3.{code.split('.')[1]}", meta.get("strand", ""))
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
    out = f"{subj['key']}_b3_lessons_enriched.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=1, ensure_ascii=False)
    # report distribution
    dist = Counter(l["ind_code"] for l in lessons_raw)
    top = dist.most_common(1)[0]
    print(f"OK {subj['name']}: {len(enriched)} lessons -> {out} | most-repeated {top[0]} x{top[1]}")

if __name__ == "__main__":
    for s in subjects:
        build_one(s)
