#!/usr/bin/env python3
"""ncosctl — inspect and exercise the kernel without starting the service.

    python tools/ncosctl.py boot-check
    python tools/ncosctl.py list-modules
    python tools/ncosctl.py generate-sample math B4 B4.1.1.1
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ncos.kernel.drivers.docx_driver import DocxDriver
from ncos.kernel.interface import GenerationRequest
from ncos.kernel.registry import ModuleRegistry

BASE_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = BASE_DIR / "ncos" / "modules"
OUT_DIR = BASE_DIR / "dist"


def boot_check():
    registry = ModuleRegistry(MODULES_DIR)
    report = registry.boot_report
    print(f"Boot completed in {report.duration_ms:.1f}ms")
    print(f"Loaded  : {', '.join(report.loaded) or '(none)'}")
    if report.failed:
        print("Failed  :")
        for entry in report.failed:
            print(f"  - {entry.module_id}: {entry.detail}")
        sys.exit(1)
    else:
        print("All modules healthy.")


def list_modules():
    registry = ModuleRegistry(MODULES_DIR)
    for module_id in registry.list_loaded():
        module = registry.get(module_id)
        print(f"{module_id:12} grades={module.grades} capabilities={sorted(module.capabilities)}")


def generate_sample(subject: str, grade: str, indicator_code: str):
    registry = ModuleRegistry(MODULES_DIR)
    if registry.boot_report.failed:
        print("Refusing to generate — boot had failures. Run `boot-check` first.")
        sys.exit(1)

    module = registry.get(subject)
    indicators = module.load_indicators(grade)
    indicator = next((i for i in indicators if i.code == indicator_code), None)
    if indicator is None:
        print(f"No indicator {indicator_code} in {subject}/{grade}")
        sys.exit(1)

    req = GenerationRequest(indicator=indicator, grade=grade, term=1, week=1)
    doc = module.generate_lesson_plan(req)

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / f"{subject}_{grade}_{indicator_code}.docx"
    out_path.write_bytes(DocxDriver().render(doc))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "boot-check":
        boot_check()
    elif cmd == "list-modules":
        list_modules()
    elif cmd == "generate-sample":
        generate_sample(*sys.argv[2:5])
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
