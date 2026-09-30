"""读取结构化问题和本地语料。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from coderagent.models import GOALS, Profile, Request, Source

FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
EVIDENCE_BLOCK = re.compile(r"```evidence\r?\n(.*?)\r?\n```", re.S)


class InputError(ValueError):
    pass


def load_request(path: Path) -> Request:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InputError(f"问题文件不是合法 JSON：{path}") from exc
    if not isinstance(data, dict):
        raise InputError("问题文件的顶层必须是对象")
    return request_from_data(data)


def request_from_data(data: dict) -> Request:
    question = data.get("question")
    options = data.get("options")
    profile = data.get("profile")
    if not isinstance(question, str) or not question.strip():
        raise InputError("question 必须是非空字符串")
    if not isinstance(options, list) or not 2 <= len(options) <= 3:
        raise InputError("options 必须是 2 到 3 个选项")
    if len(set(options)) != len(options) or not all(isinstance(item, str) and item for item in options):
        raise InputError("options 里的选项必须是不重复的非空字符串")
    if not isinstance(profile, dict):
        raise InputError("profile 必须是对象")

    background = profile.get("background")
    goal = profile.get("goal")
    hours = profile.get("hours_per_week")
    prior = profile.get("prior_ai_project")
    if not isinstance(background, list) or not background or not all(isinstance(item, str) and item for item in background):
        raise InputError("profile.background 必须是非空字符串列表")
    if not isinstance(prior, bool):
        raise InputError("profile.prior_ai_project 必须是布尔值")
    if goal not in GOALS:
        raise InputError("profile.goal 只能是 demo 或 production")
    if not isinstance(hours, int) or isinstance(hours, bool) or hours <= 0:
        raise InputError("profile.hours_per_week 必须是正整数")

    return Request(
        question=question.strip(),
        options=tuple(options),
        profile=Profile(
            background=tuple(item.strip() for item in background),
            prior_ai_project=prior,
            goal=goal,
            hours_per_week=hours,
        ),
    )


def load_corpus(directory: Path) -> tuple[Source, ...]:
    directory = directory.resolve()
    sources = []
    for path in sorted(directory.glob("*.md")):
        relative = path.relative_to(directory.parent).as_posix()
        sources.append(parse_source_text(path.read_text(encoding="utf-8"), relative))
    return tuple(sources)


def parse_source_text(text: str, path: str) -> Source:
    match = FRONT_MATTER.match(text)
    if not match:
        raise InputError(f"{path}: 缺少开头的资料头")
    front = _parse_kv(match.group(1))
    for key in ("id", "title", "tags"):
        if not front.get(key):
            raise InputError(f"{path}: 资料头缺少 {key}")
    body = EVIDENCE_BLOCK.sub("", text[match.end() :]).strip()
    return Source(
        id=front["id"],
        title=front["title"],
        tags=_parse_tags(front["tags"]),
        body=body,
        raw=text,
        path=path,
    )


def _parse_kv(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            raise InputError(f"资料头无法解析：{line}")
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def _parse_tags(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())
