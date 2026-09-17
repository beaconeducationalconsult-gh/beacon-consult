"""Copy this directory to ncos/modules/<subject_id>/, rename the class,
fill in the TODOs, then register it by giving module.json a real id.
It will not be picked up at boot until module.json's id no longer starts
with an underscore-prefixed directory name (this _template/ is skipped
deliberately — see tools/ncosctl.py)."""

from ncos.kernel.interface import (
    GenerationRequest,
    Indicator,
    MaterialDoc,
    Section,
    SubjectModule,
    TextBlock,
)


class TemplateModule(SubjectModule):
    id = "REPLACE_ME"
    display_name = "Replace Me"
    grades = ["B1"]
    capabilities = {"lesson_plan"}

    def load_indicators(self, grade: str) -> list[Indicator]:
        # TODO: read data/curriculum/<subject>/<grade>.json and return
        # a list[Indicator]. See ncos/modules/math/module.py for a
        # working example.
        raise NotImplementedError

    def validate(self) -> list[str]:
        # TODO: sanity-check your own data. Return a list of human-readable
        # problems, or [] if clean. This runs at boot — a non-empty return
        # keeps the module out of the registry.
        return ["not yet implemented"]

    def generate_lesson_plan(self, request: GenerationRequest) -> MaterialDoc:
        # TODO: build a MaterialDoc out of Sections and Blocks. Never
        # touch python-docx here — that belongs to the driver.
        raise NotImplementedError

    def generate_scheme_of_work(self, grade: str, term: int) -> MaterialDoc:
        raise NotImplementedError


def get_module() -> SubjectModule:
    return TemplateModule()
