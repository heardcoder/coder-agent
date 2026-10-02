"""把用户的一段话拆成问题、选项和背景。没说清的字段不会编造。"""

from __future__ import annotations

import json
import re

from coderagent.advise import Complete
from coderagent.load import InputError, request_from_data
from coderagent.models import GOALS, Request


class NeedInput(InputError):
    """选型还缺条件。调用方把这一问退回用户，不继续研究。"""

    def __init__(self, text: str, step: str, carry: str = ""):
        super().__init__(text)
        self.step = step
        self.carry = carry


_FIELDS = ("question", "options", "background", "prior_ai_project", "goal", "hours_per_week")
HOURS_QUESTION = "每周可投入多少小时？"
DIRECTION_QUESTION = "想在什么方向上做选择？说两到三个方向就行。"
DEFAULT_HOURS = 8


def parse_user_text(text: str, complete: Complete, *, asked: str = "", answer: str = "") -> Request:
    if not text or not text.strip():
        raise InputError("请用一段话描述问题、在比较的选项，以及你的背景。")
    carry = ""
    if asked == "hours":
        hours = _read_hours(answer)
        if hours is None:
            hours = DEFAULT_HOURS
        carry = f"每周投入 {hours} 小时"
        text = text.rstrip() + "\n" + carry
    elif asked == "direction" and answer.strip():
        text = text.rstrip() + "\n" + answer.strip()
    raw = complete(build_messages(text.strip()))
    data = _load_json(raw)
    if data is None:
        raise InputError("没能从这段话里拆出结构化输入。")
    _apply_known_hours(data, text)
    if asked == "direction" and answer.strip() and "options" in _missing_fields(data):
        parsed = _options_from_direction(answer)
        if parsed:
            data["options"] = parsed
    missing = _missing_fields(data)
    if "hours_per_week" in missing:
        raise NeedInput(HOURS_QUESTION, "hours")
    if "options" in missing or "question" in missing:
        raise NeedInput(DIRECTION_QUESTION, "direction", carry)
    _fill_unasked(data, text)
    data["question"] = _compose_question(data)
    return request_from_data(data)


def _compose_question(data: dict) -> str:
    """检索用的问题带上问卷里补上的选项、时间和背景。"""
    profile = data["profile"]
    original = str(data.get("question") or "").strip()
    lines = [original] if original else []
    background = [item.strip() for item in profile["background"] if isinstance(item, str) and item.strip() and item.strip() != "未说明"]
    if background:
        lines.append("技术背景：" + "、".join(background))
    lines.append(f"每周投入 {profile['hours_per_week']} 小时")
    lines.append("做过 AI 项目" if profile["prior_ai_project"] else "还没做过 AI 项目")
    lines.append("想先做个能演示的" if profile["goal"] == "demo" else "想接到业务上")
    lines.append("在 " + "、".join(data["options"]) + " 之间选")
    return "\n".join(lines)


def describe_request(request: Request) -> str:
    profile = request.profile
    prior = "是" if profile.prior_ai_project else "否"
    return "\n".join(
        [
            "--- 拆解结果 ---",
            f"问题：{request.question}",
            f"选项：{'、'.join(request.options)}",
            f"技术背景：{'、'.join(profile.background)}",
            f"做过 AI 项目：{prior}",
            f"目标：{profile.goal}",
            f"每周投入：{profile.hours_per_week} 小时",
        ]
    )


def build_messages(text: str) -> list[dict[str, str]]:
    system = (
        "从用户的一段话里拆出 question、options 和 profile。"
        "不要编造用户没说过的背景、时间、目标，也不要猜测是否做过项目。"
        "没说清楚的字段填 null，并写入 missing。"
        "options 放用户列出的 2 到 3 个方向，按用户的写法原样保留。"
        "简称、英文片段也算，例如 SFT、loop、context，不要因为名称短就留空。"
        "不要把简称扩成用户没写过的全称。"
        "用户说的是某项技术时，只留名称，例如「RRF 融合」写成 RRF，「BGE-M3 向量」写成 BGE-M3。"
        "用户没有给出名称、只描述做法时，留做法里的关键词，不要整句，例如「自己把分数加权加起来」写成「加权求和」。"
        "goal 只能是 demo 或 production：想先做出可演示的东西是 demo，想接到真实业务是 production。"
        "prior_ai_project 只能是 true 或 false。"
        "hours_per_week 是正整数。"
        "只输出一个 JSON 对象，格式："
        '{"question":"","options":[],"profile":{"background":[],"prior_ai_project":null,'
        '"goal":null,"hours_per_week":null},"missing":[]}'
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]


_QUOTES = "\u201c\u201d\"\u300c\u300d\u300e\u300f"


def _options_from_direction(answer: str) -> list[str]:
    """方向这一问的回答就是选项。模型没收下时，按用户写的名称拆。"""
    quoted = rf"[{_QUOTES}]([^{_QUOTES}]+)[{_QUOTES}]"
    text = re.sub(quoted, lambda match: match.group(1).replace(" ", "\0"), answer)
    text = re.sub(r"[,，、]|和|与|还是", " ", text)
    names = []
    for piece in text.split():
        name = piece.replace("\0", " ").strip()
        if name and name not in names:
            names.append(name)
    if 2 <= len(names) <= 3:
        return names
    return []


def _read_hours(answer: str) -> int | None:
    match = re.search(r"\d+", answer or "")
    if not match:
        return None
    hours = int(match.group())
    if hours <= 0:
        return None
    return hours


def _apply_known_hours(data: dict, text: str) -> None:
    profile = data.get("profile")
    if not isinstance(profile, dict):
        profile = {}
        data["profile"] = profile
    hours = profile.get("hours_per_week")
    if isinstance(hours, int) and not isinstance(hours, bool) and hours > 0:
        return
    found = re.search(r"每周投入\s*(\d+)\s*小时", text)
    if found:
        profile["hours_per_week"] = int(found.group(1))


def _fill_unasked(data: dict, text: str) -> None:
    """问卷只问时间和方向。其余没说的用保守默认，避免再追问。"""
    profile = data.get("profile")
    if not isinstance(profile, dict):
        profile = {}
        data["profile"] = profile
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        data["question"] = text.strip().split("\n", 1)[0][:200]
    background = profile.get("background")
    if not isinstance(background, list) or not any(isinstance(item, str) and item.strip() for item in background):
        profile["background"] = ["未说明"]
    if not isinstance(profile.get("prior_ai_project"), bool):
        profile["prior_ai_project"] = False
    if profile.get("goal") not in GOALS:
        profile["goal"] = "demo"


def _missing_fields(data: dict) -> list[str]:
    if not isinstance(data, dict):
        return list(_FIELDS)
    profile = data.get("profile") if isinstance(data.get("profile"), dict) else {}
    missing: list[str] = []
    question = data.get("question")
    if not isinstance(question, str) or not question.strip():
        missing.append("question")
    options = data.get("options")
    if (
        not isinstance(options, list)
        or not 2 <= len(options) <= 3
        or len(set(options)) != len(options)
        or not all(isinstance(item, str) and item.strip() for item in options)
    ):
        missing.append("options")
    background = profile.get("background")
    if not isinstance(background, list) or not background or not all(isinstance(item, str) and item.strip() for item in background):
        missing.append("background")
    if not isinstance(profile.get("prior_ai_project"), bool):
        missing.append("prior_ai_project")
    if profile.get("goal") not in GOALS:
        missing.append("goal")
    hours = profile.get("hours_per_week")
    if not isinstance(hours, int) or isinstance(hours, bool) or hours <= 0:
        missing.append("hours_per_week")
    return missing


def _load_json(raw: str) -> dict | None:
    text = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data
