import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.judge import answers_question


class JudgeTest(unittest.TestCase):
    def test_keeps_a_page_that_explains_the_option(self):
        seen = []

        def complete(messages):
            seen.extend(messages)
            return '{"answer": true}'

        kept = answers_question(
            "我是做 Java 的，现在怎么转 AI 呢\n每周投入 6 小时",
            "上下文工程",
            "上下文工程是在调用模型前组装该放进窗口的信息。",
            complete,
        )

        blob = json.dumps(seen, ensure_ascii=False)
        self.assertTrue(kept)
        self.assertIn("上下文工程", blob)
        self.assertNotIn("每周投入", blob)
        self.assertIn("讲这个选项", blob)

    def test_rejects_a_page_the_model_marks_unrelated(self):
        def complete(messages):
            return '{"answer": false}'

        self.assertFalse(answers_question("问题", "RRF", "加权求和公式是 A 乘以 B。", complete))


if __name__ == "__main__":
    unittest.main()
