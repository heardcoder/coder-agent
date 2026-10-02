"""本地页面。步骤通过 SSE 推给浏览器。"""

from __future__ import annotations

import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from coderagent.advise import Complete
from coderagent.chat import chat_reply
from coderagent.intake import NeedInput, describe_request, parse_user_text
from coderagent.llm import LLMError
from coderagent.load import InputError
from coderagent.lookup import Search, search_web
from coderagent.models import Advice
from coderagent.pipeline import run
from coderagent.react import Turn
from coderagent.render import render
from coderagent.route import BOOK_REPLY

PAGE = Path(__file__).with_name("page.html").read_text(encoding="utf-8")
HOST = "127.0.0.1"


def serve(
    port: int,
    corpus_dir: Path,
    complete: Complete,
    turn: Turn,
    model: str,
    knowledge=None,
    classify=None,
    chat: Complete | None = None,
    search: Search = search_web,
) -> None:
    server = make_server(
        HOST, port, corpus_dir, complete, turn, model, knowledge, classify, chat, search
    )
    print(f"页面：http://{HOST}:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


def make_server(
    host: str,
    port: int,
    corpus_dir: Path,
    complete: Complete,
    turn: Turn,
    model: str,
    knowledge=None,
    classify=None,
    chat: Complete | None = None,
    search: Search = search_web,
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            if self.path.split("?", 1)[0] != "/":
                self.send_error(404)
                return
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            if self.path.split("?", 1)[0] != "/api/run":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                text = payload["text"]
                asked = payload.get("asked") if isinstance(payload.get("asked"), str) else ""
                answer = payload.get("answer") if isinstance(payload.get("answer"), str) else ""
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                self.send_error(400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                self._run(text, asked, answer)
            except BrokenPipeError:
                return
            except (InputError, LLMError) as exc:
                self._send({"type": "error", "text": str(exc)})
            except Exception:
                traceback.print_exc()
                self._send({"type": "error", "text": "流程中断。"})
            self._end_chunk()

        def _run(self, text: str, asked: str = "", answer: str = "") -> None:
            self._send({"type": "step", "id": "route", "state": "running", "text": "正在分类"})
            route = classify(text) if classify is not None else "selection"
            if route == "book":
                self._send({"type": "step", "id": "route", "state": "done", "text": "书籍"})
                self._skip("intake", "research")
                self._send({"type": "result", "ok": True, "text": BOOK_REPLY})
                return
            if route == "chat":
                self._send({"type": "step", "id": "route", "state": "done", "text": "闲聊"})
                self._skip("intake", "research")
                if chat is None:
                    raise LLMError("闲聊需要模型。")
                self._send({"type": "result", "ok": True, "text": chat_reply(text, chat)})
                return
            self._send({"type": "step", "id": "route", "state": "done", "text": "选型"})
            self._send({"type": "step", "id": "intake", "state": "running", "text": "正在拆成问题、选项和背景"})
            try:
                request = parse_user_text(text, complete, asked=asked, answer=answer)
            except NeedInput as exc:
                self._send({"type": "step", "id": "intake", "state": "done", "text": str(exc)})
                self._skip("research")
                self._send(
                    {
                        "type": "result",
                        "ok": False,
                        "ask": True,
                        "step": exc.step,
                        "carry": exc.carry,
                        "text": str(exc),
                    }
                )
                return
            self._send({"type": "step", "id": "intake", "state": "done", "text": describe_request(request)})

            def on_step(step: str, state: str, detail: str) -> None:
                self._send({"type": "step", "id": step, "state": state, "text": detail})

            result = run(
                request,
                corpus_dir,
                turn=turn,
                model=model,
                on_step=on_step,
                search=search,
                knowledge=knowledge,
            )
            self._send(
                {
                    "type": "result",
                    "ok": isinstance(result.outcome, Advice),
                    "text": render(request, result),
                }
            )

        def _skip(self, *steps: str) -> None:
            for step in steps:
                self._send({"type": "step", "id": step, "state": "skipped", "text": ""})

        def _send(self, payload: dict) -> None:
            raw = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
            self.wfile.write(f"{len(raw):x}\r\n".encode("ascii") + raw + b"\r\n")
            self.wfile.flush()

        def _end_chunk(self) -> None:
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()

        def log_message(self, fmt: str, *args) -> None:
            sys.stderr.write("页面 %s\n" % (fmt % args))

    return ThreadingHTTPServer((host, port), Handler)
