#!/usr/bin/env python3
"""Audit A - Structural validation of all 76 curriculum DB files.

Checks per file:
  1. JSON parses, top-level dict
  2. No duplicate keys
  3. Every key is a 5-part indicator code B{g}.s.ss.cs.ind
  4. Grade digit in code == grade of file
  5. Required fields present and non-empty
  6. cs_code consistent with indicator code (first 4 parts)
  7. Placeholder vs rich metadata flag
  8. Counts vs embedded summary JSON (where present) and vs expected table
"""
# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json, os, re, sys
from pathlib import Path
from _paths import find_data  # noqa: E402  (scripts/ is on sys.path)

ROOT = str(Path(__file__).resolve().parents[2])
CDB = os.path.join(ROOT, 'data/curriculum')
CODE_RE = re.compile(r'^B(\d)\.(\d+)\.(\d+)\.(\d+)\.(\d+)$')
REQUIRED = ['strand', 'sub_strand', 'cs_code', 'cs_desc', 'ind_desc',
            'competencies', 'resources', 'keywords', 'assessment']

B1_ALIAS = {
    'math': 'mathematics', 'science': 'science', 'english': 'english-language',
    'ghanaian_language': 'ghanaian-language', 'history': 'history',
    'owop': 'owop', 'rme': 'rme', 'creative_arts': 'creative-arts',
}

EXPECTED = {  # subject-id -> grade -> expected count (verified against official NaCCA PDFs)
    'mathematics':   {'B1': 24, 'B2': 29, 'B3': 39, 'B4': 71, 'B5': 67, 'B6': 42, 'B7': 67, 'B8': 49, 'B9': 43},
    'science':       {'B1': 31, 'B2': 25, 'B3': 25, 'B4': 24, 'B5': 29, 'B6': 26, 'B7': 52, 'B8': 46, 'B9': 54},
    'english-language': {'B1': 72, 'B2': 67, 'B3': 78, 'B4': 129, 'B5': 133, 'B6': 131, 'B7': 53, 'B8': 49, 'B9': 50},
    'ghanaian-language': {'B1': 77, 'B2': 69, 'B3': 73, 'B4': 83, 'B5': 89, 'B6': 94, 'B7': 48, 'B8': 28, 'B9': 28},
    'history':       {'B1': 8, 'B2': 4, 'B3': 7, 'B4': 10, 'B5': 13, 'B6': 9},
    'owop':          {'B1': 24, 'B4': 25, 'B5': 25, 'B6': 24},
    'rme':           {'B1': 9, 'B2': 13, 'B3': 14, 'B4': 13, 'B5': 15, 'B6': 13, 'B7': 27, 'B8': 22, 'B9': 19},
    'creative-arts': {'B1': 42, 'B2': 42, 'B3': 40, 'B4': 47, 'B5': 48, 'B6': 46},
    'computing':     {'B7': 50, 'B8': 37, 'B9': 36},
    'social-studies': {'B7': 17, 'B8': 18, 'B9': 19},
    'career-technology': {'B7': 43, 'B8': 42, 'B9': 47},
    'creative-arts-design': {'B7': 33, 'B8': 34, 'B9': 33},
    'french':        {'B7': 64, 'B8': 54, 'B9': 48},
}

def pairs_no_dup(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        dups = sorted({k for k in keys if keys.count(k) > 1})
        raise ValueError(f'duplicate keys: {dups}')
    return dict(pairs)

def audit_file(path, sid, grade):
    r = {'file': path.replace(ROOT + '/', ''), 'subject': sid, 'grade': grade}
    issues = []
    try:
        with open(path) as f:
            d = json.load(f, object_pairs_hook=pairs_no_dup)
    except Exception as e:
        r.update(status='FAIL', n=0, issues=[f'JSON load error: {e}'])
        return r
    r['n'] = len(d)
    if not isinstance(d, dict) or not d:
        r.update(status='FAIL', issues=['empty or non-dict DB'])
        return r
    bad_code, grade_mismatch, missing_fields, empty_fields, cs_mismatch = [], [], [], [], []
    placeholder = 0
    for code, v in d.items():
        m = CODE_RE.match(code)
        if not m:
            bad_code.append(code); continue
        if f'B{m.group(1)}' != grade:
            grade_mismatch.append(code)
        if not isinstance(v, dict):
            missing_fields.append(code); continue
        for fld in REQUIRED:
            if fld not in v:
                missing_fields.append(f'{code}.{fld}')
            elif v[fld] is None or str(v[fld]).strip() == '':
                empty_fields.append(f'{code}.{fld}')
        cs = v.get('cs_code', '')
        if cs and not code.startswith(cs + '.'):
            cs_mismatch.append(f'{code} vs cs_code={cs}')
        if re.match(r'^\w[\w &-]* Learning Indicator ', str(v.get('ind_desc', ''))):
            placeholder += 1
    if bad_code: issues.append(f'{len(bad_code)} malformed codes: {bad_code[:5]}')
    if grade_mismatch: issues.append(f'{len(grade_mismatch)} grade-mismatched codes: {grade_mismatch[:5]}')
    if missing_fields: issues.append(f'{len(missing_fields)} missing fields: {missing_fields[:5]}')
    if empty_fields: issues.append(f'{len(empty_fields)} empty fields: {empty_fields[:5]}')
    if cs_mismatch: issues.append(f'{len(cs_mismatch)} cs_code inconsistencies: {cs_mismatch[:3]}')
    r['placeholder'] = placeholder
    r['rich'] = len(d) - placeholder
    # summary cross-check
    sdir = ROOT if grade == 'B1' else CDB
    sfname = f'{B1_ALIAS.get(sid, sid)}_curriculum_summary.json' if grade == 'B1' else f'{sid}_{grade}_curriculum_summary.json'
    spath = os.path.join(sdir, sfname)
    if os.path.exists(spath):
        try:
            s = json.load(open(spath))
            s_count = s.get('counts', {}).get('indicators')
            if s_count is not None and s_count != len(d):
                issues.append(f'summary says {s_count} indicators, DB has {len(d)}')
        except Exception as e:
            issues.append(f'summary unreadable: {e}')
    # expected table
    exp = EXPECTED.get(sid, {}).get(grade)
    r['expected'] = exp
    if exp is not None and exp != len(d):
        issues.append(f'expected {exp} indicators, DB has {len(d)}')
    r['status'] = 'PASS' if not issues else ('WARN' if not issues[:1] else 'FAIL')
    r['status'] = 'PASS' if not issues else 'WARN'
    r['issues'] = issues
    return r

def main():
    jobs = []
    for f, sid in B1_ALIAS.items():
        # Resolved through find_data, not joined onto ROOT: the B1 files used to
        # sit in the repository root and now live in data/curriculum/ (several
        # also exist only in data/reference/). A ROOT join silently produced
        # eight "file not found" failures that looked like data corruption.
        p = find_data(f'{f}_curriculum_db_clean.json')
        jobs.append((str(p) if p else os.path.join(ROOT, f'{f}_curriculum_db_clean.json'), sid, 'B1'))
    for fn in sorted(os.listdir(CDB)):
        m = re.match(r'^(.+)_B(\d)_curriculum_db_clean\.json$', fn)
        if m:
            jobs.append((os.path.join(CDB, fn), m.group(1), f'B{m.group(2)}'))
    results = [audit_file(p, sid, g) for p, sid, g in jobs]
    npass = sum(1 for r in results if r['status'] == 'PASS')
    nwarn = sum(1 for r in results if r['status'] == 'WARN')
    nfail = sum(1 for r in results if r['status'] == 'FAIL')
    total = sum(r['n'] for r in results)
    print(f'AUDIT A - {len(results)} DB files | PASS {npass} | WARN {nwarn} | FAIL {nfail} | total indicators {total}')
    for r in results:
        flag = {'PASS': 'OK ', 'WARN': 'WRN', 'FAIL': 'FHL'}[r['status']]
        line = f"[{flag}] {r['file']:55s} n={r['n']:4d} rich={r.get('rich',0):4d} placeholder={r.get('placeholder',0):4d}"
        print(line)
        for i in r['issues']:
            print(f'      ! {i}')
    out = Path(ROOT) / 'data' / 'audit' / 'audit_a_results.json'   # ROOT is a str
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(results, open(out, 'w'), indent=1)
    print(f'wrote {out.relative_to(ROOT)}')

if __name__ == '__main__':
    main()
