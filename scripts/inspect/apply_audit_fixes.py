#!/usr/bin/env python3
"""Apply corrections found by the B1-B9 verification audit.

1. creative-arts_B3 : REMOVE 2 phantom indicators not present in the NaCCA PDF
2. 6 DB files       : ADD 10 real indicators (official text extracted from PDFs)
3. english B1 DB    : fill 69 empty assessment fields (style-consistent default)
4. summary JSONs    : recompute counts for the 7 changed DB files
5. math enriched    : restore missing cs_desc on lesson 149 from the DB
6. english enriched : propagate DB assessments into lessons with empty assessment
Originals of every modified file are backed up to audit_backup/.
"""
# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json, os, shutil, re
from collections import OrderedDict

ROOT = str(Path(__file__).resolve().parents[2])
BK = os.path.join(ROOT, 'audit_backup')
os.makedirs(BK, exist_ok=True)
log = []

def backup(path):
    dst = os.path.join(BK, os.path.basename(path))
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
        log.append(f'backup: {os.path.basename(path)}')

def save(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def db_file(sid, g):
    if g == 'B1':
        alias = {'mathematics': 'math', 'science': 'science', 'english-language': 'english',
                 'ghanaian-language': 'ghanaian_language', 'history': 'history', 'owop': 'owop',
                 'rme': 'rme', 'creative-arts': 'creative_arts'}
        return os.path.join(ROOT, f'{alias[sid]}_curriculum_db_clean.json')
    return os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')

def new_entry(db, code, subject_label, ind_desc, ccp=False, strand_name=None):
    """Build a new DB entry in the same house style as the file it joins."""
    parts = code.split('.')                      # B3.2.2.1.1
    g, s, ss = parts[0], parts[1], parts[2]
    cs = '.'.join(parts[:4])
    tmpl = next(iter(db.values()))
    # reuse the real strand name of an existing same-strand entry when available
    strand = strand_name
    if strand is None:
        same = [v['strand'] for k, v in db.items() if k.startswith(f'{g}.{s}.')]
        strand = same[0] if same else tmpl['strand']
    mid = ' CCP' if 'CCP' in tmpl['cs_desc'] else ''
    return {
        'strand': strand,
        'sub_strand': f'Sub-strand {g}.{s}.{ss}',
        'cs_code': cs,
        'cs_desc': tmpl['cs_desc'].replace(tmpl['cs_code'], cs) if tmpl['cs_code'] in tmpl['cs_desc'] else f'{subject_label}{mid} Content Standard {cs}',
        'ind_desc': ind_desc,
        'competencies': tmpl['competencies'],
        'resources': tmpl['resources'],
        'keywords': tmpl['keywords'],
        'assessment': tmpl['assessment'],
    }

# ---------------------------------------------------------------- 1+2: DB fixes
DB_CHANGES = {
    ('creative-arts', 'B3'): {
        'remove': ['B3.1.2.2.4', 'B3.2.2.2.4'],
        'add': {},  # phantom codes fabricated by DB build; sub-strands end at .3 in the PDF
    },
    ('history', 'B3'): {'remove': [], 'add': {
        'B3.2.2.1.1': 'Discuss the nature of exchanges among the ethnic groups.'}},
    ('rme', 'B2'): {'remove': [], 'add': {
        'B2.2.1.1.2': 'Sing and recite simple texts from the three main religions in Ghana.'}},
    ('rme', 'B3'): {'remove': [], 'add': {
        'B3.2.1.1.2': 'Give reasons for studying the sacred scriptures of the three major religions among their followers.',
        'B3.2.2.1.2': 'Demonstrate the importance of religious festivals.',
        'B3.4.1.1.2': 'Identify the benefits of responding to God\u2019s call.'}},
    ('ghanaian-language', 'B5'): {'remove': [], 'add': {
        'B5.2.6.1.2': 'Answer factual and inferential questions.'}},
    ('mathematics', 'B8'): {'remove': [], 'add': {
        'B8.2.1.1.2': 'Calculate the gradient of a line and use it to write equation of a line of the form y = mx + c.',
        'B8.2.1.1.3': 'Use graph of a linear relation to determine subsequent missing elements in the ordered pairs of the relation.',
        'B8.2.1.1.4': 'Use graphs of linear relations to solve real life problems.'}},
    ('rme', 'B7'): {'remove': [], 'add': {
        'B7.1.1.1.3': 'Identify the similarities in the way that the nature of God is understood through His attributes in the three major religions in Ghana.'}},
}
SUBJECT_LABEL = {
    'creative-arts': 'Creative Arts', 'history': 'History', 'rme': 'Religious and Moral Education',
    'ghanaian-language': 'Ghanaian Language', 'mathematics': 'Mathematics',
}

changed_dbs = []
for (sid, g), ch in DB_CHANGES.items():
    p = db_file(sid, g)
    backup(p)
    db = json.load(open(p))
    for code in ch['remove']:
        if code in db:
            del db[code]
            log.append(f'REMOVE {code} from {os.path.basename(p)} (not in official NaCCA PDF)')
    for code, desc in ch['add'].items():
        if code not in db:
            db[code] = new_entry(db, code, SUBJECT_LABEL[sid], desc)
            log.append(f'ADD    {code} to {os.path.basename(p)} (official text from PDF)')
    save(p, db)
    changed_dbs.append((sid, g, p))

# ------------------------------------------------- 3: english B1 DB assessment fill
p = db_file('english-language', 'B1')
backup(p)
db = json.load(open(p))
DEFAULT_ASS = 'Oral questions and answers; short written exercise in exercise books; teacher observation with checklist'
filled = 0
for code, v in db.items():
    if not str(v.get('assessment', '')).strip():
        v['assessment'] = DEFAULT_ASS
        filled += 1
save(p, db)
log.append(f'FILL   {filled} empty assessment fields in english_curriculum_db_clean.json')

# ------------------------------------------------- 4: recompute summary counts
for sid, g, p in changed_dbs:
    db = json.load(open(p))
    sp = p.replace('_curriculum_db_clean.json', '_curriculum_summary.json')
    if not os.path.exists(sp):
        continue
    backup(sp)
    summ = json.load(open(sp))
    strands = sorted({k.rsplit('.', 1)[0] for k in db}, key=lambda x: [int(t) for t in x[1:].split('.')])
    strand_rows = []
    for st in strands:
        keys = [k for k in db if k.rsplit('.', 1)[0] == st]
        strand_rows.append(OrderedDict([
            ('code', st), ('name', st),
            ('subStrands', len({k.rsplit('.', 2)[0] for k in keys})),
            ('standards', len({db[k]['cs_code'] for k in keys})),
            ('indicators', len(keys)),
        ]))
    summ['counts'] = OrderedDict([
        ('strands', len(strand_rows)),
        ('subStrands', len({k.rsplit('.', 2)[0] for k in db})),
        ('standards', len({db[k]['cs_code'] for k in db})),
        ('indicators', len(db)),
    ])
    summ['strands'] = strand_rows
    save(sp, summ)
    log.append(f'COUNTS recomputed in {os.path.basename(sp)} (indicators={len(db)})')

# ------------------------------------------------- 5: math enriched lesson 149 cs_desc
p = os.path.join(ROOT, 'math_lessons_enriched.json')
backup(p)
lessons = json.load(open(p))
mdb = json.load(open(db_file('mathematics', 'B1')))
cs_lookup = {v['cs_code']: v['cs_desc'] for v in mdb.values()}
fixed = 0
for l in lessons:
    if not str(l.get('cs_desc', '')).strip() and l['cs_code'] in cs_lookup:
        l['cs_desc'] = cs_lookup[l['cs_code']]
        fixed += 1
save(p, lessons)
log.append(f'FIX    {fixed} empty cs_desc in math_lessons_enriched.json (from Math DB)')

# ------------------------------------------------- 6: english enriched assessments
p = os.path.join(ROOT, 'english_lessons_enriched.json')
backup(p)
lessons = json.load(open(p))
edb = json.load(open(db_file('english-language', 'B1')))
fixed = 0
for l in lessons:
    if not str(l.get('assessment', '')).strip():
        v = edb.get(l['ind_code'], {})
        l['assessment'] = v.get('assessment', DEFAULT_ASS)
        fixed += 1
save(p, lessons)
log.append(f'FIX    {fixed} empty assessment in english_lessons_enriched.json (from English DB)')

print('\n'.join(log))
json.dump(log, open(os.path.join(ROOT, 'audit_fixes_log.json'), 'w'), indent=1)
print(f'\nTotal changes: {len(log)} (backups in audit_backup/)')
