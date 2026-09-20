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
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "public" / "curriculum" / "_BUILD_REPORT.json"

# Every deploy path this checks. `src/deployCheck.test.js` compares this list with
# verify_deploy.mjs's, so the two implementations cannot drift apart.
CHECKED_PATHS = [
    "/build-info.json",
    "/",
    "/curriculum/grades.json",
    "/curriculum/schedules/b1-mathematics.json",
    "/sw.js",
]


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


def read_env_file(path: Path) -> tuple[dict, str, int]:
    """(env, encoding, non-blank lines) for a dotenv file, decoded from the bytes.

    Windows PowerShell writes `>` and `Out-File` as UTF-16LE, so a perfectly good
    `.env.local` read as UTF-8 is a string full of NUL bytes and every key
    "disappears". Same handling as scripts/verify_deploy.mjs: byte-order mark
    first, then a NUL-byte sniff, then `utf-8`.
    """
    raw = path.read_bytes()
    encoding = "UTF-8"
    if raw[:2] == b"\xff\xfe":
        text, encoding = raw[2:].decode("utf-16-le"), "UTF-16LE"
    elif raw[:2] == b"\xfe\xff" and len(raw) % 2 == 0:
        text, encoding = raw[2:].decode("utf-16-be"), "UTF-16BE"
    else:
        text = raw.decode("utf-8", errors="replace")
        if text.startswith("\ufeff"):
            text = text[1:]
        if len(raw) % 2 == 0 and "\x00" in text[:400]:
            text, encoding = raw.decode("utf-16-le", errors="replace"), "UTF-16LE (no byte-order mark)"

    env = {}
    lines = text.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        env[match.group(1)] = value
    return env, encoding, len([line for line in lines if line.strip()])


def pinned_project() -> str | None:
    """The project `.firebaserc` sends `firebase deploy` to, or None."""
    try:
        return json.loads((ROOT / ".firebaserc").read_text(encoding="utf-8")).get("projects", {}).get("default")
    except Exception:  # noqa: BLE001
        return None


FIREBASE_KEYS = [
    "VITE_FIREBASE_API_KEY",
    "VITE_FIREBASE_AUTH_DOMAIN",
    "VITE_FIREBASE_PROJECT_ID",
    "VITE_FIREBASE_STORAGE_BUCKET",
    "VITE_FIREBASE_MESSAGING_SENDER_ID",
    "VITE_FIREBASE_APP_ID",
]


def looks_like_html(body: bytes) -> bool:
    """A 200 that is the app shell: the rewrite caught a path the deploy lacks."""
    return bool(re.match(rb"\s*(<!doctype|<html)", body[:200], re.IGNORECASE))


def local_file(url_path: str):
    """(byte length, parsed JSON or None) for the same file in this checkout."""
    file = ROOT / "public" / url_path.lstrip("/")
    if not file.exists():
        return None
    raw = file.read_bytes()
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001 — not JSON is a legitimate answer here
        parsed = None
    return len(raw), parsed


def kb(n: int) -> str:
    return f"{n / 1024:.1f} KB" if n < 10240 else f"{n / 1024:.0f} KB"


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

    # The app and the rules have to live in the same Firebase project, and they are
    # configured in two different files: `.env.local` (Vite, gitignored) and
    # `.firebaserc` (the CLI, committed). `firebase deploy` follows `.firebaserc`,
    # so a mismatch publishes the rules to a project the app never talks to — and
    # leaves the live one on whatever rules it has.
    env_path = ROOT / ".env.local"
    app_project = None
    if env_path.exists():
        env, encoding, _ = read_env_file(env_path)
        app_project = env.get("VITE_FIREBASE_PROJECT_ID") or None
        missing_env = [key for key in FIREBASE_KEYS if not env.get(key)]
        if missing_env:
            problems.append(f".env.local does not define: {', '.join(missing_env)} "
                            f"(read as {encoding})")
    pinned = pinned_project()
    if not pinned:
        notes.append(".firebaserc has no default project — `firebase deploy` needs --project")
    elif app_project and pinned != app_project:
        problems.append(f".firebaserc pins `{pinned}` but the app is configured for `{app_project}` "
                        "— `firebase deploy` (and `make deploy-rules`) would publish the rules and "
                        "indexes to the project the app never talks to")
        notes.append(f"fix: `firebase use {app_project}` (writes .firebaserc), or deploy with "
                     f"`--project {app_project}`")
    elif app_project:
        notes.append(f".firebaserc pins the same project the app uses ({pinned})")

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
        if looks_like_html(body):
            remote = {}
            problems.append("GET /build-info.json returned the SPA shell — this deploy predates "
                            "build-info.json, so it is not the commit that was pushed. On Vercel, "
                            "check Settings → Git → Production Branch: production deploys `main` "
                            "unless it is changed, and `main` is still the old snapshot")
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
            if remote.get("projectId") and app_project and remote["projectId"] != app_project:
                problems.append(f"the deploy was built for project `{remote['projectId']}`, but this "
                                f"checkout's .env.local configures `{app_project}` — the deployment "
                                "and your local app are talking to different Firebase projects")

    status, body = get(f"{base}/")
    if status != 200 or b'id="root"' not in body:
        problems.append(f"GET / -> {status}; the SPA shell did not come back (rewrite broken?)")
    else:
        notes.append("SPA shell served")

    # A 200 is not enough: the SPA rewrite answers every path with index.html, so a
    # file the deploy does not have looks like a small success. Compare the shape
    # and the size against this checkout — that is what catches a deploy serving a
    # different branch, where everything that exists in both looks perfect.
    shell_for_missing_file = False
    for path in [p for p in CHECKED_PATHS if p.startswith("/curriculum/")]:
        status, body = get(f"{base}{path}")
        if status != 200:
            problems.append(f"GET {path} -> {status} — the " +
                            ("bundle is not deployed" if path.endswith("grades.json") else
                             "per-subject schedules are missing, so planners would come up empty"))
            continue
        if looks_like_html(body):
            shell_for_missing_file = True
            local = local_file(path)
            problems.append(f"GET {path} returned the SPA shell, not the file — this deploy does "
                            f"not contain {path}" + (f" (this checkout has it, {kb(local[0])})" if local else ""))
            continue
        try:
            served = json.loads(body)
        except json.JSONDecodeError:
            problems.append(f"GET {path} did not return JSON — the file is not what the app expects")
            continue
        local = local_file(path)
        if local is None:
            notes.append(f"{path} is served ({kb(len(body))}) — no local copy to compare")
        elif isinstance(served, list) and isinstance(local[1], list) and len(served) != len(local[1]):
            problems.append(f"{path} holds {len(served)} entries; this checkout's copy holds "
                            f"{len(local[1])} — the deploy is serving a different curriculum")
        else:
            drift = abs(len(body) - local[0]) / local[0]
            if drift > 0.10:
                problems.append(f"{path} is {kb(len(body))} on the deploy but {kb(local[0])} in this "
                                f"checkout ({round(drift * 100)}% different) — the deploy is serving "
                                "a different curriculum than this checkout")
            else:
                notes.append(f"{path} matches this checkout ({kb(len(body))}"
                             + (f", {len(served)} entries)" if isinstance(served, list) else ")"))
    if shell_for_missing_file:
        notes.append("a curriculum file coming back as the app shell means the rewrite served "
                     "index.html — almost always the wrong branch: Vercel deploys the Production "
                     "Branch to this domain (main by default), not the branch that was pushed")

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
