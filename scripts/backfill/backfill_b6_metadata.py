#!/usr/bin/env python3
"""Backfill B6 Core-4 DBs (math, science, english, ghanaian) with authentic NaCCA
text from the Upper Primary PDFs. All grabs GRADE-SCOPED to BASIC 6 body slices."""
# --- resolve bare data filenames against data/ (see tools/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[2] / "tools"))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json, os, re, shutil, gzip, hashlib

ROOT = str(Path(__file__).resolve().parents[2])
CACHE = os.path.join(ROOT, 'pdf_text_cache')
BK = os.path.join(ROOT, 'audit_backup')

def text_of(pdf):
    h = hashlib.md5(pdf.encode()).hexdigest()[:10]
    p = os.path.join(CACHE, f'{h}.txt.gz')
    if not os.path.exists(p):
        from pypdf import PdfReader
        t = '\n'.join((pg.extract_text() or '') for pg in PdfReader(pdf).pages)
        with gzip.open(p, 'wt', encoding='utf-8') as f:
            f.write(t)
        return t
    with gzip.open(p, 'rt', encoding='utf-8', errors='ignore') as f:
        return f.read()

def code_rx(code):
    parts = code.split('.')
    return ('B' + r'\s*' + re.escape(parts[0][1]) + r'\s*[.\s]\s*'
            + r'\s*[.\s]\s*'.join(re.escape(x) for x in parts[1:])
            + r'(?![.\s]*\d)')

BOUNDARY = re.compile(
    r'\uf0b7|\u2022|E\.\s?g|E\.G|Enquiry route|CORE COMPETENCIES|Core Competencies|Exemplar'
    r'|B\s*\d\s*[.\s]\s*\d+(?:\s*[.\s]\s*\d+){2,4}')

def grab(t, code, minlen=15, maxscan=420):
    best = ''
    for m in list(re.finditer(code_rx(code), t))[:8]:
        seg = t[m.end():m.end() + maxscan]
        bm = BOUNDARY.search(seg)
        seg = seg[:bm.start()] if bm else seg
        seg = re.sub(r'\s+', ' ', seg).strip(' :.-\u2013\t')
        if len(seg) > len(best):
            best = seg
    return best if len(best) >= minlen else ''

COMP_PAT = re.compile(r'\s*(Communication and Collaboration|Critical Thinking and Problem Solving'
                      r'|Personal Development and Leadership|Creativity and Innovation'
                      r'|Cultural Identity and Global Citizenship|Digital Literacy)\s*\d*\s*$')
CONTAM = re.compile(r'(©\s*NaCCA.*|CONTENT STANDARDS.*|SUBJECT SPECIFIC.*|INDICATORS AND EXEMPLARS.*)$')

def clean_desc(d):
    d = CONTAM.sub('', d).strip(' .|')
    while True:
        m = COMP_PAT.search(d)
        if not m:
            break
        d = d[:m.start()].rstrip(' .|')
    return d

BODIES = {
    'mathematics_B4-B6.pdf': (192017, None),
    'science_B4-B6.pdf': (113742, None),
    'english_B4-B6.pdf': (256501, None),
    'ghanaian_language_B4-B6.pdf': (170461, None),
}

JOBS = [
    ('mathematics', 'B6', 'mathematics_B4-B6.pdf', {
        1: '1. NUMBER', 2: '2. ALGEBRA', 3: '3. GEOMETRY AND MEASUREMENT', 4: '4. DATA'}),
    ('science', 'B6', 'science_B4-B6.pdf', {
        1: '1. DIVERSITY OF MATTER', 2: '2. CYCLES', 3: '3. SYSTEMS',
        4: '4. FORCES AND ENERGY', 5: '5. HUMANS AND THE ENVIRONMENT'}),
    ('english-language', 'B6', 'english_B4-B6.pdf', {
        1: '1. ORAL LANGUAGE', 2: '2. READING',
        3: '3. GRAMMAR USAGE AT WORD AND PHRASE LEVELS', 4: '4. WRITING',
        5: '5. USING WRITING CONVENTIONS/ GRAMMAR USAGE', 6: '6. EXTENSIVE READING'}),
    ('ghanaian-language', 'B6', 'ghanaian_language_B4-B6.pdf', {
        1: '1. ORAL LANGUAGE (LISTENING AND SPEAKING)', 2: '2. READING', 3: '3. WRITING',
        4: '4. COMPOSITION WRITING', 5: '5. WRITING CONVENTIONS/ USAGE',
        6: "6. EXTENSIVE READING/CHILDREN\u2019S LITERATURE/ LIBRARY"}),
]

report = []
for sid, g, pdf, strand_map in JOBS:
    full = text_of(pdf)
    s, e = BODIES[pdf]
    scope = full[s:e if e else len(full)]
    path = os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')
    bak = os.path.join(BK, os.path.basename(path) + '.pre_b6backfill')
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    db = json.load(open(path))
    zero_hits = [c for c in db if not re.search(code_rx(c), scope)]
    n_ind = n_cs = n_str = 0
    misses = []
    for code, v in db.items():
        cur = str(v.get('ind_desc', ''))
        if f'Learning Indicator {code}' in cur or cur.strip() == '':
            new = grab(scope, code)
            if new:
                new = clean_desc(new)
                if len(new) >= 14:
                    v['ind_desc'] = new
                    n_ind += 1
                else:
                    misses.append(('ind', code))
            else:
                misses.append(('ind', code))
        cs = v.get('cs_code', '')
        cur_cs = str(v.get('cs_desc', ''))
        if cs and (f'Content Standard {cs}' in cur_cs or cur_cs.strip() == ''):
            new = grab(scope, cs, minlen=12, maxscan=260)
            if new:
                v['cs_desc'] = new
                n_cs += 1
            else:
                misses.append(('cs', cs))
        num = int(code.split('.')[1])
        target = strand_map.get(num)
        if target and v.get('strand') != target:
            v['strand'] = target
            n_str += 1
    for v in db.values():
        cs = str(v.get('cs_desc', ''))
        if re.search(r"CONT\s*['’]D", cs):
            v['cs_desc'] = re.sub(r"CONT\s*['’]D.*$", '', cs).strip().rstrip('.,;')
            if not v['cs_desc'].endswith('.'):
                v['cs_desc'] += '.'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    report.append((sid, g, len(db), n_ind, n_cs, n_str, misses, zero_hits))

for sid, g, n, i, c, s, misses, zero_hits in report:
    print(f"== {sid} {g}: indicators={n} | ind backfilled={i} | cs backfilled={c} | strands set={s}")
    if zero_hits:
        print(f"   ? ZERO hits in B6 body (artifact candidates): {zero_hits}")
    if misses:
        ind_m = [c2 for t2, c2 in misses if t2 == 'ind']
        cs_m = sorted({c2 for t2, c2 in misses if t2 == 'cs'})
        print(f"   ! ind misses ({len(ind_m)}): {ind_m[:10]}")
        if cs_m: print(f"   ! cs misses ({len(cs_m)}): {cs_m[:10]}")
    db = json.load(open(os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')))
    k0 = sorted(db)[0]
    print(f"   sample {k0}: ind={db[k0]['ind_desc'][:70]!r}")
    print(f"              cs={db[k0]['cs_desc'][:60]!r} strand={db[k0]['strand']!r}")
