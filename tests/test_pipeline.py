import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.advise import parse_advice
from coderagent.extract import extract
from coderagent.knowledge import Hit
from coderagent.llm import LLMError
from coderagent.load import load_corpus, load_request, parse_source_text
from coderagent.models import Advice, Evidence, Profile, Request, Stop
from coderagent.pipeline import NO_MATERIAL, run
from coderagent.react import EXHAUSTED

RAG_PAYLOAD = {
    "recommend": "RAG",
    "recommend_evidence_id": "src-rag-0",
    "reasons": [{"text": "先做输入输出固定的链路。", "evidence_id": "src-rag-0"}],
    "not_yet": [{"text": "多 Agent 先不做。", "evidence_id": "src-agent-0"}],
    "next_step": {"text": "用笔记做一个带引用的问答。", "evidence_id": "src-rag-0"},
}

AGENT_PAYLOAD = {
    "recommend": "Agent",
    "recommend_evidence_id": "src-agent-0",
    "reasons": [{"text": "下一步学工具调用和状态。", "evidence_id": "src-agent-0"}],
    "not_yet": [{"text": "继续补充框架名单解决不了业务分支。", "evidence_id": "src-rag-0"}],
    "next_step": {"text": "在会分支的那一步决定调用哪个工具。", "evidence_id": "src-agent-0"},
}


class CorpusHits:
    """测试用知识库：正文里出现检索词就返回一段，不走标签。"""

    def __init__(self, corpus_dir: Path):
        self.corpus_dir = corpus_dir

    def index_corpus(self, corpus_dir: Path) -> None:
        self.corpus_dir = corpus_dir

    def search(self, query: str, limit: int = 4) -> list[Hit]:
        hits = []
        for source in load_corpus(self.corpus_dir):
            if source.id not in {"src-rag", "src-agent"}:
                continue
            text = source.body.split("\n\n", 1)[0].strip()
            hits.append(Hit(source.id, source.path, "", text, source.body.index(text), source.body.index(text) + len(text), 0.9))
        return hits[:limit]


def tool(name, arguments, call_id):
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)},
            }
        ],
    }


def studied(payload):
    def turn(messages, tools):
        blob = json.dumps(messages, ensure_ascii=False)
        if "src-rag-0" not in blob:
            return tool("lookup", {"query": "RAG 是什么", "option": "RAG"}, "rag")
        if "src-agent-0" not in blob:
            return tool("lookup", {"query": "Agent 是什么", "option": "Agent"}, "agent")
        return tool("submit_advice", payload, "advice")

    return turn


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.corpus = Path(self._tmp.name) / "corpus"
        self.corpus.mkdir()
        for path in (ROOT / "corpus").glob("*.md"):
            shutil.copy(path, self.corpus / path.name)
        self.searches = []

    def tearDown(self):
        self._tmp.cleanup()

    def test_beginner_uses_model_text_and_evidence_ref(self):
        result = self._run("rag_vs_agent.json", studied(RAG_PAYLOAD))
        self.assertIsInstance(result.outcome, Advice)
        advice = result.outcome
        self.assertEqual(result.model, "deepseek-flash")
        self.assertEqual(advice.recommend.text, "RAG")
        self.assertEqual(advice.recommend.ref, "model:deepseek-flash:src-rag-0")
        self.assertEqual(advice.reasons[0].text, "先做输入输出固定的链路。")
        self.assertIn("带引用的问答", advice.next_step.text)
        self.assertTrue(any("多 Agent" in item.text for item in advice.not_yet))
        self.assertEqual(self.searches, [])

    def test_same_comparison_different_advice(self):
        def turn(messages, tools):
            user = messages[1]["content"]
            payload = AGENT_PAYLOAD if "已经做过一个笔记问答" in user else RAG_PAYLOAD
            return studied(payload)(messages, tools)

        beginner = self._run("rag_vs_agent.json", turn)
        experienced = self._run("agent_after_rag.json", turn)
        self.assertEqual(beginner.comparison, experienced.comparison)
        self.assertEqual(experienced.outcome.recommend.text, "Agent")
        self.assertIn("调用哪个工具", experienced.outcome.next_step.text)

    def test_question_is_sent_to_the_model(self):
        seen = []

        def turn(messages, tools):
            if len(messages) == 2:
                seen.append(messages[1]["content"])
            return studied(RAG_PAYLOAD)(messages, tools)

        request = self._request("rag_vs_agent.json")
        self._run_request(request, turn)
        rewritten = Request("换一种说法", request.options, request.profile)
        self._run_request(rewritten, turn)
        self.assertIn(request.question, seen[0])
        self.assertIn("换一种说法", seen[1])

    def test_text_only_reply_omits_empty_tool_calls(self):
        seen = []

        def turn(messages, tools):
            seen.append(messages)
            if len(seen) == 1:
                return {"role": "assistant", "content": "我先说明一下", "tool_calls": []}
            self.assertNotIn("tool_calls", seen[1][2])
            return studied(RAG_PAYLOAD)(messages, tools)

        result = self._run("rag_vs_agent.json", turn)
        self.assertIsInstance(result.outcome, Advice)

    def test_steps_follow_the_research_loop(self):
        events = []
        result = self._run(
            "rag_vs_agent.json",
            studied(RAG_PAYLOAD),
            on_step=lambda step, state, text: events.append((step, state, text)),
        )
        self.assertIsInstance(result.outcome, Advice)
        self.assertIn(("research", "done"), [(step, state) for step, state, _ in events])
        done = next(text for step, state, text in events if state == "done")
        self.assertIn("从知识库读到", done)
        self.assertIn("建议先做 RAG", done)

    def test_missing_material_does_not_invent_advice(self):
        def turn(messages, tools):
            if any(item.get("role") == "tool" for item in messages):
                return tool("submit_advice", {"recommend": "Rust"}, "bad")
            return tool("lookup", {"query": "Rust 和 Go", "option": "Rust"}, "rust")

        before = {path.name for path in self.corpus.glob("web-*.md")}
        result = self._run("rust_vs_go.json", turn, search=self._no_page)
        self.assertIsInstance(result.outcome, Stop)
        self.assertEqual(result.outcome.reason, NO_MATERIAL)
        self.assertEqual(self.searches, [("Rust", "应该先学习 Rust 还是 Go？")])
        self.assertEqual({path.name for path in self.corpus.glob("web-*.md")}, before)

    def test_invalid_advice_can_be_resubmitted(self):
        attempts = {"advice": 0}

        def turn(messages, tools):
            blob = json.dumps(messages, ensure_ascii=False)
            if "src-rag-0" not in blob:
                return tool("lookup", {"query": "RAG", "option": "RAG"}, "rag")
            if "src-agent-0" not in blob:
                return tool("lookup", {"query": "Agent", "option": "Agent"}, "agent")
            attempts["advice"] += 1
            if attempts["advice"] == 1:
                return tool("submit_advice", {"recommend": "RAG", "recommend_evidence_id": "missing"}, "bad")
            return tool("submit_advice", RAG_PAYLOAD, "good")

        result = self._run("rag_vs_agent.json", turn)
        self.assertIsInstance(result.outcome, Advice)
        self.assertEqual(result.outcome.recommend.text, "RAG")

    def test_invalid_json_stops_at_the_round_limit(self):
        result = self._run(
            "rag_vs_agent.json",
            lambda messages, tools: tool("submit_advice", "不是 json", "bad"),
        )
        self.assertIsInstance(result.outcome, Stop)
        self.assertEqual(result.outcome.reason, NO_MATERIAL)
        self.assertEqual(result.model, "deepseek-flash")

    def test_unknown_evidence_id_is_rejected_until_the_limit(self):
        def turn(messages, tools):
            blob = json.dumps(messages, ensure_ascii=False)
            if "src-rag-0" not in blob:
                return tool("lookup", {"query": "RAG", "option": "RAG"}, "rag")
            return tool(
                "submit_advice",
                {
                    "recommend": "RAG",
                    "recommend_evidence_id": "missing",
                    "reasons": [{"text": "原因", "evidence_id": "rag-start"}],
                    "not_yet": [{"text": "先不做", "evidence_id": "rag-start"}],
                    "next_step": {"text": "下一步", "evidence_id": "rag-next"},
                },
                "bad",
            )

        result = self._run("rag_vs_agent.json", turn)
        self.assertIsInstance(result.outcome, Stop)
        self.assertEqual(result.outcome.reason, EXHAUSTED)

    def test_missing_key_when_model_is_needed(self):
        with self.assertRaises(LLMError):
            run(self._request("rag_vs_agent.json"), self.corpus, turn=None, model="deepseek-flash")

    def test_program_does_not_insert_hours_into_advice(self):
        advice = self._run("rag_vs_agent.json", studied(RAG_PAYLOAD)).outcome
        blob = "\n".join(line.text for line in advice.technical_lines())
        self.assertNotIn("8", blob)

    def test_comparison_covers_every_dimension(self):
        result = self._run("rag_vs_agent.json", studied(RAG_PAYLOAD))
        dimensions = {row.dimension for row in result.comparison}
        self.assertEqual(dimensions, {"资料原句"})
        for row in result.comparison:
            for option, lines in row.cells:
                self.assertTrue(lines, f"{row.dimension} / {option}")

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

    def _run(self, name: str, turn, search=None, on_step=None):
        return self._run_request(self._request(name), turn, search, on_step)

    def _run_request(self, request, turn, search=None, on_step=None):
        return run(
            request,
            self.corpus,
            turn=turn,
            model="deepseek-flash",
            on_step=on_step,
            search=search or self._unexpected_search,
            knowledge=CorpusHits(self.corpus),
        )

    def _unexpected_search(self, query, option, question=""):
        raise AssertionError(f"知识库已有资料，不应联网：{query}")

    def _no_page(self, query, option, question=""):
        self.searches.append((query, question))
        return None


class AdviceFieldTest(unittest.TestCase):
    def test_rejection_names_text_and_evidence_id(self):
        request = Request(
            "先学哪个？",
            ("RAG", "Agent"),
            Profile(("Python",), False, "demo", 8),
        )
        evidence = (
            Evidence("rag-start", "rag", "RAG", "资料原句", "info", "先把输入输出固定下来。"),
        )
        raw = json.dumps(
            {
                "recommend": "RAG",
                "recommend_evidence_id": "rag-start",
                "reasons": [{"point": "先做固定链路。", "evidence_id": "rag-start"}],
                "not_yet": [{"text": "多 Agent 先不做。", "evidence_id": "rag-start"}],
                "next_step": {"reason": "用笔记做一个问答。"},
            },
            ensure_ascii=False,
        )
        outcome, rejected = parse_advice(raw, request, evidence, "deepseek-flash")
        self.assertIsInstance(outcome, Stop)
        self.assertIn("text", outcome.reason)
        self.assertIn("evidence_id", outcome.reason)
        self.assertTrue(any("缺少 text" in item for item in rejected))
        self.assertTrue(any("缺少 evidence_id" in item for item in rejected))


if __name__ == "__main__":
    unittest.main()
