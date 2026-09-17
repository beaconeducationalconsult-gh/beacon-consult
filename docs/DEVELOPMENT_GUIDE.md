# Beacon Consult Development Guide

A staged path from the scaffold you already have to a real, multi-subject,
multi-school system. Each stage has a goal, why it comes at that point (not
earlier, not later), concrete tasks, sample code where it earns its place,
and a "definition of done" you can actually check against — not a vibe.

Work the stages in order. Each one assumes the previous is genuinely done,
not "mostly working." The kernel/module boundary only pays off if you
resist the urge to skip ahead and special-case something in the service
layer because a module isn't ready yet.

---

## Stage 0 — Environment

**Goal:** a machine that can run `boot-check` cleanly.

- Python 3.11+, on PATH as `python` (see the PATH note if you're on Windows
  — the Store alias for `python3` will burn an afternoon if you don't
  disable it).
- A virtual environment, so `pip install` doesn't fight with anything else
  on the machine:
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate      # PowerShell
  # source .venv/bin/activate   # macOS/Linux
  pip install -r requirements.txt
  ```
- Git, and a repo pushed somewhere (GitHub/GitLab) — you'll want CI by
  Stage 5, so start with version control from day one, not as an
  afterthought once things are "working."

**Definition of done:** `python tools/ncosctl.py boot-check` prints
`All modules healthy.` on a fresh clone.

---

## Stage 1 — Kernel foundations (you have this)

**Goal:** the contract every subject builds against is stable before you
write a second subject.

What's already in the starter: `SubjectModule`, `MaterialDoc`/`Section`/
`Block`, the registry's boot sequence, and the docx driver. Don't add
fields to `Indicator` or new `Block` types speculatively — add them when a
real subject needs one, otherwise the interface accumulates unused surface
area that every future module has to at least think about.

**One thing worth doing now, before Stage 2:** write the interface's own
test — not a subject's test, the *contract's* test. Any module that claims
to implement `SubjectModule` should be checkable generically:

```python
# tests/test_module_contract.py
import pytest
from ncos.kernel.interface import SubjectModule

def assert_valid_module(module: SubjectModule, sample_grade: str):
    """Run against every module — math, and every subject after it."""
    assert module.id and module.display_name
    assert module.grades, "a module with no grades can never be requested"
    problems = module.validate()
    assert problems == [], f"{module.id} failed self-validation: {problems}"

    indicators = module.load_indicators(sample_grade)
    assert indicators, f"{module.id} returned no indicators for {sample_grade}"
    codes = [i.code for i in indicators]
    assert len(codes) == len(set(codes)), "duplicate indicator codes"

def test_math_module():
    from ncos.modules.math.module import get_module
    assert_valid_module(get_module(), sample_grade="B4")
```

This is the test you copy-paste one line of (`from ... import get_module`)
for every new subject in Stage 4. It's also what CI runs in Stage 5 — a
module that violates the contract fails the build, not just the boot
report.

**Definition of done:** `test_math_module` passes, and you have a
reusable `assert_valid_module` other subjects will call into.

---

## Stage 2 — Prove the loop with one subject (you have this)

**Goal:** one subject, fully working, end to end — indicator → lesson
plan → real `.docx` on disk — before touching a second subject.

This is deliberate sequencing, not laziness: any design mistake in the
interface is cheap to fix with one module implementing it, and expensive
once twelve do. Math is that proof. Don't move to Stage 3 until you've
generated a scheme of work too, not just a lesson plan — schemes exercise
`TableBlock`, which lesson plans in the starter don't.

```powershell
python tools/ncosctl.py generate-sample math B4 B4.1.1.1
```

**Definition of done:** you've generated both a lesson plan and a scheme
of work from the math module, opened both `.docx` files, and they look
like something a teacher could use without embarrassment.

---

## Stage 3 — Curriculum ingestion pipeline

**Goal:** turn the 24 NaCCA source PDFs into the `data/curriculum/`
JSON your modules read — the "boot source" in the OS metaphor. This is
the part of the original project you'd already built once; it's being
re-homed here, not redesigned.

**Why now, not earlier:** Stage 2 proved the *consumption* side of the
data (a module reading `B4.json`) works. Now you build the *production*
side. Keeping them separate stages means a parsing bug never gets
confused with an interface bug — you already know the interface is sound
from Stage 2.

**Structure:**

```
tools/ingest/
  parse_pdf.py       # PDF -> raw extracted text/tables
  extract_indicators.py   # raw text -> Indicator-shaped records
  build_curriculum.py     # writes data/curriculum/<subject>/<grade>.json
```

Each subject's PDFs likely have quirks (different heading styles, table
layouts) — resist building one universal parser. A per-subject parsing
profile, even if 80% shared code, will save you from a parser that's
correct for Math and silently wrong for Creative Arts:

```python
# tools/ingest/build_curriculum.py
from pathlib import Path
import json

def build(subject: str, grade: str, indicators: list[dict], out_dir: Path):
    """The one function every subject's ingestion script calls at the end —
    this is what guarantees every subject's output JSON has the same
    shape, even if the parsing that got there differs wildly."""
    payload = {"grade": grade, "subject": subject, "indicators": indicators}
    out_path = out_dir / subject / f"{grade}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return out_path
```

Add a validation pass here too — catch bad extraction (empty indicator
text, duplicate codes) at ingestion time, not at boot time three weeks
later when you've forgotten what B4 Math's PDF layout looks like.

**Definition of done:** running the ingestion pipeline for math from a
real source PDF reproduces (or improves on) the hand-written
`B4.json` sample from the starter, and `boot-check` still passes after
swapping it in.

---

## Stage 4 — Roll out remaining subjects

**Goal:** all 13 subjects loaded and passing `assert_valid_module`.

Now the template earns its keep. Per subject:

1. `cp -r ncos/modules/_template ncos/modules/<subject_id>`
2. Fill in `module.json`.
3. Implement `load_indicators` (using Stage 3's ingestion output),
   `validate`, `generate_lesson_plan`, `generate_scheme_of_work`.
4. Add a contract test (copy the one line from `test_math_module`).
5. `boot-check`.

**Where subjects will actually differ from Math** — decide these
per-subject, don't force a shared answer:

- **Creative Arts / PE** have no single numeric "indicator sequence" the
  way Math does — content standards may matter more than fine-grained
  codes. This is exactly what `Indicator.extra` is for: don't add new
  top-level fields to the shared dataclass, put subject-specific shape
  in `extra` and let the module interpret it.
- **French** needs UTF-8 handling for diacritics through the whole
  pipeline — verify this at Stage 3 (ingestion), not discovered here.
- **PE** likely wants a `CalloutBlock` for safety notes in every lesson
  plan — that's a case for the `Block` types already in the interface,
  not a reason to extend it.

**Order matters less than you'd think** — do 2-3 "easy" subjects first
(structurally similar to Math) to build momentum, then the 2-3 "hard"
ones (Creative Arts, PE) while the interface is still fresh in your head
and cheap to adjust if one of them genuinely needs something new.

**Definition of done:** `list-modules` shows all 13 subjects, `boot-check`
is clean, and every module has a passing contract test.

---

## Stage 5 — Testing & CI

**Goal:** the boot report and contract tests run automatically, not just
when you remember to.

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: PYTHONPATH=. python tools/ncosctl.py boot-check
      - run: pytest
```

Add `pytest` and a `requirements-dev.txt`. The `boot-check` step failing
the build is more important than it looks — it's the difference between
"a module broke" being caught in nine seconds on a PR versus discovered
by a teacher at generation time.

**Definition of done:** a PR that breaks any module's `validate()` fails
CI before it can merge.

---

## Stage 6 — Harden the Material Service

**Goal:** the API survives contact with a real Portal — auth, structured
errors, and logging, none of which exist in the starter yet.

- **Auth**: at minimum, an API key or session token checked before any
  `/api/generate/*` route runs. Don't build a full user system yet —
  that's Stage 8. A single shared secret for the Portal-to-Service call
  is enough for now.
- **Structured errors**: the starter returns raw strings; make errors
  consistent so the Portal can render them without string-matching:
  ```python
  def api_error(code: str, message: str, status: int):
      return jsonify({"error": {"code": code, "message": message}}), status
  ```
- **Logging**: log every generation request (subject, grade, indicator,
  who asked) — this is your only visibility once the Portal is the thing
  users touch, not `ncosctl`.

**Definition of done:** hitting the API with a bad subject, a missing
indicator, and a valid request all produce distinguishable, loggable
outcomes — none of them a raw Python traceback reaching the client.

---

## Stage 7 — The Portal (user space)

**Goal:** teachers can request a lesson plan through a UI, not `curl`.

This is the first point where "user space" stops being a metaphor and
becomes an actual trust boundary — the Portal runs in a browser, is not
trusted with direct data access, and must go through the Service's API
for everything, exactly like the starter's architecture already assumes.

- Framework choice is yours (the original project used React — no reason
  to change that). Given the PWA requirement from your original brief,
  set up a service worker early, not bolted on at the end — an installed
  PWA with no offline story is just a bookmark.
- The core screen is simple by design: pick subject → grade → term/week →
  indicator → generate. Resist adding features here before this loop is
  solid; every extra control is one more thing that can be wrong in front
  of a teacher.
- **What to cache for offline use**: the curriculum browse data (subjects,
  grades, indicators — read-only, changes rarely) is what a service worker
  should cache aggressively. Generation itself needs the Service, so it's
  reasonably online-only — don't over-engineer offline document generation
  in v1.

**Definition of done:** a teacher can open the Portal, pick an indicator,
and download a `.docx` — with the curriculum list still browsable if
their connection drops.

---

## Stage 8 — Access control & multi-tenancy

**Goal:** schools and teachers are real entities with real scope, not a
shared API key.

- A teacher belongs to a school; a school has a plan/tier.
- `school_context` already exists on `GenerationRequest` in the starter —
  this is where it stops being a free-form dict passed through and
  becomes something the Service populates from an authenticated session,
  not something the client can claim to be.
- Rate-limit or gate generation by plan tier here — this is the natural
  home for "free tier: 10 generations/month" style logic, and it belongs
  in the Service, never in a subject module (a module has no business
  knowing about billing).

**Definition of done:** two different school accounts cannot see or
generate each other's usage history, and an unauthenticated request to
`/api/generate/*` is rejected before it reaches the registry.

---

## Stage 9 — Curriculum package format

**Goal:** a NaCCA curriculum revision is an *install*, not a manual file
edit — this is the "package manager" piece flagged as designed-but-not-
built in the starter's README.

- Version `data/curriculum/<subject>/` directories explicitly — e.g.
  `data/curriculum/math/2019/` vs `data/curriculum/math/2024/`.
- A module declares which curriculum version it's built against in
  `module.json` (`curriculum_source`), and the registry can refuse to
  boot a module pointed at a curriculum version that no longer exists —
  same "fail loud at boot" principle as everywhere else in the kernel.
- This is also where you'd support a school choosing to stay on last
  year's scheme mid-term rather than being force-migrated — a real
  requirement once this is live in actual schools.

**Definition of done:** you can add a second, differently-versioned copy
of one subject's curriculum, point a module at either version via
manifest, and both boot cleanly side by side.

---

## Stage 10 — Question bank

**Goal:** implement the optional `generate_questions` capability the
interface already has a slot for.

- Add `"questions"` to a module's `capabilities` only once it actually
  implements `generate_questions` — the interface raises
  `NotImplementedError` by default specifically so a half-finished
  capability doesn't silently return nothing.
- Question generation is the subject where you'll most want subject-
  specific logic (numeric questions for Math, cloze/comprehension for
  Language) — this is a good test of whether the interface still holds up
  once a genuinely different content type goes through it. If it strains,
  that's useful signal for a `Question` model refinement, not a sign to
  special-case it in the Service.

**Definition of done:** at least one subject generates a real question
set, gated correctly by the `capabilities` check the Service already
performs for other capabilities.

---

## Stage 11 — Deployment

**Goal:** the Service and Portal run somewhere teachers can reach, not
just on your laptop.

- Containerize the Service (`Dockerfile`, standard Flask pattern — gunicorn
  in front of it for anything beyond local dev).
- Decide hosting for the two pieces separately: the Portal is static/PWA
  and can go almost anywhere (Vercel, Netlify, S3+CDN); the Service needs
  a real process host (Fly.io, Render, a small VM).
- Curriculum data (`data/curriculum/`) needs to ship with the Service
  deployment — decide now whether it's baked into the container image
  (simple, redeploy to update) or mounted/fetched separately (flexible,
  more moving parts). Baked-in is the right default until you have a
  concrete reason otherwise.

**Definition of done:** a teacher on a real device, on real Ghanaian
mobile networks, can load the Portal and generate a document.

---

## What to build in the meantime, informally

Two things don't need their own stage but should exist by the time you
hit Stage 7:

- **A `CHANGELOG.md`** — once real schools are using this, "what changed
  and when" matters more than you'll expect at Stage 0.
- **A `docs/DECISIONS.md`** — a running log of choices like the
  `MaterialDoc` separation or the curriculum versioning scheme, with a
  sentence on *why*. Six months from now, "why doesn't a module render
  its own docx" will not be an obvious question to whoever's reading the
  code — possibly including you.
