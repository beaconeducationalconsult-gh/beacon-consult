# NCOS Subject Module Interface

How subjects plug into the curriculum engine. The goal: adding Creative Arts
or French should mean writing one new module directory, not editing
`tools/generate_schemes.py`, `tools/generate_records_of_work.py`, and the
Material Service in three different places.

## Why this exists

Right now subject-specific logic is implicit — scattered across generator
scripts as `if subject == "math"` branches, or baked into how `data/curriculum/`
happens to be shaped for each subject. That works at 13 subjects. It will not
survive Creative Arts (rubric-based, no numeric indicators), French (needs
diacritics and a different question format), or PE (needs a safety-note
section no other subject has).

A subject module is the unit that owns everything subject-specific:
its slice of curriculum data, its document layout quirks, and its question
generation rules. The kernel (Curriculum Engine / Material Service) never
special-cases a subject by name again — it only calls the interface.

## Directory layout

```
modules/
  math/
    module.json          # manifest — see below
    module.py             # implements SubjectModule
    templates/
      lesson_plan.docx.j2 # or a python-docx builder function
      scheme.docx.j2
    schema.json           # subject-specific indicator schema, for validation
  creative_arts/
    module.json
    module.py
    templates/
    schema.json
  french/
    ...
```

Each module is self-contained. It reads from `data/curriculum/<subject>/`
(via `_paths.py`, unchanged) but owns *how that data is interpreted*.

## The manifest — `module.json`

```json
{
  "id": "math",
  "display_name": "Mathematics",
  "grades": ["KG1", "KG2", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"],
  "interface_version": "1.0",
  "module_version": "2024.1",
  "curriculum_source": "NaCCA Mathematics Curriculum 2019",
  "capabilities": ["lesson_plan", "scheme_of_work", "records_of_work", "questions"]
}
```

- `interface_version` — which version of the `SubjectModule` contract this
  module was built against. The registry refuses to load a module whose
  interface_version the kernel doesn't support, instead of failing halfway
  through a generation run.
- `capabilities` — not every subject needs to support every material type on
  day one. PE might ship without `questions` initially. The kernel checks
  this before routing a request, and the portal uses it to grey out buttons.

## The interface

```python
# ncos/kernel/interface.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class Indicator:
    code: str          # e.g. "B4.1.1.1"
    strand: str
    sub_strand: str
    content_standard: str
    text: str
    grade: str
    subject: str
    extra: dict[str, Any]  # subject-specific fields live here, not as new columns

@dataclass
class GenerationRequest:
    indicator: Indicator
    grade: str
    term: int
    week: int
    school_context: dict[str, Any]   # school name, teacher name, class size, etc.
    options: dict[str, Any]          # e.g. {"duration_minutes": 60}

class SubjectModule(ABC):
    """Everything the kernel needs from a subject, and nothing more."""

    id: str
    display_name: str
    grades: list[str]

    @abstractmethod
    def load_indicators(self, grade: str) -> list[Indicator]:
        """Parse this subject's slice of data/curriculum/ into Indicators.
        Subject-specific fields (e.g. a Math 'sub-skill', a Language
        'genre') go in Indicator.extra rather than forcing a shared schema."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Self-check: missing indicators, duplicate codes, orphaned
        sub-strands. Returns a list of problems, empty if clean. The kernel
        runs this at boot and refuses to route requests to a module that
        fails validation."""

    @abstractmethod
    def generate_lesson_plan(self, request: GenerationRequest) -> "MaterialDoc":
        """Returns a MaterialDoc — a structured, driver-agnostic document
        description (sections, content blocks) — NOT a rendered .docx.
        The docx driver renders it. This is what lets you add a PDF driver
        later without touching a single subject module."""

    @abstractmethod
    def generate_scheme_of_work(self, grade: str, term: int) -> "MaterialDoc":
        ...

    def generate_questions(self, indicator: Indicator, count: int,
                            difficulty: str) -> list["Question"]:
        """Optional — only required if 'questions' is in capabilities.
        Default raises NotImplementedError so the kernel gets a clean
        capability-mismatch error instead of a silent wrong answer."""
        raise NotImplementedError(f"{self.id} does not support question generation")
```

`MaterialDoc` is the key decision here: **modules produce structured
content, not rendered files.** A module returns something like

```python
MaterialDoc(
    title="Lesson Plan — Fractions — B4 Week 3",
    sections=[
        Section("Objectives", blocks=[...]),
        Section("Core Content", blocks=[...]),
        Section("Assessment", blocks=[...]),
    ]
)
```

and the **docx driver** (your existing `python-docx` code in `service/`)
is the only thing that knows how to turn a `MaterialDoc` into a `.docx`
file. This is the same separation as a kernel driver: the subject module
is "the app," the docx driver is "the hardware," and `MaterialDoc` is the
syscall payload between them. It's also what makes a PDF or Google Docs
driver additive later, instead of a rewrite.

The one place a subject legitimately needs to break the generic template —
Math wanting an equation box, PE wanting a safety-note callout — is handled
by a small set of typed `Block` variants (`TextBlock`, `TableBlock`,
`CalloutBlock`, `EquationBlock`) rather than letting modules embed raw
docx-rendering code. Keeps the "app" honest about not touching "hardware"
directly.

## The registry

```python
# ncos/kernel/registry.py
import importlib
import json
from pathlib import Path

class ModuleRegistry:
    SUPPORTED_INTERFACE = "1.0"

    def __init__(self, modules_dir: Path):
        self._modules: dict[str, SubjectModule] = {}
        self._load_all(modules_dir)

    def _load_all(self, modules_dir: Path):
        for manifest_path in modules_dir.glob("*/module.json"):
            manifest = json.loads(manifest_path.read_text())
            if manifest["interface_version"] != self.SUPPORTED_INTERFACE:
                raise IncompatibleModuleError(manifest["id"], manifest["interface_version"])

            mod = importlib.import_module(f"modules.{manifest['id']}.module")
            instance = mod.get_module()  # each module.py exposes this factory
            problems = instance.validate()
            if problems:
                raise ModuleValidationError(manifest["id"], problems)

            self._modules[manifest["id"]] = instance

    def get(self, subject_id: str) -> SubjectModule:
        return self._modules[subject_id]

    def capable_of(self, subject_id: str, capability: str) -> bool:
        return capability in self._modules[subject_id].manifest["capabilities"]
```

This runs once at service boot — "boot" in the literal sense from your OS
metaphor: every module is discovered, validated, and refused if broken,
*before* the service starts accepting requests. A bad Math module shouldn't
be discoverable only when a teacher hits "generate" at 11pm.

## How the kernel calls it

```python
# service/main.py (the Material Service — this barely changes)
@app.route("/api/generate/lesson-plan", methods=["POST"])
def generate_lesson_plan():
    req = parse_request(request.json)
    module = registry.get(req.subject)

    if not registry.capable_of(req.subject, "lesson_plan"):
        return error(f"{req.subject} does not support lesson plan generation")

    material_doc = module.generate_lesson_plan(req)
    docx_bytes = docx_driver.render(material_doc)   # the one "driver"
    return send_file(docx_bytes)
```

Nothing here mentions Math, Creative Arts, or French by name. That's the
test of whether the boundary is in the right place — if you ever need to
add `if subject == "x"` inside `service/main.py` again, something leaked
across the interface.

## Migration path from what you have today

You don't need to do this all at once:

1. Keep `data/curriculum/` exactly as-is for now.
2. Write `modules/math/module.py` as a thin wrapper: `load_indicators()`
   calls your existing parsing code, `generate_lesson_plan()` calls your
   existing `tools/generate_schemes.py` logic but returns a `MaterialDoc`
   instead of writing a file directly.
3. Point one route in the Material Service through the registry instead of
   calling the script directly.
4. Once that round-trips correctly, migrate the other 12 subjects — they're
   now a template to copy, not a design problem to solve again.
5. Only then tackle the subject that doesn't fit the mold (Creative Arts,
   PE) — by that point you'll know exactly which part of the interface
   needs a new `Block` type rather than a new special case.

## Open questions worth deciding before you build this

- **Does `Indicator.extra` need a schema per subject**, or is free-form
  `dict` good enough? A `schema.json` per module (referenced above) gives
  you validation without forcing a shared shape across subjects.
- **Where does cross-subject logic live** — e.g. a "generate all subjects
  for B4 Term 1" bulk job. That's a kernel-level orchestration concern, not
  a module concern; it just calls the registry in a loop.
- **Curriculum versioning vs. module versioning** — a module version bump
  (interface changes) is different from a curriculum content update (NaCCA
  revises Math 2024). Worth keeping `module_version` and
  `curriculum_source` as separate fields in the manifest, as drafted above,
  so you can update one without touching the other.
