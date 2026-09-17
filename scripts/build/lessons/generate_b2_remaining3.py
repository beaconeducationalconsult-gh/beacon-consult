#!/usr/bin/env python3
"""Generate 180 full-year daily lesson plans for Basic 2 remaining subjects:
Creative Arts, History, RME. Uses verified B2 DBs (authentic NaCCA text).
Includes session-variant rotation so indicators with many sessions vary.
Output: {creative_arts,history,rme}_b2_lessons_enriched.json
"""
import json
from collections import defaultdict, Counter
from itertools import cycle

DBDIR = 'data/curriculum'
DAYS5 = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

subjects = [
    {"key": "creative_arts", "sid": "creative-arts", "name": "Creative Arts",
     "week_plan": [("Monday", "B2.1", 1), ("Tuesday", "B2.2", 2), ("Wednesday", "B2.1", 1),
                   ("Thursday", "B2.2", 2), ("Friday", "B2.1", 1)]},
    {"key": "history", "sid": "history", "name": "History",
     "week_plan": None,  # global indicator cycle: 4 indicators x 45 sessions each
     },
    {"key": "rme", "sid": "rme", "name": "Religious and Moral Education",
     "week_plan": [("Monday", "B2.1", 1), ("Tuesday", "B2.2", 2), ("Wednesday", "B2.3", 3),
                   ("Thursday", "B2.4", 4), ("Friday", "B2.1", 1)]},
]

RPK = {
    "creative_arts": "Learners sing, dance, draw, colour, mould and role-play informally at home and in KG; they see local artworks and performances at festivals and durbars.",
    "history": "Learners have listened to stories told by elders and grandparents, seen chiefs and elders at durbars, and know some local traditions and festivals.",
    "rme": "Learners pray and worship with their families (Christian, Islamic, Traditional), know basic moral rules of right and wrong from home.",
}

# variant banks (rotate by session number to reduce repetition)
VAR = {
    "creative_arts": {
        "media": ["picture charts and real artworks", "local instruments and recorded music",
                  "textiles, clay and found materials", "pupils' own bodies and voice"],
        "task": ["create a small individual piece", "work in pairs on a joint piece",
                 "create in groups and stage a mini-show", "make individual pieces and hold a gallery walk"],
    },
    "history": {
        "media": ["storytelling with picture charts", "a simple timeline drawn on the board",
                  "a map of Ghana and local examples", "real objects or drawings as artefacts"],
        "task": ["sequence 3\u20134 picture cards and explain the order", "draw and label what they learnt",
                 "role-play the event in small groups", "answer 4 comprehension questions in pairs"],
    },
    "rme": {
        "media": ["a short moral story or scripture text", "a proverb or wise saying",
                  "a picture chart of a worship scene", "a short song or recitation"],
        "task": ["role-play the right choice", "sort right/wrong behaviour cards in groups",
                 "draw a poster of the moral lesson", "share one sentence each in a circle"],
    },
}

def get_act(key, meta, session_num, total_sessions, day, week):
    ind = meta.get("ind_desc", "")
    ind_l = ind[0].lower() + ind[1:] if ind else ""
    ss = str(meta.get("sub_strand", "")).replace("Sub-strand ", "").lower()
    vn = (session_num - 1) % 4
    media = VAR[key]["media"][vn]
    task = VAR[key]["task"][vn]
    if session_num == 1:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Introduction"
    elif session_num == total_sessions:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Consolidation"
    else:
        session_title = f"Session {session_num} of {total_sessions} \u2014 Practice"

    if key == "creative_arts":
        starter = [
            "Greet learners with a creative warm-up clap / body percussion.",
            f"Show {media} linked to today's lesson; ask 'What can you see? How does it make you feel?'",
            f"NEW TODAY (Week {week}): Creative Arts \u2013 we {ind_l}",
            "Introduce tools/materials and safety rules for handling them.",
        ]
        main = [
            f"ACTIVITY 1 (Demonstration \u2013 5 min): Teacher models the skill using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Guided Practice \u2013 5 min): Pupils practise in pairs/small groups; teacher moves round scaffolding technique and safe use of tools.",
            f"ACTIVITY 3 (Creative Making \u2013 7 min): Pupils {task} on the lesson's theme ({ss}).",
            "ACTIVITY 4 (Showcase \u2013 3 min): Mini gallery walk / performance; peer appreciation with 'two stars and a wish'; teacher feedback on creativity and craftsmanship.",
        ]
        plenary = [
            "Clean-up song \u2013 pupils tidy tools and materials together.",
            "Reflection questions: 'What did you enjoy? What was challenging? What will you try differently?'",
            "Homework: finish or practise today's artwork/song/dance at home with family.",
            "Preview next Visual/Performing Arts lesson.",
        ]
    elif key == "history":
        starter = [
            "Greet learners; sing the Ghana National Anthem or a patriotic song briefly.",
            f"Show {media} related to today's topic; ask 'What do you think happened here?'",
            f"NEW TODAY (Week {week}): In History we {ind_l}",
            "Write 3 key words on the board; read them chorally.",
        ]
        main = [
            f"ACTIVITY 1 (Story/Source \u2013 5 min): Teacher presents the topic using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Guided Discussion \u2013 5 min): Turn-and-talk in pairs on 3 probing questions ('Who? What? Why does it matter?').",
            f"ACTIVITY 3 (Group Task \u2013 7 min): In groups, learners {task} about {ss}.",
            "ACTIVITY 4 (Share \u2013 3 min): Groups present; teacher links the lesson to Ghanaian identity, citizenship and values.",
        ]
        plenary = [
            "Recite 2 key facts from today's lesson \u2013 call and response.",
            "Ask: 'Why is this part of our history important for us as Ghanaians?'",
            "Homework: ask an elder at home one question about today's topic; bring one sentence tomorrow.",
            "Preview the next History lesson.",
        ]
    else:  # rme
        starter = [
            "Greet learners peacefully; open with an inclusive moment: short prayer / silence / moral song (Christian\u2013Islamic\u2013Traditional).",
            f"Show {media} linked to today's moral theme; ask learners what it teaches.",
            f"NEW TODAY (Week {week}): R.M.E. \u2013 we {ind_l}",
            "Introduce the key moral vocabulary for the lesson.",
        ]
        main = [
            f"ACTIVITY 1 (Story/Text \u2013 5 min): Teacher shares {media} on the lesson's theme \u2013 {ind_l}",
            "ACTIVITY 2 (Guided Discussion \u2013 5 min): Think-pair-share: 'How does this teaching help us at home and in school?'",
            f"ACTIVITY 3 (Values Practice \u2013 7 min): Learners {task} showing the moral value in action ({ss}).",
            "ACTIVITY 4 (Reflection \u2013 3 min): Groups share; teacher affirms honesty, respect, tolerance and love from Christian, Islamic and Traditional perspectives.",
        ]
        plenary = [
            "Recite the golden rule / a memory verse / a wise saying together.",
            "Commitment question: 'What will you do differently from today?'",
            "Homework: share today's moral lesson with family and do one good deed.",
            "Close with an inclusive prayer/song; preview next lesson.",
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
    lessons_raw = []
    n = 1
    if subj["week_plan"] is None:
        # global round-robin over all indicators (balanced coverage for thin curricula)
        all_codes = [c for sc in sorted(strand_groups) for c in sorted(strand_groups[sc])]
        it = cycle(all_codes)
        for term in (1, 2, 3):
            for week in range(1, 13):
                for day_name in DAYS5:
                    ind_code = next(it)
                    p = ind_code.split('.')
                    lessons_raw.append({"lesson_num": n, "term": term, "week": week, "day": day_name,
                                        "strand_num": int(p[1]), "ind_code": ind_code})
                    n += 1
    else:
        missing = {s for _, s, _ in subj["week_plan"]} - set(strand_groups)
        assert not missing, f"{subj['key']}: week_plan strands missing in DB: {missing}"
        strand_iters = {sc: cycle(sorted(strand_groups[sc])) for sc in strand_groups}
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
        enriched.append({
            "lesson_num": l["lesson_num"], "term": l["term"], "week": l["week"], "day": l["day"],
            "strand_num": l["strand_num"], "strand_name": meta.get("strand", ""),
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

if __name__ == "__main__":
    for s in subjects:
        build_one(s)
