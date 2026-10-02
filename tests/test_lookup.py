import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.knowledge import KnowledgeBase
from coderagent.lookup import _result_links, lookup, search_web

PAGE = (
    "GraphQL 简介",
    "GraphQL 让客户端按需取字段，而不是每次拿回固定的接口结构。后端开发者已经熟悉请求和返回。",
)


class LookupTest(unittest.TestCase):
    def test_bing_result_links_skip_bing_itself(self):
        html = (
            '<h2><a href="https://www.bing.com/search?q=x">跳过</a></h2>'
            '<h2><a href="https://example.com/a">结果</a></h2>'
        )
        self.assertEqual(_result_links(html), ["https://example.com/a"])

    def test_web_page_is_saved_and_reused(self):
        calls = []

        def search(query, option, question=""):
            calls.append((query, option, question))
            return PAGE

        def embed(texts):
            return [[1.0 if "GraphQL" in text else 0.0] for text in texts]

        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus"
            corpus.mkdir()
            knowledge = KnowledgeBase(Path(tmp) / "knowledge.sqlite", embed)
            first = lookup(corpus, "GraphQL 是什么", "GraphQL", search, knowledge, "GraphQL 怎么按需取字段")
            self.assertEqual(first.origin, "web")
            self.assertTrue(first.evidence)
            self.assertTrue((corpus / "web-graphql.md").exists())
            for item in first.evidence:
                self.assertIn(item.quote, (corpus / "web-graphql.md").read_text(encoding="utf-8"))
            second = lookup(corpus, "GraphQL 入门", "GraphQL", search, knowledge, "GraphQL 入门时怎么取字段")
            self.assertEqual(second.origin, "knowledge")
            self.assertEqual(calls, [("GraphQL", "GraphQL", "GraphQL 怎么按需取字段")])

    def test_search_logs_the_page_it_keeps(self):
        pages = {
            "https://www.bing.com/search?q=LangGraph&setlang=zh-Hans": (
                '<h2><a href="https://example.com/dict">词典</a></h2>'
            '<h2><a href="https://example.com/langgraph">LangGraph</a></h2>'
            ),
            "https://example.com/dict": "<title>应该的意思</title><p>" + ("情理上必然或必须如此。" * 8) + "</p>",
            "https://example.com/langgraph": (
                "<title>LangGraph 简介</title><p>"
                + ("LangGraph 用图来保存每一步的状态。" * 5)
                + "</p>"
            ),
        }

        def fake_get(url):
            return pages.get(url)

        logs = io.StringIO()
        with mock.patch("coderagent.lookup._get", fake_get), redirect_stderr(logs):
            found = search_web("LangGraph")

        printed = logs.getvalue()
        self.assertIsNotNone(found)
        self.assertIn("query: LangGraph", printed)
        self.assertIn("https://example.com/langgraph", printed)
        self.assertIn("页面未提到 LangGraph：https://example.com/dict", printed)
        self.assertIn("采用：LangGraph 简介", printed)
        self.assertIn("LangGraph 用图来保存每一步的状态。", printed)
        self.assertEqual(found[0], "LangGraph 简介")

    def test_knowledge_hit_skips_web(self):
        calls = []

        def search(query, option, question=""):
            calls.append((query, option, question))
            return PAGE

        def embed(texts):
            return [[1.0, 0.0] if "LangGraph" in text else [0.0, 1.0] for text in texts]

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            corpus = folder / "corpus"
            corpus.mkdir()
            (corpus / "graph.md").write_text(
                "---\n"
                "id: graph\n"
                "title: 图流程\n"
                "tags: 图\n"
                "---\n\n"
                "LangGraph 用图来保存每一步的状态，适合把流程画成节点。\n",
                encoding="utf-8",
            )
            base = KnowledgeBase(folder / "knowledge.sqlite", embed)
            found = lookup(corpus, "LangGraph 是什么", "LangGraph", search, base)

        self.assertEqual(found.origin, "knowledge")
        self.assertEqual(calls, [])
        self.assertTrue(found.evidence)
        self.assertIn("LangGraph", found.evidence[0].quote)

    def test_knowledge_search_uses_the_original_question(self):
        seen = []

        class Recording:
            def index_corpus(self, corpus_dir):
                return None

            def search(self, query, limit=4):
                seen.append(query)
                return []

        def search(query, option, question=""):
            return None

        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus"
            corpus.mkdir()
            found = lookup(
                corpus,
                "RRF",
                "RRF",
                search,
                Recording(),
                "两路检索结果应该用 RRF 融合，还是自己把分数加权加起来",
            )

        self.assertEqual(seen, ["两路检索结果应该用 RRF 融合，还是自己把分数加权加起来"])
        self.assertFalse(found.found)

    def test_unrelated_knowledge_still_searches_web(self):
        calls = []

        def search(query, option, question=""):
            calls.append(option)
            return PAGE

        def embed(texts):
            return [[1.0, 0.0] if "GraphQL" in text else [0.0, 1.0] for text in texts]

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            corpus = folder / "corpus"
            corpus.mkdir()
            (corpus / "other.md").write_text(
                "---\n"
                "id: other\n"
                "title: 别的\n"
                "tags: 其他\n"
                "---\n\n"
                "这是一段和选项无关的说明，讲的是别的事情，不能拿来引用。\n",
                encoding="utf-8",
            )
            base = KnowledgeBase(folder / "knowledge.sqlite", embed)
            found = lookup(corpus, "GraphQL 是什么", "GraphQL", search, base)

        self.assertEqual(calls, ["GraphQL"])
        self.assertEqual(found.origin, "web")

    def test_long_page_is_indexed_without_short_sentences(self):
        def search(query, option, question=""):
            return ("RRF 说明", "前面很多字。" + ("RRF 融合" + "甲" * 200))

        def embed(texts):
            return [[1.0, 0.0] if "RRF" in text else [0.0, 1.0] for text in texts]

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            corpus = folder / "corpus"
            corpus.mkdir()
            base = KnowledgeBase(folder / "knowledge.sqlite", embed)
            found = lookup(corpus, "RRF 融合", "RRF 融合", search, base)
            note = corpus / "web-rrf.md"
            self.assertTrue(note.exists())
            self.assertIn("RRF 融合", note.read_text(encoding="utf-8"))
            self.assertEqual(found.origin, "knowledge")
            self.assertTrue(found.evidence)

    def test_page_chrome_is_dropped_and_off_topic_page_is_skipped(self):
        pages = {
            "https://www.bing.com/search?q=RRF&setlang=zh-Hans": (
                '<h2><a href="https://example.com/math">数学</a></h2>'
                '<h2><a href="https://example.com/rrf">RRF</a></h2>'
            ),
            "https://example.com/math": "<title>公式</title><p>" + ("RRF 的加权求和公式是 A 乘以 B。" * 8) + "</p>",
            "https://example.com/rrf": (
                "<title>RRF</title><p>向TA提问 我来答。"
                + ("RRF 用排名融合两路检索结果。" * 6)
                + "</p>"
            ),
        }

        def fake_get(url):
            return pages.get(url)

        asked = []

        def judge(query, option, excerpt):
            asked.append(query)
            return "排名融合" in excerpt

        with mock.patch("coderagent.lookup._get", fake_get):
            found = search_web("RRF", "RRF", judge, question="两路结果怎么融合")

        self.assertEqual(asked, ["两路结果怎么融合", "两路结果怎么融合"])

        self.assertIsNotNone(found)
        self.assertNotIn("向TA提问", found[1])
        self.assertIn("排名融合", found[1])


if __name__ == "__main__":
    unittest.main()
