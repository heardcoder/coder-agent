from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coderagent.intake import describe_request, parse_user_text
from coderagent.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LLMError, complete
from coderagent.load import InputError, load_corpus, load_request
from coderagent.models import Advice, Request
from coderagent.pipeline import run
from coderagent.render import render
from coderagent.server import serve

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "用一段话描述你的问题、在比较的选项，以及背景、目标和每周时间："


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行技术研究流程，并由 DeepSeek 写建议")
    parser.add_argument("text", nargs="?", help="用一段话描述问题、选项和背景")
    parser.add_argument("--request", type=Path, help="已经拆好的问题 JSON")
    parser.add_argument("--api-key", help="DeepSeek API 密钥")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名，默认 deepseek-flash（DeepSeek-V4.1-Flash）")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="接口地址")
    parser.add_argument("--corpus", type=Path, default=ROOT / "corpus", help="语料目录")
    parser.add_argument("--web", action="store_true", help="打开本地页面，用 SSE 推送步骤")
    parser.add_argument("--port", type=int, default=8765, help="页面端口，默认 8765")
    args = parser.parse_args(argv)

    api_key = (args.api_key or "").strip()

    def caller(messages):
        return complete(api_key, messages, model=args.model, base_url=args.base_url)

    if args.web:
        if not api_key:
            print("打开页面需要 API 密钥，请在命令里传入 --api-key。", file=sys.stderr)
            return 1
        try:
            sources = load_corpus(args.corpus)
        except InputError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        serve(args.port, sources, caller, args.model)
        return 0

    try:
        request = _load_input(args, caller if api_key else None)
        sources = load_corpus(args.corpus)
    except InputError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = run(request, sources, complete=caller if api_key else None, model=args.model)
    except LLMError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.write(render(request, result))
    return 0 if isinstance(result.outcome, Advice) else 2


def _load_input(args, caller) -> Request:
    if args.text and args.request:
        raise InputError("一段话和 --request 只能使用其中一个。")
    if args.request:
        return load_request(args.request)
    text = args.text if args.text is not None else _read_text()
    if caller is None:
        raise InputError("拆解用户输入需要 API 密钥，请在命令里传入 --api-key。")
    request = parse_user_text(text, caller)
    print(describe_request(request), file=sys.stderr)
    return request


def _read_text() -> str:
    if sys.stdin.isatty():
        print(PROMPT, file=sys.stderr)
        return input().strip()
    return sys.stdin.read().strip()


if __name__ == "__main__":
    raise SystemExit(main())
