import json, os
from collections import defaultdict, Counter
from itertools import cycle

subjects = [
    {"key":"history","db":"history_curriculum_db_clean.json","name":"History"},
    {"key":"owop","db":"owop_curriculum_db_clean.json","name":"Our World Our People"},
    {"key":"rme","db":"rme_curriculum_db_clean.json","name":"Religious and Moral Education"},
    {"key":"creative_arts","db":"creative_arts_curriculum_db_clean.json","name":"Creative Arts"},
]

def build_one(subj):
    with open(subj["db"]) as f:
        cur_db = json.load(f)
    codes = sorted(cur_db.keys(), key=lambda x: [int(p) if p.isdigit() else 0 for p in x.replace('B','').split('.')])
    print(f"{subj['key']}: {len(codes)} indicators")
    # group by strand
    strand_groups = defaultdict(list)
    for code in codes:
        parts = code.split('.')
        strand = f"{parts[0]}.{parts[1]}"
        strand_groups[strand].append(code)
    strand_list = sorted(strand_groups.keys())
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday"]
    # map weekdays to strands round-robin
    week_plan = []
    extended = (strand_list*5)[:5]
    if len(extended) < 5:
        extended = extended + [strand_list[0]]*(5-len(extended))
    for i,day in enumerate(days):
        week_plan.append((day, extended[i], i+1))
    print("  week_plan", week_plan)
    strand_iters = {sc: cycle(strand_groups[sc]) for sc in strand_groups}
    lessons_raw = []
    lesson_num=1
    for term in [1,2,3]:
        for week in range(1,13):
            for day_name, strand_code, strand_num in week_plan:
                if strand_code not in strand_iters:
                    strand_code = next(iter(strand_iters))
                ind_code = next(strand_iters[strand_code])
                lessons_raw.append({"lesson_num":lesson_num,"term":term,"week":week,"day":day_name,"strand_num":strand_num,"strand_code":strand_code,"ind_code":ind_code,"is_revision":False})
                lesson_num+=1
    ind_counts = Counter([l["ind_code"] for l in lessons_raw])
    ind_current = Counter()
    enriched=[]
    # activity templates per subject
    def get_act(meta, session_num, total_sessions, day_name):
        strand = meta.get("strand","")
        sub_strand = meta.get("sub_strand","")
        ind_desc = meta.get("ind_desc","")
        k = subj["key"]
        if k=="history":
            starter=[f"Greet learners. Sing Ghana National Anthem / patriotic song.","Show picture related to "+sub_strand.lower()+". Ask 'What do you see?'",f"NEW TODAY: Today in History we learn about {sub_strand.lower()}.","Write key words on board, read chorally."]
            main=[f"ACTIVITY 1 (Modelling – 5 min): Teacher tells the historical story / shows timeline / artefacts – {ind_desc[:100]}","ACTIVITY 2 (Guided Discussion – 5 min): Turn-and-talk in pairs, answer 3 probing questions, whole-class share.","ACTIVITY 3 (Group Task – 7 min): Sort picture cards / sequence timeline / draw / role-play related to "+sub_strand.lower()+".","ACTIVITY 4 (Share – 3 min): Groups present, teacher links to Ghanaian identity and values."]
            plenary=["Recite 2 key facts – call and response.","Ask: 'Why is this important for us as Ghanaians?'","Homework: Ask an elder at home, bring 1 sentence.","Preview next History lesson."]
        elif k=="owop":
            starter=[f"Greet with OWOP community song. Check-in feelings.","Show real object / picture for "+sub_strand.lower()+".","NEW TODAY: 'In Our World Our People we explore "+sub_strand.lower()+".'","Introduce keywords, echo chorally."]
            main=[f"ACTIVITY 1 (Modelling – 5 min): Teacher models real-life context – {ind_desc[:80]}","ACTIVITY 2 (Guided Exploration – 5 min): Pairs explore pictures / case stories, discuss values.","ACTIVITY 3 (Collaborative – 7 min): Groups make mini-poster / role-play / community map – "+sub_strand.lower()+".","ACTIVITY 4 (Sharing – 3 min): Showcase, peer appreciation, teacher reinforces citizenship competencies."]
            plenary=["Pupils state 1 learning + 1 action at home/school.","Sing citizenship pledge song.","Homework: Talk to family, draw 1 action.","Preview next OWOP."]
        elif k=="rme":
            starter=["Greet peacefully. Open with inter-faith prayer / moment of silence / moral song (Christian-Islamic-Traditional inclusive).",f"Show moral picture linked to {sub_strand.lower()}.","NEW TODAY: 'R.M.E. – "+ind_desc[:70]+"'","Introduce key moral vocabulary."]
            main=[f"ACTIVITY 1 (Story/Scripture – 5 min): Teacher shares moral story / text / proverb – {ind_desc.lower()}","ACTIVITY 2 (Guided Discussion – 5 min): Think-pair-share – how does this help at home/school?","ACTIVITY 3 (Values Practice – 7 min): Role-play good moral choice / draw right-behaviour poster / sort right-wrong cards – "+sub_strand.lower()+".","ACTIVITY 4 (Reflection – 3 min): Groups share. Teacher affirms honesty, respect, tolerance, love – Christian, Islamic, ATR perspectives."]
            plenary=["Recite golden rule / memory verse / wise saying.","Ask: 'What will you do differently?'","Homework: Share moral lesson with family, do 1 good deed.","Close with inclusive prayer/song."]
        elif k=="creative_arts":
            starter=["Greet with creative warm-up clap / body percussion.","Show artwork / instrument / movement – "+sub_strand.lower()+".","NEW TODAY: Creative Arts – "+ind_desc[:70],"Introduce tools/materials safely."]
            main=["ACTIVITY 1 (Demonstration – 5 min): Teacher models creative skill – drawing / painting / modelling / singing / drumming / dance / drama.","ACTIVITY 2 (Guided Practice – 5 min): Pupils practise in pairs/small groups, teacher scaffolds, safe tidy workspace.","ACTIVITY 3 (Creative Making – 7 min): Pupils create own artwork/performance – "+sub_strand.lower()+".","ACTIVITY 4 (Showcase – 3 min): Gallery walk / mini performance. Peer appreciation. Teacher feedback on creativity & craftsmanship."]
            plenary=["Clean-up song – tidy tools.","Reflection: 'What did you enjoy? What was challenging?'","Homework: Finish artwork / practise song/dance at home.","Preview next Visual / Performing rotation."]
        else:
            starter=["Greet learners.","Activate prior knowledge.","State today's focus.","Write keywords."]
            main=["Teacher models.","Guided practice.","Group task.","Sharing."]
            plenary=["Recap.","Share takeaway.","Homework.","Preview next."]
        # session titles
        if session_num==1:
            session_title=f"Session {session_num} of {total_sessions} — Introduction"
        elif session_num==total_sessions:
            session_title=f"Session {session_num} of {total_sessions} — Consolidation"
        else:
            session_title=f"Session {session_num} of {total_sessions} — Practice"
        perf_indicator=f"By the end of the lesson, learners will be able to: {ind_desc.lower()}"
        return {"session_title":session_title,"perf_indicator":perf_indicator,"starter":starter,"main":main,"plenary":plenary}
    for l in lessons_raw:
        code=l["ind_code"]
        meta=cur_db.get(code)
        if not meta:
            meta=next(iter(cur_db.values()))
        ind_current[code]+=1
        session_num=ind_current[code]
        total_sessions=ind_counts[code]
        act=get_act(meta, session_num, total_sessions, l["day"])
        rpk_map={
            "history":"Learners have listened to stories from elders, seen national symbols, celebrated national days.",
            "owop":"Learners interact daily with family, school, community, and environment – KG foundations.",
            "rme":"Learners pray/worship with family (Christian/Islamic/Traditional), know basic moral rules.",
            "creative_arts":"Learners sing, dance, draw, colour, mould, and play drama informally at home and KG."
        }
        enriched.append({
            "lesson_num":l["lesson_num"],"term":l["term"],"week":l["week"],"day":l["day"],
            "strand_num":l["strand_num"],
            "strand_name":meta.get("strand",""),
            "sub_strand":meta.get("sub_strand",""),
            "cs_code":meta.get("cs_code",""),
            "cs_desc":meta.get("cs_desc",""),
            "ind_code":code,
            "ind_desc":meta.get("ind_desc",""),
            "is_revision":False,
            "session_title":act["session_title"],
            "perf_indicator":act["perf_indicator"],
            "competencies":meta.get("competencies","Critical Thinking and Problem Solving; Communication and Collaboration; Creativity and Innovation; Cultural Identity and Global Citizenship; Personal Development and Leadership; Digital Literacy"),
            "resources":meta.get("resources","NaCCA approved textbook; pictures; realia; ICT tools"),
            "keywords":meta.get("keywords",subj["key"]),
            "rpk":rpk_map.get(subj["key"],"Prior everyday experience."),
            "starter":act["starter"],
            "main":act["main"],
            "plenary":act["plenary"],
            "assessment":meta.get("assessment","Observation; oral questions; class exercise")
        })
    out_path=f"{subj['key']}_lessons_enriched.json"
    with open(out_path,"w",encoding="utf-8") as out:
        json.dump(enriched,out,indent=2,ensure_ascii=False)
    print(f"✅ {subj['name']} → {len(enriched)} lessons → {out_path}")
    return out_path

if __name__=="__main__":
    for s in subjects:
        build_one(s)
