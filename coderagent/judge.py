"""判断联网摘录是不是在讲这个选项。"""

from __future__ import annotations

import json
import re

from coderagent.advise import Complete


def answers_question(_question: str, option: str, excerpt: str, complete: Complete) -> bool:
    raw = complete(
        [
            {
                "role": "system",
                "content": (
                    "判断摘录是不是在讲这个选项。"
                    "讲清它是什么、怎么用或适合什么情况，算是。"
                    "导航、广告、纯数学定义，或同一个词的另一种意思，算否。"
                    "不必提到用户的背景和时间，也不必在几个选项里做选择。"
                    '只输出 JSON：{"answer": true} 或 {"answer": false}。'
                ),
            },
            {
                "role": "user",
                "content": f"选项：{option}\n摘录：{excerpt[:1200]}",
            },
        ]
    )
    data = _load(raw)
    return isinstance(data, dict) and data.get("answer") is True


def _load(raw: str) -> dict | None:
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
