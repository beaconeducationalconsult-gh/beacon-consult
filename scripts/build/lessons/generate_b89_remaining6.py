#!/usr/bin/env python3
"""Generate 180 full-year daily lesson plans for Basic 8 AND Basic 9 remaining subjects:
RME, Computing, Social Studies, Career Technology, Creative Arts and Design, French.
Uses verified B8/B9 CCP DBs. Subject-specific 3-phase templates (from the B7 build).
Output: {key}_b{8,9}_lessons_enriched.json
"""
import json
from collections import defaultdict, Counter
from itertools import cycle

DBDIR = 'data/curriculum'
DAYS5 = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

def P(*slots):
    """slots: (day, code_or_[odd,even]) -> list; strand_num derived from code."""
    out = []
    for day, slot in slots:
        out.append((day, slot))
    return out

GRADES = {
    "B8": [
        {"key": "rme", "sid": "rme", "name": "Religious and Moral Education",
         "week_plan": [("Monday", "B8.2"), ("Tuesday", "B8.5"), ("Wednesday", ["B8.1", "B8.3"]),
                       ("Thursday", ["B8.4", "B8.6"]), ("Friday", "B8.2")]},
        {"key": "computing", "sid": "computing", "name": "Computing",
         "week_plan": [("Monday", "B8.1"), ("Tuesday", "B8.2"), ("Wednesday", "B8.3"),
                       ("Thursday", "B8.4"), ("Friday", "B8.1")]},
        {"key": "social_studies", "sid": "social-studies", "name": "Social Studies",
         "week_plan": None},
        {"key": "career_technology", "sid": "career-technology", "name": "Career Technology",
         "week_plan": [("Monday", "B8.5"), ("Tuesday", "B8.3"), ("Wednesday", "B8.2"),
                       ("Thursday", ["B8.1", "B8.4"]), ("Friday", ["B8.6", "B8.4"])]},
        {"key": "creative_arts_design", "sid": "creative-arts-design", "name": "Creative Arts and Design",
         "week_plan": [("Monday", "B8.1"), ("Tuesday", "B8.2"), ("Wednesday", "B8.2"),
                       ("Thursday", "B8.2"), ("Friday", "B8.1")]},
        {"key": "french", "sid": "french", "name": "French",
         "week_plan": [("Monday", "B8.1"), ("Tuesday", "B8.5"), ("Wednesday", ["B8.2", "B8.4"]),
                       ("Thursday", ["B8.4", "B8.6"]), ("Friday", ["B8.6", "B8.8"])]},
    ],
    "B9": [
        {"key": "rme", "sid": "rme", "name": "Religious and Moral Education",
         "week_plan": [("Monday", "B9.2"), ("Tuesday", "B9.5"), ("Wednesday", ["B9.1", "B9.3"]),
                       ("Thursday", ["B9.4", "B9.6"]), ("Friday", "B9.2")]},
        {"key": "computing", "sid": "computing", "name": "Computing",
         "week_plan": [("Monday", "B9.1"), ("Tuesday", "B9.2"), ("Wednesday", "B9.3"),
                       ("Thursday", "B9.4"), ("Friday", "B9.1")]},
        {"key": "social_studies", "sid": "social-studies", "name": "Social Studies",
         "week_plan": None},
        {"key": "career_technology", "sid": "career-technology", "name": "Career Technology",
         "week_plan": [("Monday", "B9.5"), ("Tuesday", "B9.3"), ("Wednesday", "B9.2"),
                       ("Thursday", ["B9.1", "B9.4"]), ("Friday", ["B9.6", "B9.4"])]},
        {"key": "creative_arts_design", "sid": "creative-arts-design", "name": "Creative Arts and Design",
         "week_plan": [("Monday", "B9.1"), ("Tuesday", "B9.2"), ("Wednesday", "B9.2"),
                       ("Thursday", "B9.2"), ("Friday", "B9.1")]},
        {"key": "french", "sid": "french", "name": "French",
         "week_plan": [("Monday", "B9.9"), ("Tuesday", "B9.7"), ("Wednesday", ["B9.2", "B9.10"]),
                       ("Thursday", ["B9.5", "B9.6"]), ("Friday", ["B9.8", "B9.10"])]},
    ],
}

RPK = {
    "rme": "Learners pray and worship with their families (Christian, Islamic, Traditional) and built moral values through home, primary school and JHS 1-2 RME.",
    "computing": "Learners have used smartphones or computers, know basic ICT tools, productivity software and safe online practices from JHS 1-2 Computing.",
    "social_studies": "Learners studied the environment, family life, sense of purpose, law and order and nationhood through JHS 1-2 Social Studies and their daily community life.",
    "career_technology": "Learners observed adults cooking, sewing, farming and fixing things; they practised basic hygiene, tools and design processes in JHS 1-2 Career Technology.",
    "creative_arts_design": "Learners drew, modelled, sang and performed through primary Creative Arts and JHS 1-2 Design; they see Ghanaian designs, logos, kente and artworks around them.",
    "french": "Learners heard French around them (Ghana is surrounded by francophone countries) and learned greetings, family, environment and shopping vocabulary in JHS 1-2 French.",
}

VAR = {
    "computing": {
        "media": ["a real computer/laptop if available, or printed screenshots", "chart diagrams of computer parts and networks",
                  "an unplugged demonstration (cards, bottles, paper arrows)", "a short video or poster on technology"],
        "task": ["work in pairs on the practice exercise", "demonstrate the steps to the class in groups",
                 "complete the worksheet/diagram labelling individually", "solve the challenge task in small groups and present"],
    },
    "social_studies": {
        "media": ["a map or chart of Ghana", "a short case story from the community",
                  "picture charts of real-life situations", "a simple table/graph on the board"],
        "task": ["discuss the case in groups and present 3 points", "sort cause-and-effect cards and justify the order",
                 "draw a poster showing the solution", "role-play the situation and class debriefs"],
    },
    "career_technology": {
        "media": ["real tools/materials or pictures of them", "a finished artefact/product as a sample",
                  "a step-by-step process chart", "local products and packaging from the community"],
        "task": ["practise the skill under teacher supervision", "produce a small item in pairs following the steps",
                 "complete a labelled diagram/worksheet", "cost and plan the item as a mini business task"],
    },
    "creative_arts_design": {
        "media": ["samples of Ghanaian designs, logos and artworks", "local tools and materials (pencils, clay, fabric, found objects)",
                  "a step-by-step design process chart", "pictures of famous Ghanaian artists' works"],
        "task": ["sketch own design ideas in the sketchbook", "create the artefact individually or in pairs",
                 "work as a design team on a brief", "mount a mini exhibition and peer-appraise"],
    },
    "french": {
        "media": ["flashcards with French words and pictures", "a short recorded or teacher-modelled dialogue",
                  "a wall chart of French vocabulary", "a simple French song or rhyme"],
        "task": ["repeat chorally then in pairs (répétition)", "act out the dialogue in groups (jeu de rôle)",
                 "match words to pictures in the exercise book", "ask and answer in a circle (questions-réponses)"],
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

    if key == "computing":
        starter = [
            "Greet learners; 1-minute 'tech talk': name one technology you used since yesterday.",
            f"Show {media} related to today's lesson; ask 'What do you notice? Where have you seen this?'",
            f"NEW TODAY (Week {week}): In Computing we {ind_l}",
            "Introduce key terms and write them on the board; drill pronunciation.",
        ]
        main = [
            f"ACTIVITY 1 (Model/Demonstrate \u2013 5 min): Teacher demonstrates using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Guided practice \u2013 5 min): Learners follow step-by-step in pairs (or follow the unplugged demo); teacher moves round supporting.",
            f"ACTIVITY 3 (Task \u2013 5 min): Learners {task} on {ss}.",
            "ACTIVITY 4 (Share \u2013 3 min): 2-3 pairs/groups demonstrate; class checks answers; teacher corrects misconceptions.",
        ]
        plenary = [
            "Quick oral quiz: 3 questions on today's concept (thumbs up/down, answer on show-me boards).",
            "One learner explains today's idea in their own words.",
            "Homework: observe/describe one real-life example of today's technology at home or note one safety rule.",
            "Preview next Computing lesson; remind learners of responsible/ethical ICT use.",
        ]
    elif key == "social_studies":
        starter = [
            "Greet learners; brief 'community minute': one thing that happened in our community this week.",
            f"Show {media} linked to today's issue; ask 'What is happening here? Have you seen this before?'",
            f"NEW TODAY (Week {week}): In Social Studies we {ind_l}",
            "Introduce key concepts; learners give local examples.",
        ]
        main = [
            f"ACTIVITY 1 (Present the issue \u2013 5 min): Teacher presents the topic using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Guided inquiry \u2013 5 min): Think-pair-share on 3 guiding questions (What? Why? How does it affect us?).",
            f"ACTIVITY 3 (Group task \u2013 5 min): Learners {task} on {ss}.",
            "ACTIVITY 4 (Report \u2013 3 min): Groups present; teacher links to national values, citizenship and sustainable development.",
        ]
        plenary = [
            "Consensus round: class agrees on 2 key takeaways.",
            "Ask: 'What can YOU do about this as a young citizen?'",
            "Homework: ask a parent/elder one question about today's issue; note the answer.",
            "Preview next Social Studies lesson.",
        ]
    elif key == "career_technology":
        starter = [
            "Greet learners; 1-minute 'trade talk': name a tool, food or craft you saw at home or in the market.",
            f"Show {media} linked to today's lesson; ask 'What is this used for? Who uses it?'",
            f"NEW TODAY (Week {week}): In Career Technology we {ind_l}",
            "Introduce key terms and safety rules for today's tools/materials.",
        ]
        main = [
            f"ACTIVITY 1 (Demonstration \u2013 5 min): Teacher demonstrates the process/skill using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Guided practice \u2013 5 min): Learners handle tools/materials step-by-step under supervision; safety emphasised.",
            f"ACTIVITY 3 (Production task \u2013 5 min): Learners {task} on {ss}.",
            "ACTIVITY 4 (Review \u2013 3 min): Display of work; peers check quality against the steps; teacher gives corrective feedback.",
        ]
        plenary = [
            "Exit question: each learner states one step or safety rule from today.",
            "Link lesson to careers: 'Which jobs use this skill in our district?'",
            "Homework: gather listed local materials for the next practical lesson / ask a craftsperson one question.",
            "Preview next Career Technology lesson.",
        ]
    elif key == "creative_arts_design":
        starter = [
            "Greet learners with a creative warm-up clap / body percussion.",
            f"Show {media}; ask 'What do you see? Which ideas can you borrow from it?'",
            f"NEW TODAY (Week {week}): In Creative Arts and Design we {ind_l}",
            "Introduce tools/materials and safety; display the design brief for the session.",
        ]
        main = [
            f"ACTIVITY 1 (Demonstration \u2013 5 min): Teacher models the technique/design step using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Guided practice \u2013 5 min): Learners practise the technique in pairs; teacher scaffolds.",
            f"ACTIVITY 3 (Creative making \u2013 5 min): Learners {task} on {ss}.",
            "ACTIVITY 4 (Showcase \u2013 3 min): Mini gallery walk / display; peer appreciation ('two stars and a wish'); teacher feedback on creativity and craftsmanship.",
        ]
        plenary = [
            "Clean-up routine \u2013 tidy tools and materials.",
            "Reflection: 'What inspired your design? What would you improve?'",
            "Homework: collect natural/found materials or finish sketchbook ideas.",
            "Preview next Design/Creative Arts lesson.",
        ]
    elif key == "french":
        starter = [
            "Greet learners in French ('Bonjour la classe!') and sing a short French greeting song.",
            f"Show {media} linked to today's topic; ask 'Que voyez-vous?' (What do you see?)",
            f"NEW TODAY (Semaine {week}): Aujourd'hui nous {ind_l}",
            "Drill 4-6 new French words chorally (repeat, gesture, point).",
        ]
        main = [
            f"ACTIVITY 1 (Model \u2013 5 min): Teacher models the language using {media} \u2013 {ind_l}",
            "ACTIVITY 2 (Répétition guidée \u2013 5 min): Whole class repeats; rows/groups take turns; teacher corrects pronunciation.",
            f"ACTIVITY 3 (Pair/Group practice \u2013 5 min): Learners {task} using the new words ({ss}).",
            "ACTIVITY 4 (Performance \u2013 3 min): 2-3 pairs perform the dialogue/answers; class applauds; teacher highlights good French.",
        ]
        plenary = [
            "Exit question: every learner says one French word/sentence from today.",
            "Quick game: 'Montrez-moi...' (point to flashcard) for recall.",
            "Homework: teach today's French words to someone at home; write them twice in the exercise book.",
            "Preview next French lesson.",
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
            f"ACTIVITY 3 (Values Practice \u2013 5 min): Learners {task} showing the moral value in action ({ss}).",
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

def slot_group(slot, week):
    if isinstance(slot, list):
        return slot[0] if week % 2 == 1 else slot[1]
    return slot

def build_one(g, subj):
    path = f"{DBDIR}/{subj['sid']}_{g}_curriculum_db_clean.json"
    with open(path) as f:
        cur_db = json.load(f)
    codes = sorted(cur_db.keys(), key=lambda x: [int(p) for p in x.replace('B', '').split('.')])
    strand_groups = defaultdict(list)
    for code in codes:
        p = code.split('.')
        strand_groups[f"{p[0]}.{p[1]}"].append(code)
    strand_groups = {k: sorted(v) for k, v in strand_groups.items()}
    lessons_raw = []
    n = 1
    if subj["week_plan"] is None:
        all_codes = [c for sc in sorted(strand_groups) for c in strand_groups[sc]]
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
        needed = {slot_group(s, w) for _, s in subj["week_plan"] for w in range(1, 13)}
        missing = needed - set(strand_groups)
        assert not missing, f"{subj['key']} {g}: strands missing in DB: {missing}"
        strand_iters = {sc: cycle(strand_groups[sc]) for sc in strand_groups}
        for term in (1, 2, 3):
            for week in range(1, 13):
                for day_name, slot in subj["week_plan"]:
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
    out = f"{subj['key']}_{g.lower()}_lessons_enriched.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=1, ensure_ascii=False)
    dist = Counter(l["ind_code"] for l in lessons_raw)
    top, lo = dist.most_common(1)[0], dist.most_common()[-1]
    print(f"OK {g} {subj['name']}: {len(enriched)} lessons | {len(dist)} indicators | spread {lo[1]}..{top[1]}")

if __name__ == "__main__":
    for g in ("B8", "B9"):
        for s in GRADES[g]:
            build_one(g, s)
