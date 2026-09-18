#!/usr/bin/env python3
"""Audit B - Cross-check every curriculum DB against its source NaCCA PDF.

Independent re-extraction of indicator codes straight from the PDFs
(pypdf + tolerant regex), then set comparison with the DBs:
  - valid:    every DB code found in the PDF (DB codes are authentic)
  - coverage: % of PDF indicators captured by the DB
Also: authenticity spot-check of B1 rich ind_desc strings against PDF text.
"""
# --- resolve bare data filenames against data/ (see scripts/_compat.py) ---
import sys as _sys, pathlib as _pathlib
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parents[1]))
from _compat import open_compat; open_compat()
# -----------------------------------------------------------------------
import json, os, re, gzip, hashlib
from pathlib import Path
from pypdf import PdfReader

ROOT = str(Path(__file__).resolve().parents[2])
CACHE = os.path.join(ROOT, 'pdf_text_cache')
os.makedirs(CACHE, exist_ok=True)

B1_ALIAS = {
    'mathematics': 'math', 'science': 'science', 'english-language': 'english',
    'ghanaian-language': 'ghanaian_language', 'history': 'history',
    'owop': 'owop', 'rme': 'rme', 'creative-arts': 'creative_arts',
}

def db_path(sid, g):
    if g == 'B1':
        return os.path.join(ROOT, f'{B1_ALIAS[sid]}_curriculum_db_clean.json')
    return os.path.join(ROOT, 'data/curriculum', f'{sid}_{g}_curriculum_db_clean.json')

PDFS = [
    ('math_B1-B3.pdf',                 'mathematics',         [1, 2, 3]),
    ('science_B1-B3.pdf',              'science',             [1, 2, 3]),
    ('english_B1-B3.pdf',              'english-language',    [1, 2, 3]),
    ('gh_lang_b1b3.pdf',               'ghanaian-language',   [1, 2, 3]),
    ('creative_arts_B1-B3.pdf',        'creative-arts',       [1, 2, 3]),
    ('owop_B1-B3.pdf',                 'owop',                [1]),
    ('history.pdf',                    'history',             [1, 2, 3, 4, 5, 6]),
    ('rme_B1-B6.pdf',                  'rme',                 [1, 2, 3, 4, 5, 6]),
    ('mathematics_B4-B6.pdf',          'mathematics',         [4, 5, 6]),
    ('science_B4-B6.pdf',              'science',             [4, 5, 6]),
    ('english_B4-B6.pdf',              'english-language',    [4, 5, 6]),
    ('ghanaian_language_B4-B6.pdf',    'ghanaian-language',   [4, 5, 6]),
    ('creative_arts_B4-B6.pdf',        'creative-arts',       [4, 5, 6]),
    ('owop_B4-B6.pdf',                 'owop',                [4, 5, 6]),
    ('mathematics_CCP_B7-B9_draft.pdf','mathematics',         [7, 8, 9]),
    ('science_CCP_B7-B9.pdf',          'science',             [7, 8, 9]),
    ('english_CCP_B7-B9.pdf',          'english-language',    [7, 8, 9]),
    ('ghanaian_language_CCP_B7-B9.pdf','ghanaian-language',   [7, 8, 9]),
    ('rme_CCP_B7-B9.pdf',              'rme',                 [7, 8, 9]),
    ('computing_CCP_B7-B9.pdf',        'computing',           [7, 8, 9]),
    ('social_studies_CCP_B7-B9.pdf',   'social-studies',      [7, 8, 9]),
    ('career_tech_CCP_B7-B9.pdf',      'career-technology',   [7, 8, 9]),
    ('creative_arts_design_CCP_B7-B9.pdf', 'creative-arts-design', [7, 8, 9]),
    ('french_CCP_B7-B9.pdf',           'french',              [7, 8, 9]),
]

# Documented NaCCA-print misprints, verified against document structure.
# {(subject, grade): {code: reason}} - code absent verbatim from PDF but authentic.
KNOWN_EXCEPTIONS = {
    ('history', 'B5'): {
        'B5.5.3.1.2': 'Printed as B4.5.3.1.2 inside the B5 body (grade digit misprint). '
                      'Sits in Strand 5: Journey to Independence, Sub-strand 3: The 1948 Riots '
                      'And After, CS B5.5.3.1; indicator tail 5.3.1.2 matches. Restored as B5.5.3.1.2.'
    },
}

# grade + (dot/space-separated) 3-6 following numbers, dots REQUIRED between later parts
TOK = re.compile(r'B\s*(\d)(?:\s*/\s*JHS\s*\d)?(?:\s*[.]\s*|\s+)\d+(?:\s*[.]\s*\d+){2,5}')

def norm_text(t):
    return re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()

def pdf_text(pdf):
    """Extract (cached) full text of a PDF."""
    h = hashlib.md5(pdf.encode()).hexdigest()[:10]
    gz = os.path.join(CACHE, f'{h}.txt.gz')
    if os.path.exists(gz):
        with gzip.open(gz, 'rt', encoding='utf-8', errors='ignore') as f:
            return f.read()
    reader = PdfReader(os.path.join(ROOT, pdf))
    pages = []
    for pg in reader.pages:
        try:
            pages.append(pg.extract_text() or '')
        except Exception:
            pages.append('')
    text = '\n'.join(pages)
    with gzip.open(gz, 'wt', encoding='utf-8', errors='ignore') as f:
        f.write(text)
    return text

def extract_codes(text):
    """Normalized 5-part indicator codes present in text."""
    out = set()
    for tok in TOK.finditer(text):
        t = re.sub(r'JHS\s*\d', '', tok.group(0))
        nums = re.findall(r'\d+', t)
        if len(nums) == 5:
            out.add('B' + '.'.join(nums))
    return out

def main():
    pdf_cache = {}
    results = []
    for pdf, sid, grades in PDFS:
        path = os.path.join(ROOT, pdf)
        if not os.path.exists(path):
            for g in grades:
                results.append({'pdf': pdf, 'subject': sid, 'grade': f'B{g}',
                                'status': 'SKIP', 'note': 'source PDF missing'})
            continue
        if pdf not in pdf_cache:
            pdf_cache[pdf] = pdf_text(pdf)
        text = pdf_cache[pdf]
        codes_in_pdf = extract_codes(text)
        for g in grades:
            dbp = db_path(sid, f'B{g}')
            if not os.path.exists(dbp):
                results.append({'pdf': pdf, 'subject': sid, 'grade': f'B{g}',
                                'status': 'SKIP', 'note': 'no DB (expected for OWOP B2/B3)'})
                continue
            db = json.load(open(dbp))
            db_codes = set(db.keys())
            pdf_g = {c for c in codes_in_pdf if c.startswith(f'B{g}.')}
            missing_in_pdf = sorted(db_codes - pdf_g)
            exceptions = KNOWN_EXCEPTIONS.get((sid, f'B{g}'), {})
            explained = [c for c in missing_in_pdf if c in exceptions]
            unexplained = [c for c in missing_in_pdf if c not in exceptions]
            extra_in_pdf = sorted(pdf_g - db_codes)
            cov = round(100 * len(db_codes & pdf_g) / max(1, len(pdf_g)), 1)
            valid = round(100 * (len(db_codes) - len(unexplained)) / max(1, len(db_codes)), 1)
            status = 'PASS' if not unexplained else ('WARN' if valid >= 95 else 'FAIL')
            results.append({
                'pdf': pdf, 'subject': sid, 'grade': f'B{g}', 'status': status,
                'db_n': len(db_codes), 'pdf_n': len(pdf_g),
                'valid_pct': valid, 'coverage_pct': cov,
                'missing_in_pdf': unexplained,
                'explained_exceptions': explained,
                'extra_in_pdf_count': len(extra_in_pdf),
                'extra_in_pdf_sample': extra_in_pdf[:8],
            })
    npass = sum(1 for r in results if r['status'] == 'PASS')
    nwarn = sum(1 for r in results if r['status'] == 'WARN')
    nfail = sum(1 for r in results if r['status'] == 'FAIL')
    nskip = sum(1 for r in results if r['status'] == 'SKIP')
    print(f'AUDIT B - code cross-check vs PDFs | PASS {npass} | WARN {nwarn} | FAIL {nfail} | SKIP {nskip}')
    for r in results:
        if r['status'] == 'SKIP':
            print(f"[SKP] {r['subject']:22s} {r['grade']:3s} {r['pdf']:38s} {r['note']}")
            continue
        flag = {'PASS': 'OK ', 'WARN': 'WRN', 'FAIL': 'FHL'}[r['status']]
        print(f"[{flag}] {r['subject']:22s} {r['grade']:3s} {r['pdf']:38s} db={r['db_n']:4d} pdf={r['pdf_n']:4d} valid={r['valid_pct']:5.1f}% coverage={r['coverage_pct']:5.1f}%")
        if r.get('explained_exceptions'):
            print(f'      ~ verified exception(s) ({len(r["explained_exceptions"])}): {r["explained_exceptions"]} - see KNOWN_EXCEPTIONS')
        if r['missing_in_pdf']:
            print(f'      ! DB codes NOT found in PDF ({len(r["missing_in_pdf"])}): {r["missing_in_pdf"][:10]}')
        if r['extra_in_pdf_count']:
            print(f'      · in PDF but not DB: {r["extra_in_pdf_count"]} e.g. {r["extra_in_pdf_sample"]}')
    json.dump(results, open(os.path.join(ROOT, 'audit_b_results.json'), 'w'), indent=1)

    # ---- B1 rich-description authenticity ----
    print('\nAUDIT B2 - B1 rich ind_desc text found verbatim in source PDF?')
    auth = []
    for sid, stem in B1_ALIAS.items():
        dbp = os.path.join(ROOT, f'{stem}_curriculum_db_clean.json')
        pdfname = next(p for p, s, gs in PDFS if s == sid and 1 in gs)
        if pdfname not in pdf_cache:
            pdf_cache[pdfname] = pdf_text(pdfname)
        ntext = norm_text(pdf_cache[pdfname])
        db = json.load(open(dbp))
        hit = miss = 0
        misses = []
        for code, v in db.items():
            d = norm_text(str(v.get('ind_desc', '')))
            if len(d) < 15:
                miss += 1; misses.append(code); continue
            if d in ntext:
                hit += 1
            else:
                miss += 1; misses.append(code)
        pct = round(100 * hit / max(1, hit + miss), 1)
        auth.append({'subject': sid, 'hit': hit, 'miss': miss, 'pct': pct, 'miss_codes': misses})
        print(f"  {sid:22s} verbatim {hit:3d}/{hit+miss:3d} ({pct:5.1f}%)  not-found: {misses[:6]}")
    json.dump(auth, open(os.path.join(ROOT, 'audit_b2_results.json'), 'w'), indent=1)

if __name__ == '__main__':
    main()
