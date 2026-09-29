from __future__ import annotations

import json
import sys
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.load import load_corpus
from coderagent.server import make_server

USER_TEXT = "我有 Python 和后端经验，每周 8 小时，还没做过 AI 项目，想先做个能演示的应用。应该先学 RAG 还是 Agent？"

INTAKE = {
    "question": "应该先学 RAG 还是 Agent？",
    "options": ["RAG", "Agent"],
    "profile": {
        "background": ["Python", "后端经验"],
        "prior_ai_project": False,
        "goal": "demo",
        "hours_per_week": 8,
    },
}

ADVICE = {
    "recommend": "RAG",
    "recommend_evidence_id": "rag-start",
    "reasons": [{"text": "先做输入输出固定的链路。", "evidence_id": "rag-start"}],
    "not_yet": [{"text": "多 Agent 先不做。", "evidence_id": "agent-later-multi"}],
    "next_step": {"text": "用笔记做一个带引用的问答。", "evidence_id": "rag-next"},
}


class ServerTest(unittest.TestCase):
    def test_page_streams_steps_over_sse(self):
        def complete(messages):
            content = messages[-1]["content"]
            payload = ADVICE if "evidence" in content else INTAKE
            return json.dumps(payload, ensure_ascii=False)

        server = make_server("127.0.0.1", 0, load_corpus(ROOT / "corpus"), complete, "deepseek-flash")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            page = _request(port, "GET", "/")
            self.assertEqual(page.status, 200)
            self.assertIn("拆解输入", page.read().decode("utf-8"))

            response = _request(
                port,
                "POST",
                "/api/run",
                json.dumps({"text": USER_TEXT}).encode("utf-8"),
                {"Content-Type": "application/json"},
            )
            self.assertEqual(response.status, 200)
            events = _events(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()

        ids = [(event.get("id"), event.get("state")) for event in events if event["type"] == "step"]
        self.assertIn(("intake", "done"), ids)
        self.assertIn(("advise", "done"), ids)
        result = next(event for event in events if event["type"] == "result")
        self.assertTrue(result["ok"])
        self.assertIn("建议先做：RAG", result["text"])

    def test_incomplete_text_stops_on_the_page(self):
        def complete(messages):
            return json.dumps(
                {
                    "question": "应该先学 RAG 还是 Agent？",
                    "options": ["RAG", "Agent"],
                    "profile": {
                        "background": ["Python"],
                        "prior_ai_project": False,
                        "goal": "demo",
                        "hours_per_week": None,
                    },
                },
                ensure_ascii=False,
            )

        server = make_server("127.0.0.1", 0, load_corpus(ROOT / "corpus"), complete, "deepseek-flash")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            response = _request(
                port,
                "POST",
                "/api/run",
                json.dumps({"text": "还没说每周时间"}).encode("utf-8"),
                {"Content-Type": "application/json"},
            )
            events = _events(response.read().decode("utf-8"))
        finally:
            server.shutdown()
            server.server_close()

        self.assertTrue(any(event["type"] == "error" and "每周投入时间" in event["text"] for event in events))
        self.assertFalse(any(event["type"] == "result" for event in events))


def _request(port: int, method: str, path: str, body: bytes | None = None, headers: dict | None = None):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path, body=body, headers=headers or {})
    return connection.getresponse()


def _events(body: str) -> list[dict]:
    events = []
    for block in body.split("\n\n"):
        line = next((item for item in block.split("\n") if item.startswith("data: ")), "")
        if line:
            events.append(json.loads(line[6:]))
    return events


if __name__ == "__main__":
    unittest.main()
