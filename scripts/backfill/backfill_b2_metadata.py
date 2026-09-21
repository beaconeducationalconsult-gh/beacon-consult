#!/usr/bin/env python3
"""Backfill B2 Core-4 DBs (math, science, english, ghanaian) with authentic
NaCCA text extracted from the source curriculum PDFs:
  - ind_desc  : official indicator description (text after the 5-part code,
                cut at exemplar/bullet boundaries)
  - cs_desc   : official content standard text (text after the 4-part code)
  - strand    : official strand name (e.g. "1. NUMBER"), fallback to code
Fallback = keep existing placeholder text. Backup + full report.
"""
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
    """Tolerant regex: 'B2 2.1.1.1.1' / 'B2.2.1.1.1' / 'B 2.2.1.1.1'."""
    parts = code.split('.')
    return ('B' + r'\s*' + re.escape(parts[0][1]) + r'\s*[.\s]\s*'
            + r'\s*[.\s]\s*'.join(re.escape(x) for x in parts[1:])
            + r'(?![.\s]*\d)')

BOUNDARY = re.compile(
    r'\uf0b7|\u2022|E\.\s?g|E\.G|Enquiry route|CORE COMPETENCIES|Core Competencies|Exemplar'
    r'|B\s*\d\s*[.\s]\s*\d+(?:\s*[.\s]\s*\d+){2,4}')

def grab(t, code, minlen=15, maxscan=420):
    """Extract text after every occurrence of code; return best (longest) candidate."""
    best = ''
    for m in list(re.finditer(code_rx(code), t))[:8]:
        seg = t[m.end():m.end() + maxscan]
        bm = BOUNDARY.search(seg)
        seg = seg[:bm.start()] if bm else seg
        seg = re.sub(r'\s+', ' ', seg).strip(' :.-\u2013\t')
        if len(seg) > len(best):
            best = seg
    return best if len(best) >= minlen else ''

def strand_names(t, grade):
    """Map strand number -> name from PDF headings (course-level, applies to all grades)."""
    names = {}
    for m in re.finditer(r'STRAND\s*(\d)\s*[:\.\s]\s*\n?\s*([A-Z][A-Z &,\u2019\-]{2,60})', t):
        n = int(m.group(1))
        name = re.sub(r'\s+', ' ', m.group(2)).strip(' .:').title()
        if n not in names or len(name) > len(names[n]):
            names[n] = name
    return names

JOBS = [
    # sid, grade, pdf, subject label
    ('mathematics', 'B2', 'math_B1-B3.pdf', 'Mathematics'),
    ('science', 'B2', 'science_B1-B3.pdf', 'Science'),
    ('english-language', 'B2', 'english_B1-B3.pdf', 'English Language'),
    ('ghanaian-language', 'B2', 'gh_lang_b1b3.pdf', 'Ghanaian Language'),
]

report = []
for sid, g, pdf, label in JOBS:
    t = text_of(pdf)
    snames = strand_names(t, g)
    path = os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')
    bak = os.path.join(BK, os.path.basename(path) + '.pre_b2backfill')
    if not os.path.exists(bak):
        shutil.copy2(path, bak)
    db = json.load(open(path))
    n_ind = n_cs = n_str = 0
    misses = []
    for code, v in db.items():
        # 1) indicator description
        cur = str(v.get('ind_desc', ''))
        if f'Learning Indicator {code}' in cur or cur.strip() == '':
            new = grab(t, code)
            if new:
                v['ind_desc'] = new
                n_ind += 1
            else:
                misses.append(code)
        # 2) content standard description
        cs = v.get('cs_code', '')
        cur_cs = str(v.get('cs_desc', ''))
        if cs and (f'Content Standard {cs}' in cur_cs or cur_cs.strip() == ''):
            new = grab(t, cs, minlen=12, maxscan=260)
            if new:
                v['cs_desc'] = new
                n_cs += 1
        # 3) strand name
        m = re.match(r'^B\d+\.(\d+)$', str(v.get('strand', '')))
        if m and int(m.group(1)) in snames:
            v['strand'] = f"{m.group(1)}. {snames[int(m.group(1))]}"
            n_str += 1
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=1)
    report.append((sid, g, len(db), n_ind, n_cs, n_str, misses, dict(sorted(snames.items()))))

for sid, g, n, i, c, s, misses, snames in report:
    print(f"== {sid} {g}: indicators={n} | ind_desc backfilled={i} | cs_desc backfilled={c} | strand named={s}")
    print(f"   strand names: {snames}")
    if misses:
        print(f"   ! no text found for {len(misses)}: {misses[:12]}")
    # samples
    db = json.load(open(os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')))
    k0 = sorted(db)[0]
    print(f"   sample {k0}: ind={db[k0]['ind_desc'][:80]!r} cs={db[k0]['cs_desc'][:70]!r} strand={db[k0]['strand']!r}")
print('\nBackups: audit_backup/*.pre_b2backfill')
