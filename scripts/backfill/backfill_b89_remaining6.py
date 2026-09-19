#!/usr/bin/env python3
"""Backfill B8/B9 remaining-6 DBs (rme, computing, social-studies, career-technology,
creative-arts-design, french) with authentic NaCCA CCP text. /JHS-aware matcher,
notation-table guard, competency-tail cleaner. Social Studies = whole-PDF (codes self-identify)."""
# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json, os, re, shutil, gzip, hashlib
from pathlib import Path  # noqa: E402  (legacy script)

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
    return ('B' + r'\s*' + re.escape(parts[0][1]) + r'(?:\s*/\s*JHS\s*\d\s*)?'
            + r'\s*[.\s]\s*'
            + r'\s*[.\s]\s*'.join(re.escape(x) for x in parts[1:])
            + r'(?![.\s]*\d)')

BOUNDARY = re.compile(
    r'\uf0b7|\u2022|E\.\s?g|E\.G|E\.g|Enquiry route|CORE COMPETENCIES|Core Competencies|Exemplar|Exemplars?:?'
    r'|B\s*\d(?:\s*/\s*JHS\s*\d\s*)?\s*[.\s]\s*\d+(?:\s*[.\s]\s*\d+){2,4}')

NOTATION = re.compile(r'Example:\s*B\s*\d|ANNOTATION|MEANING /|REPRESENTATION|Year or Class|Class/Year|STRAND NUMBER|Sub-Strand Number', re.IGNORECASE)

def grab(t, code, minlen=14, maxscan=420, t2=None):
    best = ''
    for tt in (t, t2) if t2 else (t,):
        for m in list(re.finditer(code_rx(code), tt))[:8]:
            pre = tt[max(0, m.start() - 90):m.start()]
            if NOTATION.search(pre):
                continue
            seg = tt[m.end():tt and tt.find(chr(10), m.end()) if False else m.end() + maxscan]
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
    'rme_CCP_B7-B9.pdf': {'B8': (107140, 149507), 'B9': (149507, None)},
    'computing_CCP_B7-B9.pdf': {'B8': (95520, 120376), 'B9': (120376, None)},
    'social_studies_CCP_B7-B9.pdf': {'B8': (0, None), 'B9': (0, None)},
    'career_tech_CCP_B7-B9.pdf': {'B8': (135389, 180695), 'B9': (180695, None)},
    'creative_arts_design_CCP_B7-B9.pdf': {'B8': (129437, 168964), 'B9': (168964, None)},
    'french_CCP_B7-B9.pdf': {'B8': (145898, 208455), 'B9': (208455, None)},
}

RME_STRANDS = {1: '1. GOD, HIS CREATION AND ATTRIBUTES', 2: '2. RELIGIOUS PRACTICES',
               3: '3. THE FAMILY AND THE COMMUNITY', 4: '4. RELIGIOUS LEADERS AND PERSONALITIES',
               5: '5. ETHICS AND MORAL LIFE', 6: '6. RELIGION AND ECONOMIC LIFE'}
COMP_STRANDS = {1: '1. INTRODUCTION TO COMPUTING', 2: '2. PRODUCTIVITY SOFTWARE',
                3: '3. COMMUNICATION NETWORKS', 4: '4. COMPUTATIONAL THINKING'}
SS_STRANDS = {1: '1. ENVIRONMENT', 2: '2. FAMILY LIFE', 3: '3. SENSE OF PURPOSE',
              4: '4. LAW AND ORDER', 5: '5. SOCIO-ECONOMIC DEVELOPMENT', 6: '6. NATIONHOOD'}
CT_STRANDS = {1: '1. HEALTH AND SAFETY', 2: '2. MATERIALS FOR PRODUCTION',
              3: '3. TOOLS, EQUIPMENT AND PROCESSES', 4: '4. TECHNOLOGY',
              5: '5. DESIGNING AND MAKING OF ARTEFACTS/PRODUCTS', 6: '6. ENTREPRENEURIAL SKILLS'}
CAD_STRANDS = {1: '1. DESIGN', 2: '2. CREATIVE ARTS'}
FR_B8 = {1: '1. FAIRE CONNAISSANCE', 2: "2. L'ENVIRONNEMENT",
         4: '4. LA LOCALISATION, LES HORAIRES ET LES DÉPLACEMENTS', 5: '5. LES ACHATS',
         6: '6. LES LOISIRS', 8: "8. LES PROJETS D'AVENIR"}
FR_B9 = {2: "2. L'ENVIRONNEMENT", 5: '5. LES ACHATS', 6: '6. LES LOISIRS',
         7: "7. LES HABITUDES ET LES FAITS DU PASSÉ", 8: "8. PROJETS D'AVENIR",
         9: '9. LES SENTIMENTS ET LES OPINIONS', 10: '10. LES MOYENS DE COMMUNICATION'}

JOBS = []
for g in ('B8', 'B9'):
    JOBS += [
        ('rme', g, 'rme_CCP_B7-B9.pdf', RME_STRANDS),
        ('computing', g, 'computing_CCP_B7-B9.pdf', COMP_STRANDS),
        ('social-studies', g, 'social_studies_CCP_B7-B9.pdf', SS_STRANDS),
        ('career-technology', g, 'career_tech_CCP_B7-B9.pdf', CT_STRANDS),
        ('creative-arts-design', g, 'creative_arts_design_CCP_B7-B9.pdf', CAD_STRANDS),
        ('french', g, 'french_CCP_B7-B9.pdf', FR_B8 if g == 'B8' else FR_B9),
    ]

report = []
for sid, g, pdf, strand_map in JOBS:
    full = text_of(pdf)
    s, e = BODIES[pdf][g]
    scope = full[s:e if e else len(full)]
    t2 = full if pdf != 'social_studies_CCP_B7-B9.pdf' else None
    path = os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')
    bak = os.path.join(BK, os.path.basename(path) + '.pre_b89r6backfill')
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    db = json.load(open(path))
    zero_hits = [c for c in db if not re.search(code_rx(c), scope)]
    n_ind = n_cs = n_str = 0
    misses = []
    for code, v in db.items():
        cur = str(v.get('ind_desc', ''))
        if f'Learning Indicator {code}' in cur or cur.strip() == '':
            new = grab(scope, code, t2=t2)
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
            new = grab(scope, cs, minlen=12, maxscan=260, t2=t2)
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
    print(f"== {sid} {g}: indicators={n} | ind={i} | cs={c} | strands={s}")
    if zero_hits:
        print(f"   ? ZERO hits in {g} scope (artifact candidates): {zero_hits[:8]}")
    if misses:
        ind_m = [c2 for t2, c2 in misses if t2 == 'ind']
        cs_m = sorted({c2 for t2, c2 in misses if t2 == 'cs'})
        print(f"   ! ind misses ({len(ind_m)}): {ind_m[:10]}")
        if cs_m: print(f"   ! cs misses ({len(cs_m)}): {cs_m[:10]}")
