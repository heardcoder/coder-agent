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

        def search(query, option):
            calls.append((query, option))
            return PAGE

        with tempfile.TemporaryDirectory() as tmp:
            corpus = Path(tmp) / "corpus"
            corpus.mkdir()
            first = lookup(corpus, "GraphQL 是什么", "GraphQL", search)
            self.assertEqual(first.origin, "web")
            self.assertTrue(first.evidence)
            self.assertTrue((corpus / "web-graphql.md").exists())
            for item in first.evidence:
                self.assertIn(item.quote, (corpus / "web-graphql.md").read_text(encoding="utf-8"))
            second = lookup(corpus, "GraphQL 入门", "GraphQL", search)
            self.assertEqual(second.origin, "local")
            self.assertEqual(calls, [("GraphQL", "GraphQL")])

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


if __name__ == "__main__":
    unittest.main()
