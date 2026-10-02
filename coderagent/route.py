"""用 Jev 把一句话分成选型、书籍或闲聊。密钥由调用方传入。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from coderagent.llm import LLMError

JEV_MODEL = "jev-latest"
JEV_BASE_URL = "https://api.typesafe.ai"
BOOK_REPLY = "书籍频道暂未开放"

_LABELS = {"selection": "选型", "book": "书籍", "chat": "闲聊"}


def classify(
    text: str,
    api_key: str,
    *,
    model: str = JEV_MODEL,
    base_url: str = JEV_BASE_URL,
    timeout: float = 30,
) -> str:
    if not text or not text.strip():
        raise LLMError("请先写一句话。")
    if not api_key or not api_key.strip():
        raise LLMError("分类需要 Jev 密钥，请在命令里传入 --jev-key。")
    payload = {
        "state": text.strip(),
        "model": model,
        "questions": {
            "route": {
                "type": "choice",
                "instructions": "这句话主要想做什么？拿不准时不要选闲聊。",
                "criteria": {
                    "selection": "在比较技术、做法或学习路径，或是技术问答但没说全背景。",
                    "book": "在问该看哪本书、求书单或书评。",
                    "chat": "问候、闲谈，以及和选型、书籍都无关的话。",
                },
            }
        },
    }
    url = base_url.rstrip("/") + "/v1/systemone"
    _print_request(url, payload)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        raise LLMError(f"Jev 请求失败：HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"Jev 请求失败：{exc.reason}") from exc
    answer = _answer(body)
    choice = str(answer.get("choice", "")).strip()
    confidence = _number(answer.get("confidence"))
    probabilities = answer.get("probabilities") if isinstance(answer.get("probabilities"), dict) else {}
    route = choice if choice in _LABELS else "selection"
    _print_response(body, choice, confidence, probabilities, route)
    return route


def _answer(body: dict) -> dict:
    try:
        answer = body["answers"]["route"]
    except (KeyError, TypeError) as exc:
        raise LLMError("Jev 返回里没有分类结果。") from exc
    if not isinstance(answer, dict):
        raise LLMError("Jev 返回里没有分类结果。")
    return answer


def _number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value)


def _print_request(url: str, payload: dict) -> None:
    print(
        "\n".join(
            [
                "--- 分类请求 ---",
                f"POST {url}",
                f"model: {payload['model']}",
                payload["state"],
            ]
        ),
        file=sys.stderr,
    )


def _print_response(body: dict, choice: str, confidence: float, probabilities: dict, route: str) -> None:
    probs = "、".join(f"{key} {value}" for key, value in probabilities.items())
    print(
        "\n".join(
            [
                "--- 分类结果 ---",
                f"model: {body.get('model', '')}",
                f"选择：{choice or '无'}",
                f"置信度：{confidence:.2f}",
                f"概率：{probs}",
                f"走向：{_LABELS[route]}",
            ]
        ),
        file=sys.stderr,
    )
