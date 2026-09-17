#!/usr/bin/env python3
"""Beacon Material Service — HTTP wrapper around the document generators.

Lets the web portal produce Schemes of Learning and Records of Work on demand,
pre-printed with the requesting school's details.

Why subprocesses instead of importing the generators
----------------------------------------------------
`generate_schemes.py` and `generate_records_of_work.py` keep their output paths
in module-level globals (OUT / JSON_OUT / DOCX_OUT) that main() reassigns.
Importing and monkey-patching those is fragile. Shelling out runs the exact CLI
path that is already tested, and future generator changes need no changes here.
The cost is roughly 0.3s of interpreter startup, which is invisible against
0.4s (scheme) and 4s (record) generation times.

Endpoints
---------
    GET  /health    liveness, and whether the curriculum data is visible
    GET  /catalog   grades + subjects available (drives the portal dropdowns)
    POST /generate  one .docx, or a .zip when the request spans several subjects

Security
--------
Only values found in the allow-lists below ever reach the subprocess, and the
command is passed as an argv list with shell=False, so request data cannot
inject extra arguments. Free-text branding values are length-bounded.
Set REQUIRE_AUTH=1 to demand a Firebase ID token.

Run locally
-----------
    pip install -r service/requirements.txt
    python service/main.py                      # http://127.0.0.1:8080

Deploy (Cloud Run — africa-south1 is the closest region to Ghana)
-----------------------------------------------------------------
Build from the repo root, then deploy the image. Do NOT use
`run deploy --source .`: Cloud Run looks for a Dockerfile in the source
directory, ours is at service/Dockerfile, so it falls back to buildpacks,
finds app/package.json and builds a Node image instead of this Flask app.

    gcloud builds submit --tag gcr.io/$PROJECT/beacon-materials \
        --file service/Dockerfile .

    gcloud run deploy beacon-materials \
        --image gcr.io/$PROJECT/beacon-materials \
        --region africa-south1 --allow-unauthenticated \
        --timeout 300 --memory 1Gi \
        --set-env-vars "REQUIRE_AUTH=1,ALLOWED_ORIGINS=https://YOUR-APP.vercel.app"

See docs/DEPLOYMENT.md for the full walkthrough and a verification checklist.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from flask import Flask, jsonify, request, send_file

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PY = sys.executable
TIMEOUT = int(os.environ.get("GENERATE_TIMEOUT", "300"))
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "0") == "1"
MAX_FIELD = 120

sys.path.insert(0, str(TOOLS))

app = Flask(__name__)

# ── CORS ───────────────────────────────────────────────────────────────────
# The deployed portal is served from a different origin (Vercel) than this
# service (Cloud Run), so the browser treats every call as cross-origin and
# sends an OPTIONS preflight before the real request. Without these headers
# the browser blocks the response and Generate silently fails in production
# even though the service returned 200.
#
# Set ALLOWED_ORIGINS to the portal's exact origin in production, e.g.
#   ALLOWED_ORIGINS=https://beacon-consult.vercel.app
# Comma-separate several if you use preview deployments. It defaults to "*"
# so local smoke tests keep working.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]


@app.before_request
def _cors_preflight():
    """Answer the browser's preflight without running the route."""
    if request.method == "OPTIONS":
        return ("", 204)


@app.after_request
def _cors_headers(resp):
    origin = request.headers.get("Origin", "")
    if ALLOWED_ORIGINS == ["*"]:
        resp.headers["Access-Control-Allow-Origin"] = "*"
    elif origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    # Generation can take ~30s; tell the browser not to preflight every call.
    resp.headers["Access-Control-Max-Age"] = "600"
    return resp


GENERATORS = {
    "scheme": TOOLS / "generate_schemes.py",
    "record": TOOLS / "generate_records_of_work.py",
}

# ── Allow-lists ────────────────────────────────────────────────────────────
# Request values are looked up here and never forwarded raw, so a hostile body
# cannot smuggle extra command-line arguments into the subprocess.
KINDS = ("scheme", "record")
GRADES = tuple(f"B{n}" for n in range(1, 10))
TERMS = ("1", "2", "3")

# `hod` exists only on the scheme cover; records has no such field.
BRANDING_FLAGS = {
    "scheme": {
        "school": "--school",
        "teacher": "--teacher",
        "class_name": "--class-name",
        "term": "--term",
        "year": "--year",
        "hod": "--hod",
    },
    "record": {
        "school": "--school",
        "teacher": "--teacher",
        "class_name": "--class-name",
        "term": "--term",
        "year": "--year",
    },
}

NO_STORE = {"Cache-Control": "no-store"}


# ── helpers ────────────────────────────────────────────────────────────────
def has_docx() -> bool:
    try:
        import docx  # noqa: F401
        return True
    except Exception:
        return False


def data_file_count() -> int:
    # Lesson files live in data/lessons/ since the restructure; the repo
    # root is no longer where data is kept.
    return len(list((ROOT / "data" / "lessons").glob("*_lessons_enriched.json")))


def subject_keys() -> set[str]:
    from generate_schemes import SUBJECTS
    return set(SUBJECTS)


def auth_ok() -> tuple[bool, str]:
    """Verify a Firebase ID token when REQUIRE_AUTH=1.

    Off by default so the service can be smoke-tested locally. Turn it on in
    any deployed environment — without it anyone who finds the URL can
    generate unlimited documents.
    """
    if not REQUIRE_AUTH:
        return True, ""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return False, "missing bearer token"
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        fb_auth.verify_id_token(header.split(" ", 1)[1])
        return True, ""
    except Exception:
        # Never leak the reason — it distinguishes expired from forged tokens.
        return False, "invalid token"


def zip_up(files: list[Path]) -> Path:
    """Bundle several documents into one archive next to the first file."""
    out = files[0].parent / "beacon_materials.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.name)
    return out


# ── routes ─────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({
        "ok": True,
        "python": sys.version.split()[0],
        "python_docx": has_docx(),
        "lesson_files": data_file_count(),
        "require_auth": REQUIRE_AUTH,
    }), (200 if has_docx() and data_file_count() else 503)


@app.get("/catalog")
def catalog():
    """Grades and subjects this service can generate, for portal dropdowns."""
    try:
        from generate_schemes import SUBJECTS, discover
        entries = discover()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"discovery failed: {exc}"}), 500

    by_grade: dict[str, list[dict]] = {}
    for subj, grade, _path in entries:
        sid, name = SUBJECTS[subj]
        by_grade.setdefault(grade, []).append(
            {"key": subj, "id": sid, "name": name})

    return jsonify({
        "kinds": list(KINDS),
        "grades": {
            g: sorted(by_grade.get(g, []), key=lambda s: s["name"])
            for g in GRADES
        },
    })


@app.post("/generate")
def generate():
    ok, err = auth_ok()
    if not ok:
        return jsonify({"error": err}), 401

    body = request.get_json(silent=True) or {}

    kind = str(body.get("kind", "")).lower()
    if kind not in KINDS:
        return jsonify({"error": f"kind must be one of {list(KINDS)}"}), 400

    grade = str(body.get("grade", "")).upper()
    if grade not in GRADES:
        return jsonify({"error": f"grade must be one of {list(GRADES)}"}), 400

    subject = body.get("subject")
    if subject is not None:
        subject = str(subject)
        if subject not in subject_keys():
            return jsonify({"error": f"unknown subject {subject!r}"}), 400

    per_term = bool(body.get("per_term"))

    term = body.get("term")
    if term is not None:
        term = str(term)
        if term not in TERMS:
            return jsonify({"error": f"term must be one of {list(TERMS)}"}), 400

    # A single term only exists as a per-term document, so force that mode and
    # filter afterwards.
    want_single_term = term is not None
    if want_single_term:
        per_term = True

    tmp = Path(tempfile.mkdtemp(prefix="beacon_"))
    try:
        cmd = [PY, str(GENERATORS[kind]), "--grade", grade, "--out", str(tmp)]
        if subject:
            cmd += ["--subject", subject]
        if per_term:
            cmd.append("--per-term")

        for key, flag in BRANDING_FLAGS[kind].items():
            value = body.get(key)
            if value:
                cmd += [flag, str(value)[:MAX_FIELD]]

        started = time.time()
        try:
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True,
                                  text=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return jsonify({"error": f"generation exceeded {TIMEOUT}s"}), 504

        if proc.returncode != 0:
            return jsonify({
                "error": "generator failed",
                "detail": proc.stderr[-2000:],
            }), 500

        produced = sorted((tmp / "docx").rglob("*.docx"))
        if not produced:
            return jsonify({
                "error": "generator produced no documents",
                "detail": proc.stderr[-2000:],
            }), 500

        if want_single_term:
            matched = [f for f in produced if f"Term{term}.docx" in f.name]
            if not matched:
                return jsonify({
                    "error": f"no document for term {term}",
                    "available": [f.name for f in produced],
                }), 404
            produced = matched

        elapsed = round(time.time() - started, 2)

        if len(produced) == 1:
            target = produced[0]
            return send_file(
                target,
                mimetype="application/vnd.openxmlformats-"
                         "officedocument.wordprocessingml.document",
                as_attachment=True,
                download_name=target.name,
            ), 200, NO_STORE

        bundle = zip_up(produced)
        return send_file(bundle, mimetype="application/zip",
                         as_attachment=True,
                         download_name=bundle.name), 200, NO_STORE

    finally:
        # send_file streams the response lazily in some WSGI setups, but Flask
        # has already read the bytes by the time send_file returns, so cleanup
        # here is safe.
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
