import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.__main__ import _ask_until_ready
from coderagent.intake import NeedInput, parse_user_text

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
        self.assertIn("应该先学 RAG 还是 Agent？", request.question)
        self.assertIn("每周投入 8 小时", request.question)
        self.assertIn("在 RAG、Agent 之间选", request.question)
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

        with self.assertRaises(NeedInput) as caught:
            parse_user_text(USER_TEXT, lambda messages: json.dumps(payload))
        self.assertEqual(str(caught.exception), "每周可投入多少小时？")
        self.assertEqual(caught.exception.step, "hours")

    def test_blank_hours_defaults_to_eight_then_asks_direction(self):
        payload = {
            "question": "现在怎么转 AI",
            "options": [],
            "profile": {
                "background": ["Java"],
                "prior_ai_project": None,
                "goal": None,
                "hours_per_week": None,
            },
        }

        with self.assertRaises(NeedInput) as caught:
            parse_user_text("我是做 Java 的，现在怎么转 AI", lambda messages: json.dumps(payload), asked="hours", answer="")
        self.assertEqual(str(caught.exception), "想在什么方向上做选择？说两到三个方向就行。")
        self.assertEqual(caught.exception.step, "direction")
        self.assertEqual(caught.exception.carry, "每周投入 8 小时")

    def test_hours_question_comes_before_direction(self):
        payload = {
            "question": "现在怎么转 AI",
            "options": [],
            "profile": {"background": ["Java"], "prior_ai_project": None, "goal": None, "hours_per_week": None},
        }
        with self.assertRaises(NeedInput) as caught:
            parse_user_text("我是做 Java 的，现在怎么转 AI", lambda messages: json.dumps(payload))
        self.assertEqual(caught.exception.step, "hours")

    def test_terminal_waits_for_the_next_answer(self):
        def complete(messages):
            user = messages[1]["content"]
            options = ["检索", "微调"] if "检索" in user else []
            hours = 8 if "每周投入" in user else None
            return json.dumps(
                {
                    "question": "现在怎么转 AI",
                    "options": options,
                    "profile": {
                        "background": ["Java"],
                        "prior_ai_project": None,
                        "goal": None,
                        "hours_per_week": hours,
                    },
                },
                ensure_ascii=False,
            )

        questions = []
        replies = iter(["", "检索和微调"])

        def read_reply(question):
            questions.append(question)
            return next(replies)

        request = _ask_until_ready("我是做 Java 的，现在怎么转 AI", complete, read_reply)
        self.assertEqual(
            questions,
            ["每周可投入多少小时？", "想在什么方向上做选择？说两到三个方向就行。"],
        )
        self.assertEqual(request.profile.hours_per_week, 8)
        self.assertEqual(request.options, ("检索", "微调"))
        self.assertIn("每周投入 8 小时", request.question)
        self.assertIn("在 检索、微调 之间选", request.question)

    def test_direction_names_are_kept_when_the_model_drops_them(self):
        payload = {
            "question": "我是做JAVA的，现在怎么转AI呢",
            "options": [],
            "profile": {
                "background": ["Java"],
                "prior_ai_project": None,
                "goal": None,
                "hours_per_week": 5,
            },
        }

        def complete(messages):
            self.assertIn("按用户的写法原样保留", messages[0]["content"])
            return json.dumps(payload, ensure_ascii=False)

        quoted = parse_user_text(
            "我是做JAVA的，现在怎么转AI呢\n每周投入 5 小时",
            complete,
            asked="direction",
            answer='SFT “loop engineering" "context engineering"',
        )
        self.assertEqual(quoted.options, ("SFT", "loop engineering", "context engineering"))

        short = parse_user_text(
            "我是做JAVA的，现在怎么转AI呢\n每周投入 5 小时",
            complete,
            asked="direction",
            answer="SFT loop context",
        )
        self.assertEqual(short.options, ("SFT", "loop", "context"))


if __name__ == "__main__":
    unittest.main()
