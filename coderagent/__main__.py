from __future__ import annotations

import argparse
import sys
from pathlib import Path

from coderagent.chat import chat_reply
from coderagent.intake import NeedInput, describe_request, parse_user_text
from coderagent.judge import answers_question
from coderagent.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, LLMError, complete, complete_message
from coderagent.load import InputError, load_corpus, load_request
from coderagent.lookup import search_web
from coderagent.models import Advice, Request
from coderagent.pipeline import run
from coderagent.render import render
from coderagent.route import BOOK_REPLY, JEV_BASE_URL, JEV_MODEL, classify
from coderagent.server import serve

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "logs" / "latest.txt"
PROMPT = "用一段话描述你的问题、在比较的选项，以及背景、目标和每周时间："


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行技术研究流程，并由 DeepSeek 写建议")
    parser.add_argument("text", nargs="?", help="用一段话描述问题、选项和背景")
    parser.add_argument("--request", type=Path, help="已经拆好的问题 JSON")
    parser.add_argument("--api-key", help="DeepSeek API 密钥")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名，默认 deepseek-flash（DeepSeek-V4.1-Flash）")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="接口地址")
    parser.add_argument("--jev-key", help="Jev API 密钥，用来把一句话分成选型、书籍或闲聊")
    parser.add_argument("--jev-model", default=JEV_MODEL, help="Jev 模型名，默认 jev-latest")
    parser.add_argument("--jev-base-url", default=JEV_BASE_URL, help="Jev 接口地址")
    parser.add_argument("--corpus", type=Path, default=ROOT / "corpus", help="语料目录")
    parser.add_argument("--web", action="store_true", help="打开本地页面，用 SSE 推送步骤")
    parser.add_argument("--port", type=int, default=8765, help="页面端口，默认 8765")
    args = parser.parse_args(argv)
    _open_log()

    api_key = (args.api_key or "").strip()
    jev_key = (args.jev_key or "").strip()

    def intake_complete(messages):
        return complete(api_key, messages, model=args.model, base_url=args.base_url)

    def plain_complete(messages):
        return complete(api_key, messages, model=args.model, base_url=args.base_url, json_mode=False)

    def turn(messages, tools=None):
        return complete_message(api_key, messages, tools=tools, model=args.model, base_url=args.base_url)

    def classify_text(text):
        return classify(text, jev_key, model=args.jev_model, base_url=args.jev_base_url)

    def judge(question, option, excerpt):
        return answers_question(question, option, excerpt, intake_complete)

    def bound_search(query, option, question=""):
        return search_web(query, option, judge=judge if api_key else None, question=question)

    if args.web:
        if not api_key:
            print("打开页面需要 API 密钥，请在命令里传入 --api-key。", file=sys.stderr)
            return 1
        if not jev_key:
            print("打开页面需要 Jev 密钥，请在命令里传入 --jev-key。", file=sys.stderr)
            return 1
        try:
            load_corpus(args.corpus)
            knowledge = _knowledge(args.corpus)
        except (InputError, ImportError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        serve(
            args.port,
            args.corpus,
            intake_complete,
            turn,
            args.model,
            knowledge,
            classify_text,
            plain_complete,
            bound_search,
        )
        return 0

    try:
        request = _load_input(args, intake_complete if api_key else None, classify_text if jev_key else None, plain_complete if api_key else None)
        if request is None:
            return 0
        load_corpus(args.corpus)
    except NeedInput as exc:
        print(str(exc))
        return 0
    except InputError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        result = run(
            request,
            args.corpus,
            turn=turn if api_key else None,
            model=args.model,
            search=bound_search,
            knowledge=_knowledge(args.corpus),
        )
    except (LLMError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.write(render(request, result))
    return 0 if isinstance(result.outcome, Advice) else 2


def _load_input(args, caller, classify_text, chat) -> Request | None:
    if args.text and args.request:
        raise InputError("一段话和 --request 只能使用其中一个。")
    if args.request:
        return load_request(args.request)
    text = args.text if args.text is not None else _read_text()
    if classify_text is None:
        raise InputError("分类需要 Jev 密钥，请在命令里传入 --jev-key。")
    route = classify_text(text)
    if route == "book":
        print(BOOK_REPLY)
        return None
    if route == "chat":
        if chat is None:
            raise InputError("闲聊需要 API 密钥，请在命令里传入 --api-key。")
        print(chat_reply(text, chat))
        return None
    if caller is None:
        raise InputError("拆解用户输入需要 API 密钥，请在命令里传入 --api-key。")
    request = _ask_until_ready(text, caller, _read_reply)
    print(describe_request(request), file=sys.stderr)
    return request


def _ask_until_ready(text: str, caller, read_reply) -> Request:
    asked = ""
    answer = ""
    while True:
        try:
            return parse_user_text(text, caller, asked=asked, answer=answer)
        except NeedInput as exc:
            reply = read_reply(str(exc))
            if reply is None:
                raise
            if exc.carry:
                text = text.rstrip() + "\n" + exc.carry
            asked = exc.step
            answer = reply


def _read_reply(question: str) -> str | None:
    if not sys.stdin.isatty():
        return None
    print(question)
    return input().strip()


class _Tee:
    def __init__(self, stream, log):
        self._stream = stream
        self._log = log

    def write(self, data):
        self._stream.write(data)
        self._log.write(data)
        self._log.flush()

    def flush(self):
        self._stream.flush()
        self._log.flush()

    def isatty(self):
        return self._stream.isatty()


def _open_log() -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    log = LOG_PATH.open("w", encoding="utf-8")
    sys.stdout = _Tee(sys.stdout, log)
    sys.stderr = _Tee(sys.stderr, log)
    print(f"日志：{LOG_PATH}", file=sys.stderr)


def _knowledge(corpus: Path):
    from coderagent.embed import BgeM3
    from coderagent.knowledge import KnowledgeBase

    return KnowledgeBase(corpus.parent / "knowledge.sqlite", BgeM3())


def _read_text() -> str:
    if sys.stdin.isatty():
        print(PROMPT, file=sys.stderr)
        return input().strip()
    return sys.stdin.read().strip()


if __name__ == "__main__":
    raise SystemExit(main())
