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

from coderagent.llm import DEFAULT_MODEL, complete


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class LLMClientTest(unittest.TestCase):
    def test_complete_posts_deepseek_flash_and_prints_exchange(self):
        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["url"] = request.full_url
            captured["auth"] = request.get_header("Authorization")
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return FakeResponse(
                {
                    "id": "chatcmpl-1",
                    "model": "deepseek-flash",
                    "choices": [{"finish_reason": "stop", "message": {"content": "{\"ok\": true}"}}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                }
            )

        logs = io.StringIO()
        with mock.patch("urllib.request.urlopen", fake_urlopen), redirect_stderr(logs):
            text = complete("sk-test", [{"role": "user", "content": "hi"}])

        printed = logs.getvalue()
        self.assertEqual(text, "{\"ok\": true}")
        self.assertEqual(captured["url"], "https://api.deepseek.com/chat/completions")
        self.assertEqual(captured["auth"], "Bearer sk-test")
        self.assertEqual(captured["body"]["model"], DEFAULT_MODEL)
        self.assertEqual(captured["body"]["messages"][0]["content"], "hi")
        self.assertIn("model: deepseek-flash", printed)
        self.assertIn("[user]\nhi", printed)
        self.assertIn("finish_reason: stop", printed)
        self.assertIn('{"ok": true}', printed)
        self.assertNotIn("sk-test", printed)


if __name__ == "__main__":
    unittest.main()
