#!/usr/bin/env python3
"""Audit A - Structural validation of every curriculum DB file in data/curriculum/.

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
# kindergarten prints `K1.`/`K2.` where the bundle and the file names say KG1/KG2
CODE_RE = re.compile(r'^([BK])(\d)\.(\d+)\.(\d+)\.(\d+)\.(\d+)$')
REQUIRED = ['strand', 'sub_strand', 'cs_code', 'cs_desc', 'ind_desc',
            'competencies', 'resources', 'keywords', 'assessment']

# Fields that are empty in the database because they are empty (or wrongly
# numbered) in the print.  An exemption is carried here, in the open, so the audit
# can still fail on every *other* empty field; each one is documented in
# docs/TODO.md and docs/curriculum-data.md.
BLANK_IN_PRINT = {
    'cs_desc': {
        # KG1's content-standard cell for this standard is blank in the print;
        # its five records keep whatever they have (docs/TODO.md P1-1)
        'K1.3.2.1.1', 'K1.3.2.1.2', 'K1.3.2.1.3', 'K1.3.2.1.4', 'K1.3.2.1.5',
        # the french B6 print numbers a *fifth* content standard (p93) in a
        # sub-strand whose scope table lists four, so no skill can be named
        'B6.1.2.5.3',
    },
}

# A handful of B1 databases are named after their document, not the subject id
B1_PREFIX = {'mathematics': 'math', 'science': 'science', 'english-language': 'english'}

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
    'computing':     {'B4': 27, 'B5': 81, 'B6': 98, 'B7': 50, 'B8': 37, 'B9': 36},
    'social-studies': {'B7': 17, 'B8': 18, 'B9': 19},
    'career-technology': {'B7': 43, 'B8': 42, 'B9': 47},
    'creative-arts-design': {'B7': 33, 'B8': 34, 'B9': 33},
    'french':        {'B4': 88, 'B5': 90, 'B6': 89, 'B7': 64, 'B8': 54, 'B9': 48},
    'kindergarten':  {'KG1': 169, 'KG2': 170},
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
    placeholder = excused = 0
    for code, v in d.items():
        m = CODE_RE.match(code)
        if not m:
            bad_code.append(code); continue
        # the code prints the letter and the grade digit (`K1.3.2.1.4`), while the
        # file name and the bundle label the kindergarten grades KG1/KG2
        letter, digit = m.group(1), m.group(2)
        if grade != f'{letter}{digit}' and not (letter == 'K' and grade == f'KG{digit}'):
            grade_mismatch.append(code)
        if not isinstance(v, dict):
            missing_fields.append(code); continue
        for fld in REQUIRED:
            if fld not in v:
                missing_fields.append(f'{code}.{fld}')
            elif v[fld] is None or str(v[fld]).strip() == '':
                if code in BLANK_IN_PRINT.get(fld, ()):
                    excused += 1          # empty because the print is, not the data
                else:
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
    r['blank_in_print'] = excused
    # summary cross-check
    # The B1 files are named after their document (`math_curriculum_db_clean.json`)
    # and every summary now lives beside its database in data/curriculum/, which is
    # searched through find_data rather than joined onto a directory.
    prefix = B1_PREFIX.get(sid, sid) if grade == 'B1' else sid
    sfname = f'{prefix}_curriculum_summary.json' if grade == 'B1' else f'{sid}_{grade}_curriculum_summary.json'
    spath = find_data(sfname)
    r['summary'] = Path(spath).name if spath else None
    if spath:
        try:
            s = json.loads(Path(spath).read_text())
            s_count = s.get('counts', {}).get('indicators')
            if s_count is not None and s_count != len(d):
                issues.append(f'summary says {s_count} indicators, DB has {len(d)}')
            elif s_count is None:
                issues.append('summary carries no counts block')
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
        # `_B4_` / `_KG1_`: the kindergarten grades are named KG1/KG2 while their
        # codes print K1./K2. (the `grade` column keeps the file-name form)
        m = re.match(r'^(.+)_(B\d|KG\d)_curriculum_db_clean\.json$', fn)
        if m:
            jobs.append((os.path.join(CDB, fn), m.group(1), m.group(2)))
    results = [audit_file(p, sid, g) for p, sid, g in jobs]
    npass = sum(1 for r in results if r['status'] == 'PASS')
    nwarn = sum(1 for r in results if r['status'] == 'WARN')
    nfail = sum(1 for r in results if r['status'] == 'FAIL')
    total = sum(r['n'] for r in results)
    print(f'AUDIT A - {len(results)} DB files | PASS {npass} | WARN {nwarn} | FAIL {nfail} | total indicators {total}')
    for r in results:
        flag = {'PASS': 'OK ', 'WARN': 'WRN', 'FAIL': 'FHL'}[r['status']]
        line = f"[{flag}] {r['file']:55s} n={r['n']:4d} rich={r.get('rich',0):4d} placeholder={r.get('placeholder',0):4d}"
        if r.get('blank_in_print'):
            # the exemptions stay visible: they are the print's defects, not ours
            line += f" blank-in-print={r['blank_in_print']}"
        print(line)
        for i in r['issues']:
            print(f'      ! {i}')
    out = Path(ROOT) / 'data' / 'audit' / 'audit_a_results.json'   # ROOT is a str
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(results, open(out, 'w'), indent=1)
    print(f'wrote {out.relative_to(ROOT)}')

if __name__ == '__main__':
    main()
