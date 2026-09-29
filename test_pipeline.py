import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.extract import extract
from coderagent.llm import LLMError
from coderagent.load import load_corpus, load_request, parse_source_text
from coderagent.models import Advice, Request, Stop
from coderagent.pipeline import NO_SOURCE, run

RAG_PAYLOAD = {
    "recommend": "RAG",
    "recommend_evidence_id": "rag-start",
    "reasons": [{"text": "先做输入输出固定的链路。", "evidence_id": "rag-start"}],
    "not_yet": [{"text": "多 Agent 先不做。", "evidence_id": "agent-later-multi"}],
    "next_step": {"text": "用笔记做一个带引用的问答。", "evidence_id": "rag-next"},
}

AGENT_PAYLOAD = {
    "recommend": "Agent",
    "recommend_evidence_id": "agent-start",
    "reasons": [{"text": "下一步学工具调用和状态。", "evidence_id": "agent-start"}],
    "not_yet": [{"text": "继续补充框架名单解决不了业务分支。", "evidence_id": "agent-later-frameworks"}],
    "next_step": {"text": "在会分支的那一步决定调用哪个工具。", "evidence_id": "agent-next"},
}


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = load_corpus(ROOT / "corpus")

    def test_beginner_uses_model_text_and_evidence_ref(self):
        result = self._run("rag_vs_agent.json")
        self.assertIsInstance(result.outcome, Advice)
        advice = result.outcome
        self.assertEqual(result.model, "deepseek-chat")
        self.assertEqual(advice.recommend.text, "RAG")
        self.assertEqual(advice.recommend.ref, "model:deepseek-chat:rag-start")
        self.assertEqual(advice.reasons[0].text, "先做输入输出固定的链路。")
        self.assertIn("带引用的问答", advice.next_step.text)
        self.assertTrue(any("多 Agent" in item.text for item in advice.not_yet))
        self.assertEqual(result.rejected, ())

    def test_same_comparison_different_advice(self):
        def complete(messages):
            user = messages[1]["content"]
            payload = AGENT_PAYLOAD if "已经做过一个笔记问答" in user else RAG_PAYLOAD
            return json.dumps(payload, ensure_ascii=False)

        beginner = run(self._request("rag_vs_agent.json"), self.sources, complete=complete, model="deepseek-chat")
        experienced = run(
            self._request("agent_after_rag.json"),
            self.sources,
            complete=complete,
            model="deepseek-chat",
        )
        self.assertEqual(beginner.comparison, experienced.comparison)
        self.assertEqual(experienced.outcome.recommend.text, "Agent")
        self.assertIn("调用哪个工具", experienced.outcome.next_step.text)

    def test_question_is_sent_to_the_model(self):
        seen = []

        def complete(messages):
            seen.append(messages[1]["content"])
            return json.dumps(RAG_PAYLOAD, ensure_ascii=False)

        request = self._request("rag_vs_agent.json")
        run(request, self.sources, complete=complete, model="deepseek-chat")
        run(
            Request("换一种说法", request.options, request.profile),
            self.sources,
            complete=complete,
            model="deepseek-chat",
        )
        self.assertIn(request.question, seen[0])
        self.assertIn("换一种说法", seen[1])
        self.assertNotIn('"stance"', seen[0])

    def test_steps_are_reported_in_order(self):
        events = []
        result = run(
            self._request("rag_vs_agent.json"),
            self.sources,
            complete=lambda messages: json.dumps(RAG_PAYLOAD, ensure_ascii=False),
            model="deepseek-chat",
            on_step=lambda step, state, text: events.append((step, state)),
        )
        self.assertIsInstance(result.outcome, Advice)
        self.assertEqual(
            [item for item in events if item[1] == "running"],
            [("retrieve", "running"), ("extract", "running"), ("compare", "running"), ("advise", "running")],
        )
        self.assertIn(("advise", "done"), events)

    def test_missing_source_skips_later_steps(self):
        events = []
        run(
            self._request("rust_vs_go.json"),
            self.sources,
            complete=lambda messages: (_ for _ in ()).throw(AssertionError("不应调用模型")),
            model="deepseek-chat",
            on_step=lambda step, state, text: events.append((step, state)),
        )
        self.assertEqual(
            events,
            [
                ("retrieve", "running"),
                ("retrieve", "stopped"),
                ("extract", "skipped"),
                ("compare", "skipped"),
                ("advise", "skipped"),
            ],
        )

    def test_unknown_options_do_not_call_the_model(self):
        def complete(messages):
            raise AssertionError("没有来源时不应调用模型")

        result = run(self._request("rust_vs_go.json"), self.sources, complete=complete, model="deepseek-chat")
        self.assertIsInstance(result.outcome, Stop)
        self.assertEqual(result.outcome.reason, NO_SOURCE)
        self.assertEqual(result.sources, ())
        self.assertEqual(result.model, "")

    def test_missing_key_when_model_is_needed(self):
        with self.assertRaises(LLMError):
            run(self._request("rag_vs_agent.json"), self.sources, complete=None, model="deepseek-chat")

    def test_program_does_not_insert_hours_into_advice(self):
        advice = self._run("rag_vs_agent.json").outcome
        blob = "\n".join(line.text for line in advice.technical_lines())
        self.assertNotIn("8", blob)

    def test_comparison_covers_every_dimension(self):
        result = self._run("rag_vs_agent.json")
        for row in result.comparison:
            for option, lines in row.cells:
                self.assertTrue(lines, f"{row.dimension} / {option}")

    def test_invalid_json_stops(self):
        result = run(
            self._request("rag_vs_agent.json"),
            self.sources,
            complete=lambda messages: "不是 json",
            model="deepseek-chat",
        )
        self.assertIsInstance(result.outcome, Stop)
        self.assertEqual(result.model, "deepseek-chat")

    def test_unknown_evidence_id_is_rejected(self):
        payload = {
            "recommend": "RAG",
            "recommend_evidence_id": "missing",
            "reasons": [{"text": "原因", "evidence_id": "rag-start"}],
            "not_yet": [{"text": "先不做", "evidence_id": "agent-later-multi"}],
            "next_step": {"text": "下一步", "evidence_id": "rag-next"},
        }
        result = run(
            self._request("rag_vs_agent.json"),
            self.sources,
            complete=lambda messages: json.dumps(payload, ensure_ascii=False),
            model="deepseek-chat",
        )
        self.assertIsInstance(result.outcome, Stop)

    def test_quote_missing_from_prose_is_dropped(self):
        source = parse_source_text(
            """---
id: src-rag
title: 测试
tags: RAG
---

正文里有这一句，用来对照。

```evidence
id: missing
option: RAG
dimension: 解决的问题
stance: info
quote: 这句话没有写进正文。
```
""",
            "memory.md",
        )
        evidence, rejected = extract([source])
        self.assertEqual(evidence, ())
        self.assertEqual(rejected, ("missing: 引用句不在原文中",))

    def _request(self, name: str):
        return load_request(ROOT / "examples" / name)

    def _run(self, name: str):
        return run(
            self._request(name),
            self.sources,
            complete=lambda messages: json.dumps(RAG_PAYLOAD, ensure_ascii=False),
            model="deepseek-chat",
        )


if __name__ == "__main__":
    unittest.main()
