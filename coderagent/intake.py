"""把用户的一段话拆成问题、选项和背景。没说清的字段不会编造。"""

from __future__ import annotations

import json
import re

from coderagent.advise import Complete
from coderagent.load import InputError, request_from_data
from coderagent.models import GOALS, Request

FIELD_LABELS = {
    "question": "问题",
    "options": "在比较的选项",
    "background": "技术背景",
    "prior_ai_project": "是否做过 AI 项目",
    "goal": "目标（做出演示用 demo，接到业务用 production）",
    "hours_per_week": "每周投入时间",
}


def parse_user_text(text: str, complete: Complete) -> Request:
    if not text or not text.strip():
        raise InputError("请用一段话描述问题、在比较的选项，以及你的背景。")
    raw = complete(build_messages(text.strip()))
    data = _load_json(raw)
    if data is None:
        raise InputError("没能从这段话里拆出结构化输入。")
    missing = _missing_fields(data)
    if missing:
        names = "、".join(FIELD_LABELS[item] for item in missing)
        raise InputError(f"这段话里还缺：{names}。请补充后再运行。")
    return request_from_data(data)


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
        "options 只放用户明确在比较的 2 到 3 项，每项用可检索的短名称。"
        "用户说的是某项技术时，只留名称，例如「RRF 融合」写成 RRF，「BGE-M3 向量」写成 BGE-M3。"
        "用户没有给出名称、只描述做法时，留做法里的关键词，不要整句，例如「自己把分数加权加起来」写成「加权求和」。"
        "不要换成用户没说过的专有名词。"
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


def _missing_fields(data: dict) -> list[str]:
    if not isinstance(data, dict):
        return list(FIELD_LABELS)
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
