"""这条流程里流转的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass

DIMENSIONS = ("解决的问题", "前置基础", "主路径", "何时更合适")
STANCES = ("info", "start", "later", "next", "reason")
GOALS = ("demo", "production")

GOAL_LABEL = {
    "demo": "做出一个可以演示的 AI 应用",
    "production": "把已经做出来的 AI 应用接到真实业务里",
}


@dataclass(frozen=True)
class Profile:
    background: tuple[str, ...]
    prior_ai_project: bool
    goal: str
    hours_per_week: int


@dataclass(frozen=True)
class Request:
    question: str
    options: tuple[str, ...]
    profile: Profile


@dataclass(frozen=True)
class Source:
    id: str
    title: str
    tags: tuple[str, ...]
    body: str
    raw: str
    path: str


@dataclass(frozen=True)
class Evidence:
    id: str
    source_id: str
    option: str
    dimension: str
    stance: str
    quote: str
    when: tuple[tuple[str, object], ...] = ()

    def applies(self, profile: Profile) -> bool:
        rules = dict(self.when)
        if "prior_ai_project" in rules and rules["prior_ai_project"] != profile.prior_ai_project:
            return False
        if "goal" in rules and rules["goal"] != profile.goal:
            return False
        if "max_hours" in rules and profile.hours_per_week > rules["max_hours"]:
            return False
        if "min_hours" in rules and profile.hours_per_week < rules["min_hours"]:
            return False
        return True


@dataclass(frozen=True)
class Line:
    text: str
    ref: str


@dataclass(frozen=True)
class Advice:
    recommend: Line
    reasons: tuple[Line, ...]
    not_yet: tuple[Line, ...]
    next_step: Line

    def technical_lines(self) -> tuple[Line, ...]:
        return (self.recommend, *self.reasons, *self.not_yet, self.next_step)


@dataclass(frozen=True)
class Stop:
    reason: str


@dataclass(frozen=True)
class Row:
    dimension: str
    cells: tuple[tuple[str, tuple[Line, ...]], ...]


@dataclass(frozen=True)
class Result:
    sources: tuple[Source, ...]
    comparison: tuple[Row, ...]
    outcome: Advice | Stop
    rejected: tuple[str, ...]
    model: str = ""
