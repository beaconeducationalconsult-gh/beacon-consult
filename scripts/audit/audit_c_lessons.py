#!/usr/bin/env python3
"""Audit C - Verify the 8 B1 enriched lesson JSONs and 8 DOCX lesson-plan files.

JSON checks:
  - exactly 180 records, lesson_num 1..180 unique
  - complete grid: 3 terms x 12 weeks x 5 days, one lesson per slot
  - required fields non-empty
  - ind_code valid 5-part format AND exists in the B1 curriculum DB
DOCX checks:
  - 180 'LESSON PLAN #' headers; parsed (num, week, day) sequence == JSON
  - 3-phase structure blocks x180; Reflection x180; Sign-off x180
  - font Calibri; navy 002060 header color present

The DOCX files are *build outputs*: they are generated locally from the enriched
JSONs and are not in the repository (`.gitignore` covers `dist/books/` and
`books/`), so a fresh clone has none of them. An absent document is reported as
`MISSING` — not built here — and is not a defect of the data; a document that is
present and wrong is a `WARN`. C1 (the JSONs) is the check that always runs.
"""
# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json, os, re, sys
from pathlib import Path
from collections import Counter
import docx

from _paths import AUDIT, find_data
from docx.shared import RGBColor

ROOT = str(Path(__file__).resolve().parents[2])
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
CODE_RE = re.compile(r'^B1\.\d+\.\d+\.\d+\.\d+$')
REQ = ['strand_name', 'sub_strand', 'cs_code', 'cs_desc', 'ind_code', 'ind_desc',
       'perf_indicator', 'competencies', 'resources', 'starter', 'main', 'plenary', 'assessment']

SUBJECTS = {  # enriched json stem : (db json path, docx path, display)
    'math':            ('math_curriculum_db_clean.json',            'Basic1_Mathematics_Lesson_Plans_Full_Year.docx',        'Mathematics'),
    'science':         ('science_curriculum_db_clean.json',         'Basic1_Science_Lesson_Plans_Full_Year.docx',            'Science'),
    'english':         ('english_curriculum_db_clean.json',         'Basic1_English_Lesson_Plans_Full_Year.docx',            'English'),
    'ghanaian_language': ('ghanaian_language_curriculum_db_clean.json', 'Basic1_Ghanaian_Language_Lesson_Plans_Full_Year.docx', 'Ghanaian Language'),
    'history':         ('history_curriculum_db_clean.json',         'Basic1_History_Lesson_Plans_Full_Year.docx',            'History'),
    'owop':            ('owop_curriculum_db_clean.json',            'Basic1_OWOP_Lesson_Plans_Full_Year.docx',               'OWOP'),
    'rme':             ('rme_curriculum_db_clean.json',             'Basic1_RME_Lesson_Plans_Full_Year.docx',                'RME'),
    'creative_arts':   ('creative_arts_curriculum_db_clean.json',   'Basic1_Creative_Arts_Lesson_Plans_Full_Year.docx',      'Creative Arts'),
}

def audit_json(stem, dbp):
    issues = []
    # Resolved through find_data: these files live in data/lessons/ and
    # data/curriculum/, not in the repository root they used to be joined onto.
    path = str(find_data(f'{stem}_lessons_enriched.json') or '')
    try:
        lessons = json.load(open(path))
    except Exception as e:
        return {'subject': stem, 'status': 'FAIL', 'issues': [f'load error: {e}']}
    db = set(json.load(open(str(find_data(dbp) or ''))).keys())
    n = len(lessons)
    if n != 180:
        issues.append(f'expected 180 lessons, got {n}')
    nums = [l.get('lesson_num') for l in lessons]
    if sorted(nums) != list(range(1, 181)):
        issues.append('lesson_num not exactly 1..180')
    slots = Counter((l.get('term'), l.get('week'), l.get('day')) for l in lessons)
    expected_slots = {(t, w, d) for t in (1, 2, 3) for w in range(1, 13) for d in WEEKDAYS}
    dup_slots = [s for s, c in slots.items() if c > 1]
    empty_slots = expected_slots - set(slots)
    bogus_slots = set(slots) - expected_slots
    if dup_slots: issues.append(f'{len(dup_slots)} duplicated (term,week,day) slots: {dup_slots[:3]}')
    if empty_slots: issues.append(f'{len(empty_slots)} empty grid slots: {sorted(empty_slots)[:3]}')
    if bogus_slots: issues.append(f'{len(bogus_slots)} invalid grid slots: {sorted(bogus_slots)[:3]}')
    bad_code, not_in_db, missing = [], [], []
    for l in lessons:
        ic = str(l.get('ind_code', ''))
        if not CODE_RE.match(ic):
            bad_code.append((l.get('lesson_num'), ic))
        elif ic not in db:
            not_in_db.append((l.get('lesson_num'), ic))
        for fld in REQ:
            v = l.get(fld)
            if v is None or (isinstance(v, (list, str)) and len(v) == 0):
                missing.append((l.get('lesson_num'), fld))
    if bad_code: issues.append(f'{len(bad_code)} malformed ind_codes: {bad_code[:5]}')
    if not_in_db: issues.append(f'{len(not_in_db)} ind_codes not in curriculum DB: {not_in_db[:8]}')
    if missing: issues.append(f'{len(missing)} empty required fields: {missing[:5]}')
    status = 'PASS' if not issues else ('WARN' if all('not in curriculum DB' in i for i in issues) else 'FAIL')
    return {'subject': stem, 'n': n, 'status': status, 'issues': issues}

def audit_docx(stem, docx_name, lessons):
    issues = []
    path = find_data(docx_name)
    if not path:
        return {'subject': stem, 'docx': docx_name, 'status': 'MISSING',
                'issues': ['not built here — a generated document, not a repository file']}
    d = docx.Document(path)
    texts = [p.text for p in d.paragraphs]
    joined = '\n'.join(texts)
    heads = re.findall(r'LESSON PLAN #(\d+)\s*\xb7\s*WEEK\s*(\d+)\s*\xb7\s*([A-Z]+)', joined)
    n_headers = len(re.findall(r'LESSON PLAN #\d+', joined))
    if n_headers != 180:
        issues.append(f'expected 180 lesson headers, found {n_headers}')
    parsed = [(int(a), int(b), c) for a, b, c in heads]
    want = [(l['lesson_num'], l['week'], l['day'].upper()) for l in lessons]
    if parsed != want:
        mismatch = [(p, w) for p, w in zip(parsed, want) if p != w][:3]
        issues.append(f'header (num,week,day) sequence differs from JSON; first mismatches: {mismatch} (parsed {len(parsed)}, want {len(want)})')
    for label, pat in [('PHASE 1', r'PHASE 1\s*—?\s*STARTER'), ('PHASE 2', r'PHASE 2\s*—?\s*MAIN'),
                       ('PHASE 3', r'PHASE 3\s*—?\s*PLENARY'), ('Reflection', r"Teacher's Reflection"),
                       ('Sign-off', r"Teacher's Signature")]:
        c = len(re.findall(pat, joined, re.IGNORECASE if label == 'Reflection' else 0))
        if c != 180:
            issues.append(f'{label}: found {c}, expected 180')
    # font/color spot checks
    fonts = set()
    navy = False
    for p in d.paragraphs[:400]:
        for r in p.runs:
            if r.font.name: fonts.add(r.font.name)
            try:
                if r.font.color and r.font.color.rgb == RGBColor(0, 32, 96):
                    navy = True
            except Exception:
                pass
    if fonts and not {'Calibri'} <= fonts:
        issues.append(f'unexpected fonts: {sorted(fonts)[:6]}')
    if not navy:
        issues.append('navy 002060 header color not found (spot check)')
    status = 'PASS' if not issues else 'WARN'
    return {'subject': stem, 'docx': docx_name, 'size_kb': round(os.path.getsize(path)/1024),
            'status': status, 'issues': issues}

def main():
    jr, dr = [], []
    for stem, (dbp, docx_name, disp) in SUBJECTS.items():
        jr.append(audit_json(stem, dbp))
    for stem, (dbp, docx_name, disp) in SUBJECTS.items():
        lessons = json.load(open(str(find_data(f'{stem}_lessons_enriched.json'))))
        dr.append(audit_docx(stem, docx_name, lessons))
    print('AUDIT C1 - enriched lesson JSONs')
    for r in jr:
        flag = {'PASS': 'OK ', 'WARN': 'WRN', 'FAIL': 'FHL'}.get(r['status'], '???')
        print(f"[{flag}] {r['subject']:20s} n={r.get('n','-')}")
        for i in r['issues']:
            print(f'      ! {i}')
    print('AUDIT C2 - DOCX lesson plan files')
    for r in dr:
        flag = {'PASS': 'OK ', 'WARN': 'WRN', 'FAIL': 'FHL',
                'MISSING': '···'}.get(r['status'], '???')
        print(f"[{flag}] {r['subject']:20s} {r.get('docx','')} ({r.get('size_kb','?')} KB)")
        for i in r['issues']:
            print(f'      ! {i}')
    built = [r for r in dr if r['status'] != 'MISSING']
    summary = {'checked': len(built), 'not_built': len(dr) - len(built),
               'warn': sum(1 for r in dr if r['status'] == 'WARN'),
               'fail': sum(1 for r in dr if r['status'] == 'FAIL')}
    print(f"  {summary['checked']} of {len(dr)} document(s) present — "
          f"{summary['not_built']} not built here, {summary['warn']} WARN, {summary['fail']} FAIL")
    if summary['not_built']:
        print('  (the documents are generated from the JSONs above and are not in the '
              'repository; the C1 rows are what `make check` stands on)')
    json.dump({'json': jr, 'docx': dr, 'summary': summary},
              open(str(AUDIT / 'audit_c_results.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
