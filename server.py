"""本地页面。步骤通过 SSE 推给浏览器。"""

from __future__ import annotations

import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from coderagent.advise import Complete
from coderagent.intake import describe_request, parse_user_text
from coderagent.llm import LLMError
from coderagent.load import InputError
from coderagent.models import Advice, Source
from coderagent.pipeline import run
from coderagent.render import render

PAGE = Path(__file__).with_name("page.html").read_text(encoding="utf-8")
HOST = "127.0.0.1"


def serve(port: int, sources: tuple[Source, ...], complete: Complete, model: str) -> None:
    server = make_server(HOST, port, sources, complete, model)
    print(f"页面：http://{HOST}:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


def make_server(
    host: str,
    port: int,
    sources: tuple[Source, ...],
    complete: Complete,
    model: str,
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
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                self.send_error(400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            try:
                self._run(text)
            except BrokenPipeError:
                return
            except (InputError, LLMError) as exc:
                self._send({"type": "error", "text": str(exc)})
            except Exception:
                traceback.print_exc()
                self._send({"type": "error", "text": "流程中断。"})
            self._end_chunk()

        def _run(self, text: str) -> None:
            self._send({"type": "step", "id": "intake", "state": "running", "text": "正在拆成问题、选项和背景"})
            request = parse_user_text(text, complete)
            self._send({"type": "step", "id": "intake", "state": "done", "text": describe_request(request)})

            def on_step(step: str, state: str, detail: str) -> None:
                self._send({"type": "step", "id": step, "state": state, "text": detail})

            result = run(request, sources, complete=complete, model=model, on_step=on_step)
            self._send(
                {
                    "type": "result",
                    "ok": isinstance(result.outcome, Advice),
                    "text": render(request, result),
                }
            )

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
