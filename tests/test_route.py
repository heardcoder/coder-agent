import io
import json
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.route import classify


def _response(choice, confidence, probabilities):
    body = json.dumps(
        {
            "model": "jev-1.13.0",
            "answers": {
                "route": {
                    "type": "choice",
                    "choice": choice,
                    "probabilities": probabilities,
                    "confidence": confidence,
                }
            },
        }
    ).encode("utf-8")

    class Response:
        def read(self):
            return body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return Response()


class RouteTest(unittest.TestCase):
    def test_confident_chat_stays_chat(self):
        response = _response("chat", 0.82, {"selection": 0.1, "book": 0.08, "chat": 0.82})
        with mock.patch("coderagent.route.urllib.request.urlopen", return_value=response):
            self.assertEqual(classify("今天天气不错", "jev-key"), "chat")

    def test_low_confidence_still_follows_choice(self):
        response = _response("chat", 0.41, {"selection": 0.4, "book": 0.19, "chat": 0.41})
        logs = io.StringIO()
        with mock.patch("coderagent.route.urllib.request.urlopen", return_value=response), redirect_stderr(logs):
            route = classify("今天天气不错", "jev-key")
        self.assertEqual(route, "chat")
        self.assertIn("走向：闲聊", logs.getvalue())

    def test_book_is_its_own_route(self):
        response = _response("book", 0.9, {"selection": 0.05, "book": 0.9, "chat": 0.05})
        with mock.patch("coderagent.route.urllib.request.urlopen", return_value=response):
            self.assertEqual(classify("推荐一本 RAG 的书", "jev-key"), "book")

    def test_book_with_moderate_confidence_stays_book(self):
        response = _response("book", 0.51, {"book": 0.68, "selection": 0.32, "chat": 0.0})
        with mock.patch("coderagent.route.urllib.request.urlopen", return_value=response):
            self.assertEqual(classify("clean code还值得看吗", "jev-key"), "book")


if __name__ == "__main__":
    unittest.main()
