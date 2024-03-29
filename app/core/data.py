from __future__ import annotations

from enum import Enum
from json import load
from typing import Any, Hashable, Literal, NamedTuple, Protocol, Self

__all__ = (
    'CourseType',
    'Course',
    'HistorySection',
    'Term',
)


class Section(Hashable, Protocol):
    @classmethod
    def from_dict(cls, *args: Any, **kwargs: Any) -> Self:
        ...


class CourseType(Enum):
    history = 0


class _Course[TypeT: CourseType, SectionT: Section](NamedTuple):
    type: TypeT
    name: str
    sections: list[SectionT]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> _Course:
        ty = CourseType[data['type']]
        section_cls: type[SectionT] = None  # type: ignore
        match ty:
            case CourseType.history:
                section_cls = HistorySection  # type: ignore

        return cls(
            type=ty,
            name=data['name'],
            sections=[section_cls.from_dict(section) for section in data['sections']],
        )


type Course = _Course[Literal[CourseType.history], HistorySection]


class HistorySection(NamedTuple):
    period: int
    range: str
    terms: list[Term]
    mcqs: list[QuestionSet]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HistorySection:
        return cls(
            period=data['period'],
            range=data['range'],
            terms=[Term(**term) for term in data['terms']],
            mcqs=[QuestionSet.from_dict(mcq) for mcq in data['mcqs']],
        )

    def __hash__(self) -> int:
        return hash(self.period)


class Term(NamedTuple):
    term: str
    definition: str
    image: str | None = None


def get_term_hash[S: Section](*, course: _Course[CourseType, S], section: S, term: Term) -> int:
    return hash((course.name, section, term.term))


class QuestionSet(NamedTuple):
    stimulus: Stimulus
    questions: list[Question]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QuestionSet:
        return cls(
            stimulus=Stimulus(**data['stimulus']),
            questions=[Question(**question) for question in data['questions']],
        )


class Stimulus(NamedTuple):
    header: str
    text: str | None = None
    image: str | None = None
    footer: str | None = None


class Question(NamedTuple):
    question: str
    answer: str
    other_choices: list[str]
    explanation: str | None = None


def load_courses(*, path: str = 'assets/courses.json') -> list[Course]:
    with open(path) as fp:
        return [_Course.from_dict(course) for course in load(fp)]
