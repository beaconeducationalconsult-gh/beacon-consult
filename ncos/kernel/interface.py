"""The contract every subject module implements, and the document model
that flows between a module and a driver.

A subject module never produces a rendered file (.docx, .pdf). It produces
a MaterialDoc — a structured, driver-agnostic description. A driver (see
kernel/drivers/) is the only thing that knows how to turn a MaterialDoc
into bytes on disk. This is the same separation as a kernel driver: the
module is "the app," the driver is "the hardware," MaterialDoc is the
payload crossing that boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Curriculum data
# ---------------------------------------------------------------------------

@dataclass
class Indicator:
    code: str            # e.g. "B4.1.1.1"
    strand: str
    sub_strand: str
    content_standard: str
    text: str
    grade: str
    subject: str
    extra: dict[str, Any] = field(default_factory=dict)
    # Subject-specific fields (a Math "sub-skill", a Language "genre") live
    # in `extra` rather than forcing every subject into one shared schema.


@dataclass
class GenerationRequest:
    indicator: Indicator
    grade: str
    term: int
    week: int
    school_context: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Document model — what a module hands back
# ---------------------------------------------------------------------------

@dataclass
class TextBlock:
    text: str
    style: str = "body"   # "body" | "heading" | "bullet"


@dataclass
class TableBlock:
    headers: list[str]
    rows: list[list[str]]


@dataclass
class CalloutBlock:
    label: str             # e.g. "Safety note", "Core point"
    text: str


@dataclass
class EquationBlock:
    latex: str


Block = TextBlock | TableBlock | CalloutBlock | EquationBlock


@dataclass
class Section:
    title: str
    blocks: list[Block] = field(default_factory=list)


@dataclass
class MaterialDoc:
    title: str
    sections: list[Section] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Question:
    prompt: str
    options: list[str] | None = None   # None for open-ended / numeric
    answer: str = ""
    difficulty: str = "core"           # "reinforcement" | "core" | "extension"


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

class SubjectModule(ABC):
    """Everything the kernel needs from a subject, and nothing more."""

    id: str
    display_name: str
    grades: list[str]
    capabilities: set[str] = set()

    @abstractmethod
    def load_indicators(self, grade: str) -> list[Indicator]:
        """Parse this subject's slice of data/curriculum/ into Indicators."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Self-check: missing indicators, duplicate codes, orphaned
        sub-strands. Return a list of problems (empty if clean). Run once
        at boot — a module that fails validation is not registered."""

    @abstractmethod
    def generate_lesson_plan(self, request: GenerationRequest) -> MaterialDoc:
        ...

    @abstractmethod
    def generate_scheme_of_work(self, grade: str, term: int) -> MaterialDoc:
        ...

    def generate_questions(self, indicator: Indicator, count: int,
                            difficulty: str = "core") -> list[Question]:
        """Optional — only called if 'questions' is in capabilities."""
        raise NotImplementedError(f"{self.id} does not support question generation")
