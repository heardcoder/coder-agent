"""闲聊直接交给模型，不查知识库，也不出带证据的建议。"""

from __future__ import annotations

from coderagent.advise import Complete

SYSTEM = (
    "你在闲聊。直接用中文回答用户这句话。"
    "不要调用工具，不要输出选型 JSON，不要编造 evidence_id。"
)


def chat_reply(text: str, complete: Complete) -> str:
    return complete(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": text.strip()},
        ]
    )
