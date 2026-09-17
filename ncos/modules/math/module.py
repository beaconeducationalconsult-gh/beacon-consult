import json
from pathlib import Path

from ncos.kernel.interface import (
    CalloutBlock,
    GenerationRequest,
    Indicator,
    MaterialDoc,
    Section,
    SubjectModule,
    TableBlock,
    TextBlock,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "curriculum" / "math"


class MathModule(SubjectModule):
    id = "math"
    display_name = "Mathematics"
    grades = ["B4"]
    capabilities = {"lesson_plan", "scheme_of_work"}

    def load_indicators(self, grade: str) -> list[Indicator]:
        path = DATA_DIR / f"{grade}.json"
        if not path.exists():
            return []
        raw = json.loads(path.read_text())
        return [
            Indicator(
                code=i["code"],
                strand=i["strand"],
                sub_strand=i["sub_strand"],
                content_standard=i["content_standard"],
                text=i["text"],
                grade=raw["grade"],
                subject=raw["subject"],
                extra=i.get("extra", {}),
            )
            for i in raw["indicators"]
        ]

    def validate(self) -> list[str]:
        problems = []
        for grade in self.grades:
            indicators = self.load_indicators(grade)
            if not indicators:
                problems.append(f"no indicators found for grade {grade}")
            codes = [i.code for i in indicators]
            if len(codes) != len(set(codes)):
                problems.append(f"duplicate indicator codes in grade {grade}")
        return problems

    def generate_lesson_plan(self, request: GenerationRequest) -> MaterialDoc:
        ind = request.indicator
        duration = request.options.get("duration_minutes", 60)
        return MaterialDoc(
            title=f"Lesson Plan — {ind.strand} — {ind.grade} Wk {request.week}",
            sections=[
                Section("Indicator", [
                    TextBlock(f"{ind.code}: {ind.text}"),
                ]),
                Section("Objectives", [
                    TextBlock(f"By the end of the lesson, learners will be able to {ind.text.lower()}.", "bullet"),
                ]),
                Section("Core Content", [
                    TextBlock(ind.content_standard),
                    CalloutBlock("Sub-skill", ind.extra.get("sub_skill", "n/a")),
                ]),
                Section("Duration", [
                    TextBlock(f"{duration} minutes"),
                ]),
            ],
            meta={"subject": ind.subject, "grade": ind.grade, "indicator_code": ind.code},
        )

    def generate_scheme_of_work(self, grade: str, term: int) -> MaterialDoc:
        indicators = self.load_indicators(grade)
        rows = [[i.code, i.strand, i.text] for i in indicators]
        return MaterialDoc(
            title=f"Scheme of Work — Mathematics {grade} Term {term}",
            sections=[
                Section("Indicators covered", [
                    TableBlock(headers=["Code", "Strand", "Indicator"], rows=rows),
                ]),
            ],
            meta={"subject": "math", "grade": grade, "term": term},
        )


def get_module() -> SubjectModule:
    """The factory the registry calls — see kernel/registry.py."""
    return MathModule()
