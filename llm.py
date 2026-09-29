"""调用 DeepSeek。密钥由调用方传入，不从环境变量读取。"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

# deepseek-flash 即 DeepSeek-V4.1-Flash。
DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com"


class LLMError(Exception):
    pass


def complete(
    api_key: str,
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = 60,
) -> str:
    if not api_key or not api_key.strip():
        raise LLMError("调用模型需要 API 密钥。")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    url = base_url.rstrip("/") + "/chat/completions"
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
        raise LLMError(f"模型请求失败：HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"模型请求失败：{exc.reason}") from exc
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("模型返回里没有文本内容。") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMError("模型返回里没有文本内容。")
    _print_response(body, content)
    return content


def _print_request(url: str, payload: dict) -> None:
    lines = [
        "--- 模型请求 ---",
        f"POST {url}",
        f"model: {payload['model']}",
        f"temperature: {payload['temperature']}",
        f"response_format: {payload['response_format']['type']}",
    ]
    for message in payload["messages"]:
        lines.append(f"[{message['role']}]")
        lines.append(message["content"])
    print("\n".join(lines), file=sys.stderr)


def _print_response(body: dict, content: str) -> None:
    choice = body.get("choices", [{}])[0] if isinstance(body.get("choices"), list) else {}
    if not isinstance(choice, dict):
        choice = {}
    usage = body.get("usage")
    lines = [
        "--- 模型响应 ---",
        f"id: {body.get('id', '')}",
        f"model: {body.get('model', '')}",
        f"finish_reason: {choice.get('finish_reason', '')}",
        f"usage: {json.dumps(usage, ensure_ascii=False) if usage else ''}",
        content,
    ]
    print("\n".join(lines), file=sys.stderr)
