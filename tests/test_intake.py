import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.intake import parse_user_text
from coderagent.load import InputError

USER_TEXT = "我有 Python 和后端经验，每周 8 小时，还没做过 AI 项目，想先做个能演示的应用。应该先学 RAG 还是 Agent？"

PARSED = {
    "question": "应该先学 RAG 还是 Agent？",
    "options": ["RAG", "Agent"],
    "profile": {
        "background": ["Python", "后端经验"],
        "prior_ai_project": False,
        "goal": "demo",
        "hours_per_week": 8,
    },
    "missing": [],
}


class IntakeTest(unittest.TestCase):
    def test_user_text_is_split_into_question_options_and_profile(self):
        seen = []

        def complete(messages):
            seen.append(messages)
            return json.dumps(PARSED, ensure_ascii=False)

        request = parse_user_text(USER_TEXT, complete)
        self.assertEqual(request.question, "应该先学 RAG 还是 Agent？")
        self.assertEqual(request.options, ("RAG", "Agent"))
        self.assertEqual(request.profile.background, ("Python", "后端经验"))
        self.assertFalse(request.profile.prior_ai_project)
        self.assertEqual(request.profile.goal, "demo")
        self.assertEqual(request.profile.hours_per_week, 8)
        self.assertIn(USER_TEXT, seen[0][1]["content"])

    def test_missing_hours_are_not_invented(self):
        payload = {
            "question": "应该先学 RAG 还是 Agent？",
            "options": ["RAG", "Agent"],
            "profile": {
                "background": ["Python"],
                "prior_ai_project": False,
                "goal": "demo",
                "hours_per_week": None,
            },
            "missing": ["hours_per_week"],
        }

        with self.assertRaises(InputError) as caught:
            parse_user_text(USER_TEXT, lambda messages: json.dumps(payload))
        self.assertIn("每周投入时间", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
