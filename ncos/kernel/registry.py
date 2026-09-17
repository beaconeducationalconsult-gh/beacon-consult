"""The boot sequence.

At startup, the kernel walks modules/*/module.json, imports each module,
runs its self-check, and only then makes it callable. A subject that fails
validation is left out — loudly, in the boot report — rather than silently
serving broken material at 11pm on a Tuesday.
"""

from __future__ import annotations

import importlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from ncos.kernel.interface import SubjectModule

SUPPORTED_INTERFACE = "1.0"


class IncompatibleModuleError(Exception):
    pass


@dataclass
class BootEntry:
    module_id: str
    ok: bool
    detail: str


@dataclass
class BootReport:
    started_at: float
    entries: list[BootEntry] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def loaded(self) -> list[str]:
        return [e.module_id for e in self.entries if e.ok]

    @property
    def failed(self) -> list[BootEntry]:
        return [e for e in self.entries if not e.ok]

    def as_dict(self) -> dict:
        return {
            "duration_ms": round(self.duration_ms, 1),
            "loaded": self.loaded,
            "failed": [{"module": e.module_id, "detail": e.detail} for e in self.failed],
        }


class ModuleRegistry:
    def __init__(self, modules_dir: Path):
        self.modules_dir = modules_dir
        self._modules: dict[str, SubjectModule] = {}
        self._manifests: dict[str, dict] = {}
        self.boot_report = self._boot()

    def _boot(self) -> BootReport:
        t0 = time.time()
        report = BootReport(started_at=t0)

        for manifest_path in sorted(self.modules_dir.glob("*/module.json")):
            module_id = manifest_path.parent.name
            if module_id.startswith("_"):
                continue  # _template/ and any other underscore-prefixed dir is skipped
            try:
                manifest = json.loads(manifest_path.read_text())

                if manifest.get("interface_version") != SUPPORTED_INTERFACE:
                    raise IncompatibleModuleError(
                        f"expects interface {manifest.get('interface_version')}, "
                        f"kernel supports {SUPPORTED_INTERFACE}"
                    )

                mod = importlib.import_module(f"ncos.modules.{module_id}.module")
                instance: SubjectModule = mod.get_module()

                problems = instance.validate()
                if problems:
                    raise ValueError("; ".join(problems))

                self._modules[module_id] = instance
                self._manifests[module_id] = manifest
                report.entries.append(BootEntry(module_id, True, "ok"))

            except Exception as exc:  # noqa: BLE001 — boot must never crash the process
                report.entries.append(BootEntry(module_id, False, str(exc)))

        report.duration_ms = (time.time() - t0) * 1000
        return report

    def get(self, subject_id: str) -> SubjectModule:
        if subject_id not in self._modules:
            raise KeyError(f"'{subject_id}' is not a loaded module — check the boot report")
        return self._modules[subject_id]

    def capable_of(self, subject_id: str, capability: str) -> bool:
        return capability in self._manifests[subject_id].get("capabilities", [])

    def list_loaded(self) -> list[str]:
        return list(self._modules.keys())
