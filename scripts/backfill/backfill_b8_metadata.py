#!/usr/bin/env python3
"""Backfill B8 Core-4 DBs (math, science, english, ghanaian) with authentic NaCCA CCP
text. All grabs GRADE-SCOPED to BASIC 8 body slices; /JHS-aware code matcher."""
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
    # CCP codes may carry /JHSn infix: B8/JHS2.1.1.1.1
    parts = code.split('.')
    return ('B' + r'\s*' + re.escape(parts[0][1]) + r'(?:\s*/\s*JHS\s*\d\s*)?'
            + r'\s*[.\s]\s*'
            + r'\s*[.\s]\s*'.join(re.escape(x) for x in parts[1:])
            + r'(?![.\s]*\d)')

BOUNDARY = re.compile(
    r'\uf0b7|\u2022|E\.\s?g|E\.G|E\.g|Enquiry route|CORE COMPETENCIES|Core Competencies|Exemplar|Exemplars?:?'
    r'|B\s*\d(?:\s*/\s*JHS\s*\d\s*)?\s*[.\s]\s*\d+(?:\s*[.\s]\s*\d+){2,4}')

NOTATION = re.compile(r'Example:|ANNOTATION|MEANING /|REPRESENTATION|Year or Class|Class/Year|STRAND NUMBER|Sub-Strand Number', re.IGNORECASE)

def grab(t, code, minlen=14, maxscan=420):
    best = ''
    for m in list(re.finditer(code_rx(code), t))[:8]:
        pre = t[max(0, m.start() - 90):m.start()]
        if NOTATION.search(pre):
            continue
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
CONTAM = re.compile(r'(©\s*NaCCA.*|CONTENT STANDARDS?:?.*|CONTENT STANDARD.*|SUBJECT SPECIFIC.*|INDICATORS AND EXEMPLARS.*)$')

def clean_desc(d):
    d = CONTAM.sub('', d).strip(' .|')
    while True:
        m = COMP_PAT.search(d)
        if not m:
            break
        d = d[:m.start()].rstrip(' .|')
    comp_any = re.compile(r'\s*[-,;|/]?\s*(Communication and Collaboration|Critical Thinking and Problem Solving'
                          r'|Personal Development and Leadership|Creativity and Innovation'
                          r'|Cultural Identity and Global Citizenship|Digital Literacy)(\s*\(CC\))?[^.]*$')
    while True:
        m = comp_any.search(d)
        if not m:
            break
        d = d[:m.start()].rstrip(' ,;|-')
    return d

BODIES = {
    'mathematics_CCP_B7-B9_draft.pdf': (126618, 190705),
    'science_CCP_B7-B9.pdf': (143098, 192669),
    'english_CCP_B7-B9.pdf': (118892, 157496),
    'ghanaian_language_CCP_B7-B9.pdf': (109353, 131416),
}

JOBS = [
    ('mathematics', 'B8', 'mathematics_CCP_B7-B9_draft.pdf', {
        1: '1. NUMBER', 2: '2. ALGEBRA', 3: '3. GEOMETRY AND MEASUREMENT', 4: '4. DATA'}),
    ('science', 'B8', 'science_CCP_B7-B9.pdf', {
        1: '1. DIVERSITY OF MATTER', 2: '2. CYCLES', 3: '3. SYSTEMS',
        4: '4. FORCES AND ENERGY', 5: '5. HUMANS AND THE ENVIRONMENT'}),
    ('english-language', 'B8', 'english_CCP_B7-B9.pdf', {
        1: '1. ORAL LANGUAGE (LISTENING AND SPEAKING)', 2: '2. READING',
        3: '3. GRAMMAR AND GRAMMAR USAGE', 4: '4. WRITING', 5: '5. LITERATURE'}),
    ('ghanaian-language', 'B8', 'ghanaian_language_CCP_B7-B9.pdf', {
        1: '1. CUSTOMS AND INSTITUTIONS', 2: '2. LISTENING AND SPEAKING', 3: '3. READING',
        4: '4. LANGUAGE AND USAGE', 5: '5. COMPOSITION WRITING', 6: '6. LITERATURE'}),
]

report = []
for sid, g, pdf, strand_map in JOBS:
    full = text_of(pdf)
    s, e = BODIES[pdf]
    scope = full[s:e]
    path = os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')
    bak = os.path.join(BK, os.path.basename(path) + '.pre_b8backfill')
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
        new = re.sub(r'^\(?CONTINUED\)?\s*:?\s*', '', str(v.get('cs_desc', ''))).strip()
        if new != v['cs_desc']:
            v['cs_desc'] = new
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    report.append((sid, g, len(db), n_ind, n_cs, n_str, misses, zero_hits))

for sid, g, n, i, c, s, misses, zero_hits in report:
    print(f"== {sid} {g}: indicators={n} | ind backfilled={i} | cs backfilled={c} | strands set={s}")
    if zero_hits:
        print(f"   ? ZERO hits in B8 body (artifact candidates): {zero_hits[:8]}")
    if misses:
        ind_m = [c2 for t2, c2 in misses if t2 == 'ind']
        cs_m = sorted({c2 for t2, c2 in misses if t2 == 'cs'})
        print(f"   ! ind misses ({len(ind_m)}): {ind_m[:10]}")
        if cs_m: print(f"   ! cs misses ({len(cs_m)}): {cs_m[:10]}")
    db = json.load(open(os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')))
    k0 = sorted(db)[0]
    print(f"   sample {k0}: ind={db[k0]['ind_desc'][:70]!r}")
    print(f"              cs={db[k0]['cs_desc'][:60]!r} strand={db[k0]['strand']!r}")
