#!/usr/bin/env python3
"""Check a deployed Beacon app from the outside, without a browser.

Answers the two questions a green build does not:

  1. **Did the deploy get its Firebase config?** (P0-1) — the build writes
     `build-info.json` into `dist/`, so the deployed copy says whether the six
     `VITE_FIREBASE_*` values were present at build time. Without them the app
     renders the setup notice instead of the portal, and nothing else in the
     pipeline notices.
  2. **Is it serving the curriculum bundle this checkout builds?** — the same
     file carries the `bundleHash` from `public/curriculum/_BUILD_REPORT.json`
     (the hash the service worker names its cache after), and `sw.js` must read
     it too, or returning installs keep a stale cache.

It also fetches the SPA shell and one curriculum file, because a rewrite that
swallows `/curriculum/*` is a real deployment mistake.

    python3 scripts/verify_deploy.py https://beacon.example.com
    make verify-deploy URL=https://beacon.example.com

Exit code is 1 if anything a teacher would hit is wrong. With no URL (or
`--offline-check`) it only checks the local pieces CI can check.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "public" / "curriculum" / "_BUILD_REPORT.json"


def get(url: str, timeout: int = 20):
    """(status, body) — never raises for an HTTP error, only for transport ones."""
    req = urllib.request.Request(url, headers={"User-Agent": "beacon-verify-deploy"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001 — any transport failure is the same answer here
        return None, str(e).encode()


def local_bundle_hash() -> str | None:
    try:
        return json.loads(REPORT.read_text(encoding="utf-8")).get("bundleHash")
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="deploy base URL, e.g. https://beacon.example.com")
    ap.add_argument("--offline-check", action="store_true",
                    help="only compare the local bundle hash against public/sw.js")
    args = ap.parse_args()

    local = local_bundle_hash()
    problems, notes = [], []

    if not local:
        problems.append("public/curriculum/_BUILD_REPORT.json has no bundleHash — run "
                        "scripts/build_app_curriculum.py")
    sw = (ROOT / "public" / "sw.js").read_text(encoding="utf-8")
    if "bundleHash" not in sw or "_BUILD_REPORT.json" not in sw:
        problems.append("public/sw.js no longer names its cache after the bundle hash")

    if not args.url or args.offline_check:
        for line in problems:
            print(f"  x {line}")
        if problems:
            return 1
        print(f"  ok  bundle hash {local}; sw.js reads it from _BUILD_REPORT.json")
        return 0

    base = args.url.rstrip("/")

    status, body = get(f"{base}/build-info.json")
    if status != 200:
        problems.append(f"GET /build-info.json -> {status} (the deploy predates this check, or a "
                        f"rewrite swallows it): {body[:80]!r}")
        remote = {}
    else:
        try:
            remote = json.loads(body)
        except json.JSONDecodeError:
            remote = {}
            problems.append("GET /build-info.json did not return JSON")
        if remote and not remote.get("firebaseConfigured"):
            problems.append("the deploy was built WITHOUT Firebase config — missing "
                            f"{remote.get('missingEnv')}. Set the values on Vercel for Production "
                            "AND Preview, then redeploy (docs/build-deploy.md)")
        elif remote:
            notes.append(f"Firebase config present (project {remote.get('projectId')})")
        if remote.get("bundleHash") and local and remote["bundleHash"] != local:
            problems.append(f"the deploy serves bundle {remote['bundleHash']} but this checkout "
                            f"builds {local} — the curriculum changed since the last deploy")
        if remote:
            notes.append(f"commit {remote.get('commit')}, built {remote.get('builtAt')}")

    status, body = get(f"{base}/")
    if status != 200 or b'id="root"' not in body:
        problems.append(f"GET / -> {status}; the SPA shell did not come back (rewrite broken?)")
    else:
        notes.append("SPA shell served")

    status, body = get(f"{base}/curriculum/grades.json")
    if status != 200:
        problems.append(f"GET /curriculum/grades.json -> {status} — the bundle is not deployed")
    else:
        try:
            grades = json.loads(body)
            notes.append(f"curriculum bundle served: {len(grades)} grades")
        except json.JSONDecodeError:
            problems.append("GET /curriculum/grades.json did not return JSON")

    status, body = get(f"{base}/curriculum/schedules/b1-mathematics.json")
    if status != 200:
        problems.append(f"GET /curriculum/schedules/b1-mathematics.json -> {status} — the "
                        "per-subject schedules are missing, so planners would come up empty")
    else:
        notes.append("per-subject schedules served")

    status, body = get(f"{base}/sw.js")
    if status != 200:
        problems.append(f"GET /sw.js -> {status} — offline mode would never install")
    elif b"bundleHash" not in body:
        problems.append("the deployed sw.js does not read the bundle hash — it is an older build")

    for line in notes:
        print(f"  ok  {line}")
    for line in problems:
        print(f"  x {line}")
    print()
    if problems:
        print(f"{len(problems)} problem(s) — the deployed app would not work for a teacher.")
        return 1
    print("Deploy looks right. Now drive the flows by hand (docs/verification.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
