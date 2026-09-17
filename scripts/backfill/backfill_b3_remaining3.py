#!/usr/bin/env python3
"""Backfill B3 Creative Arts, History, RME DBs with authentic NaCCA text.
History + RME grabs are GRADE-SCOPED to the BASIC 3 body sections of their PDFs."""
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

# grade-scoped B3 body slices (verified BASIC-3 section offsets)
BODIES = {
    'history.pdf': (68773, 76162),
    'rme_B1-B6.pdf': (68277, 79797),
}

JOBS = [
    ('creative-arts', 'B3', 'creative_arts_B1-B3.pdf', None),
    ('history', 'B3', 'history.pdf', {
        2: '2. MY COUNTRY GHANA', 3: '3. EUROPEANS IN GHANA'}),
    ('rme', 'B3', 'rme_B1-B6.pdf', {
        1: '1. GOD, HIS CREATION AND ATTRIBUTES',
        2: '2. RELIGIOUS PRACTICES AND THEIR MORAL IMPLICATIONS',
        3: '3. RELIGIOUS LEADERS',
        4: '4. THE FAMILY AND THE COMMUNITY'}),
]

report = []
for sid, g, pdf, strand_map in JOBS:
    t = text_of(pdf)
    if pdf in BODIES:
        s, e = BODIES[pdf]
        scope = t[s:e]
    else:
        scope = t
    path = os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')
    bak = os.path.join(BK, os.path.basename(path) + '.pre_b3r3backfill')
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    db = json.load(open(path))
    n_ind = n_cs = n_str = 0
    misses = []
    for code, v in db.items():
        cur = str(v.get('ind_desc', ''))
        if f'Learning Indicator {code}' in cur or cur.strip() == '':
            new = grab(scope, code)
            if new:
                v['ind_desc'] = new
                n_ind += 1
            else:
                misses.append(code)
        cs = v.get('cs_code', '')
        cur_cs = str(v.get('cs_desc', ''))
        if cs and (f'Content Standard {cs}' in cur_cs or cur_cs.strip() == ''):
            new = grab(scope, cs, minlen=12, maxscan=260)
            if new:
                v['cs_desc'] = new
                n_cs += 1
        if strand_map:
            num = int(code.split('.')[1])
            target = strand_map.get(num)
            if target and v.get('strand') != target:
                v['strand'] = target
                n_str += 1
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    report.append((sid, g, len(db), n_ind, n_cs, n_str, misses))

for sid, g, n, i, c, s, misses in report:
    print(f"== {sid} {g}: indicators={n} | ind backfilled={i} | cs backfilled={c} | strands set={s}")
    if misses:
        print(f"   ! no ind text for {len(misses)}: {misses[:12]}")
    db = json.load(open(os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')))
    k0 = sorted(db)[0]
    print(f"   sample {k0}: ind={db[k0]['ind_desc'][:75]!r}")
    print(f"              cs={db[k0]['cs_desc'][:65]!r} strand={db[k0]['strand']!r}")
