import json, os
from collections import defaultdict, Counter
from itertools import cycle

subjects = [
    {"key":"history","db":"history_curriculum_db_clean.json","name":"History","subject_label":"History","period":30},
    {"key":"owop","db":"owop_curriculum_db_clean.json","name":"Our World Our People","subject_label":"Our World Our People","period":30},
    {"key":"rme","db":"rme_curriculum_db_clean.json","name":"Religious and Moral Education","subject_label":"Religious and Moral Education","period":30},
    {"key":"creative_arts","db":"creative_arts_curriculum_db_clean.json","name":"Creative Arts","subject_label":"Creative Arts","period":60},
]

def build_lessons(subj):
    with open(subj["db"]) as f:
        cur_db=json.load(f)
    codes=list(cur_db.keys())
    # sort naturally
    def sort_key(c):
        return [int(x) if x.isdigit() else 0 for x in c.replace('B','').split('.')]
    codes=sorted(codes, key=sort_key)
    print(f"{subj['key']}: {len(codes)} indicators")
    # group by strand for weekday mapping if possible
    strand_groups=defaultdict(list)
    for code in codes:
        parts=code.split('.')
        strand=f"{parts[0]}.{parts[1]}"
        strand_groups[strand].append(code)
    strand_list=sorted(strand_groups.keys())
    print("  strands:", strand_list)
    # build week_plan: map Mon-Fri to strands cyclically, fill up to 5
    days=["Monday","Tuesday","Wednesday","Thursday","Friday"]
    week_plan=[]
    # if >=5 strands, take first 5, else repeat
    extended_strands = (strand_list*3)[:5]
    if len(extended_strands)<5:
        extended_strands = extended_strands + [strand_list[0]]*(5-len(extended_strands))
    for i, day in enumerate(days):
        sc = extended_strands[i] if i < len(extended_strands) else strand_list[0]
        week_plan.append((day, sc, i+1))
    print("  week_plan:", week_plan)
    # create iterators per strand
    strand_iters={sc: cycle(strand_groups[sc]) for sc in strand_groups}
    # also create a global fallback cycle for strands not mapped? already covered
    lessons_raw=[]
    lesson_num=1
    for term in [1,2,3]:
        for week in range(1,13):
            for day_name, strand_code, strand_num in week_plan:
                # if strand_code not in strand_iters (shouldn't happen), pick first
                if strand_code not in strand_iters:
                    strand_code = list(strand_iters.keys())[0]
                ind_code = next(strand_iters[strand_code])
                lessons_raw.append({
                    "lesson_num": lesson_num,
                    "term": term,
                    "week": week,
                    "day": day_name,
                    "strand_num": strand_num,
                    "strand_code": strand_code,
                    "ind_code": ind_code,
                    "is_revision": False
                })
                lesson_num+=1
    # count occurrences
    ind_counts=Counter([l["ind_code"] for l in lessons_raw])
    ind_current=Counter()
    enriched=[]
    # activity generator – generic but subject-aware
    def get_activities(ind_code, meta, session_num, total_sessions, day_name):
        strand = meta.get("strand","")
        sub_strand = meta.get("sub_strand","")
        ind_desc = meta.get("ind_desc","")
        keywords = meta.get("keywords", subj["key"])
        subject_name = subj["name"]
        if session_num==1:
            session_title = f"Session {session_num} of {total_sessions} — Introduction"
            perf_indicator = f"By the end of the lesson, learners will be able to explore: {ind_desc.lower()}"
        elif session_num==total_sessions:
            session_title = f"Session {session_num} of {total_sessions} — Consolidation & Assessment"
            perf_indicator = f"By the end of the lesson, learners will be able to demonstrate understanding of: {ind_desc.lower()}"
        else:
            session_title = f"Session {session_num} of {total_sessions} — Practice & Deepening"
            perf_indicator = f"By the end of the lesson, learners will be able to practice: {ind_desc.lower()}"
        # generic starter tailored by subject
        if subj["key"]=="history":
            starter = [
                f"Greet learners warmly. Sing the Ghana National Anthem first verse / a patriotic call-and-response.",
                f"Show a picture/flashcard related to {sub_strand.lower()}. Ask: 'What do you see? What do you know?'",
                f"NEW TODAY: 'Today in {subject_name} we will learn about {sub_strand.lower()}.'",
                f"Write key words on the board: {keywords.split(',')[0].strip()}. Read chorally, in groups, individually."
            ]
            main = [
                f"ACTIVITY 1 (Teacher Modelling – 5 min): Teacher narrates / demonstrates the historical concept '{ind_desc[:80]}...' using story-telling, timeline chart, pictures, or artefacts. Pupils listen attentively.",
                f"ACTIVITY 2 (Guided Discussion – 5 min): Teacher asks 3–4 probing questions. Pupils turn-and-talk in pairs, then share whole-class. Teacher clarifies misconceptions, reinforces chronology / cause-effect.",
                f"ACTIVITY 3 (Group Task – 7 min): In mixed-ability groups, pupils: sort picture cards / sequence events on a timeline / draw and label / role-play a short historical scene related to {sub_strand.lower()}.",
                f"ACTIVITY 4 (Presentation & Feedback – 3 min): 1–2 groups present. Teacher summarises key points, links to Ghanaian identity, values, and patriotism."
            ]
            plenary = [
                "Whole class recites 2 key facts learned today – call and response.",
                "Ask: 'Why is this important for us as Ghanaians?' – 2 pupils respond.",
                "Homework: 'Ask an elder at home what they know about today's topic. Bring 1 sentence tomorrow.'",
                "Preview next History lesson."
            ]
        elif subj["key"]=="owop":
            starter = [
                f"Greet learners with a cheerful OWOP community song / clap. Quick 'How are we feeling today?' check-in with emojis.",
                f"Show a real object / picture linked to {sub_strand.lower()}. Ask pupils to observe, touch, describe in Mother Tongue then English.",
                f"NEW TODAY: 'In Our World Our People today we explore {sub_strand.lower()}.'",
                f"Introduce keywords: {keywords}. Echo chorally."
            ]
            main = [
                f"ACTIVITY 1 (Modelling – 5 min): Teacher models using real-life context, dramatisation, or community walk photo/video – connecting {ind_desc.lower()}.",
                f"ACTIVITY 2 (Guided Exploration – 5 min): Pupils in pairs explore pictures / objects / simple case stories. Teacher prompts with open questions to elicit values, attitudes, skills.",
                f"ACTIVITY 3 (Collaborative Task – 7 min): Small groups create a mini-poster / role-play / sorting game / community map showing understanding of {sub_strand.lower()}. Emphasise respect, inclusivity, Ghanaian values.",
                f"ACTIVITY 4 (Sharing – 3 min): Groups showcase. Peer appreciation – 2 stars and 1 wish. Teacher reinforces core competencies: communication, cultural identity, citizenship."
            ]
            plenary = [
                "Pupils state 1 thing they learned and 1 thing they will do at home/school.",
                "Sing closing values song / recite class citizenship pledge.",
                "Homework: 'Talk to your family / community helper about today's topic. Draw / tell 1 action you will take.'",
                "Preview next OWOP strand."
            ]
        elif subj["key"]=="rme":
            starter = [
                "Greet learners peacefully. Open with a short inter-faith prayer / moment of silence / song on moral values (Christian – Islamic – Traditional inclusive).",
                f"Show a moral picture / object related to {sub_strand.lower()}. Ask: 'What good behaviour do you see?'",
                f"NEW TODAY: 'In R.M.E. today we learn: {ind_desc[:70]}...'",
                f"Introduce key moral/religious vocabulary: {keywords.split(',')[0].strip()}."
            ]
            main = [
                f"ACTIVITY 1 (Story / Scripture / Modelling – 5 min): Teacher shares a short moral story / religious text / proverb illustrating {ind_desc.lower()}. Models reverence, respect for all three major religions in Ghana.",
                f"ACTIVITY 2 (Guided Discussion – 5 min): Think-pair-share: 'How does this teaching help us at home / school?' Pupils discuss in pairs, teacher facilitates inclusive dialogue.",
                f"ACTIVITY 3 (Values Practice – 7 min): In small groups – role-play a good moral choice, draw a poster showing right behaviour, or sort 'right / wrong' picture cards linked to {sub_strand.lower()}.",
                f"ACTIVITY 4 (Reflection – 3 min): 2 groups share. Teacher affirms positive values – honesty, respect, obedience, tolerance, love, patriotism – linking Christian, Islamic and African Traditional perspectives."
            ]
            plenary = [
                "Whole class recites a golden rule / memory verse / traditional wise saying related to the lesson.",
                "Ask: 'What will you do differently this week because of what we learned?' – 2–3 pupils.",
                "Homework / Family: 'Share today’s moral lesson with your family. Practise one good deed.'",
                "Close with a short prayer / song of thanks – inclusive."
            ]
        elif subj["key"]=="creative_arts":
            starter = [
                "Greet learners with a creative warm-up clap / body percussion / call-and-response art chant.",
                f"Show an artwork / instrument / dance movement linked to {sub_strand.lower()}. Ask pupils to observe colours, shapes, sounds, movements.",
                f"NEW TODAY: 'In Creative Arts today: {ind_desc[:70]}...'",
                f"Introduce tools/materials safely: {keywords.split(',')[0].strip()}."
            ]
            main = [
                f"ACTIVITY 1 (Demonstration – 5 min): Teacher models the creative skill – e.g., drawing, colour mixing, modelling with clay, singing, drumming pattern, dance step, drama role – thinking aloud.",
                f"ACTIVITY 2 (Guided Practice – 5 min): Pupils practise in pairs / small groups with teacher scaffolding – explore tools, try techniques, keep a safe and tidy workspace.",
                f"ACTIVITY 3 (Creative Making – 7 min): Individually / groups – pupils create their own artwork / performance based on {sub_strand.lower()} – e.g., draw, paint, model, compose a 4-beat rhythm, choreograph 8-count movement, rehearse a short skit.",
                f"ACTIVITY 4 (Gallery Walk / Showcase – 3 min): Display works / mini performance. Peer appreciations – 'I like … because …'. Teacher gives specific positive feedback on creativity, craftsmanship, collaboration."
            ]
            plenary = [
                "Clean-up song – 1 minute – pupils return tools, wash hands, tidy tables.",
                "Reflection circle: 'What did you enjoy creating today? What was challenging?'",
                "Homework / Extension: 'Finish colouring / practise your song / dance / lines at home. Bring found materials next lesson.'",
                "Preview next Creative Arts strand – Visual ↔ Performing rotation."
            ]
        else:
            # generic fallback
            starter = [f"Greet learners. Introduce {subject_name} – {sub_strand}.", "Activate prior knowledge with quick Q&A.", f"State today's focus: {ind_desc[:80]}", "Write keywords on board."]
            main = ["Teacher models concept.", "Guided practice in pairs.", "Group hands-on task.", "Sharing and teacher feedback."]
            plenary = ["Recap key learning.", "Pupils share 1 takeaway.", "Homework assigned.", "Preview next lesson."]
        return {"session_title":session_title,"perf_indicator":perf_indicator,"starter":starter,"main":main,"plenary":plenary}
    # enrich loop
    for l in lessons_raw:
        code=l["ind_code"]
        meta=cur_db.get(code)
        if not meta:
            # fallback first entry
            meta=next(iter(cur_db.values()))
        ind_current[code]+=1
        session_num=ind_current[code]
        total_sessions=ind_counts[code]
        act=get_activities(code, meta, session_num, total_sessions, l["day"])
        # RPK generic per subject
        rpk_map={
            "history":"Learners have listened to stories from elders, seen national symbols (flag, Coat of Arms), celebrated national days, and visited community historical sites in KG / home.",
            "owop":"Learners interact daily with family, school, community, nature, technology, and have basic awareness of personal hygiene, safety, Ghanaian values, and the environment from KG.",
            "rme":"Learners pray / worship with family (Christian / Islamic / Traditional), know basic moral rules (respect elders, greetings, honesty) from home and KG.",
            "creative_arts":"Learners sing, dance, clap, draw, colour, mould clay, and play drama games informally at home, in KG, church/mosque, and community festivals."
        }
        rpk=rpk_map.get(subj["key"],"Learners have relevant previous experiences from KG and everyday life.")
        enriched.append({
            "lesson_num": l["lesson_num"],
            "term": l["term"],
            "week": l["week"],
            "day": l["day"],
            "strand_num": l["strand_num"],
            "strand_name": meta.get("strand",""),
            "sub_strand": meta.get("sub_strand",""),
            "cs_code": meta.get("cs_code",""),
            "cs_desc": meta.get("cs_desc",""),
            "ind_code": code,
            "ind_desc": meta.get("ind_desc",""),
            "is_revision": False,
            "session_title": act["session_title"],
            "perf_indicator": act["perf_indicator"],
            "competencies": meta.get("competencies","Critical Thinking and Problem Solving; Communication and Collaboration; Creativity and Innovation; Cultural Identity and Global Citizenship; Personal Development and Leadership; Digital Literacy"),
            "resources": meta.get("resources","NaCCA approved textbook; pictures; realia; ICT tools"),
            "keywords": meta.get("keywords",subj["key"]),
            "rpk": rpk,
            "starter": act["starter"],
            "main": act["main"],
            "plenary": act["plenary"],
            "assessment": meta.get("assessment","Observation; oral questions; class exercise")
        })
    out_path = f"{subj['key']}_lessons_enriched.json"
    with open(out_path,"w",encoding="utf-8") as out:
        json.dump(enriched,out,indent=2,ensure_ascii=False)
    print(f"{subj['name']} -> {len(enriched)} lessons -> {out_path}")
    return out_path

if __name__ == "__main__":
    for s in subjects:
        # reset per-subject globals that build_lessons uses internally? build_lessons defines its own locals, fine
        build_lessons(s)
