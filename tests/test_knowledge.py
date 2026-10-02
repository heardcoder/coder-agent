import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.knowledge import KnowledgeBase
from coderagent.load import parse_source_text


def embed(texts):
    vectors = []
    for text in texts:
        if "LangGraph" in text:
            vectors.append([1.0, 0.0])
        else:
            vectors.append([0.0, 1.0])
    return vectors


def note(body: str, note_id: str) -> str:
    return f"---\nid: {note_id}\ntitle: {note_id}\ntags: 图\nurl: https://example.com/{note_id}\n---\n\n{body}\n"


class KnowledgeTest(unittest.TestCase):
    def test_search_returns_the_closer_paragraph(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            corpus = folder / "corpus"
            corpus.mkdir()
            (corpus / "graph.md").write_text(
                note("LangGraph 用图来保存每一步的状态，适合把流程画成节点。", "graph"),
                encoding="utf-8",
            )
            (corpus / "other.md").write_text(
                note("这是一段和选项无关的说明，讲的是别的事情。", "other"),
                encoding="utf-8",
            )
            base = KnowledgeBase(folder / "knowledge.sqlite", embed)
            base.index_corpus(corpus)
            hits = base.search("LangGraph")
            self.assertEqual(hits[0].note_id, "graph")
            self.assertGreater(hits[0].score, 0.9)
            self.assertIn("LangGraph", hits[0].text)
            self.assertEqual(hits[0].url, "https://example.com/graph")
            self.assertLess(hits[-1].score, 0.2)

    def test_index_can_be_rebuilt_from_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            corpus = folder / "corpus"
            corpus.mkdir()
            raw = note("LangGraph 用图来保存每一步的状态。", "graph")
            (corpus / "graph.md").write_text(raw, encoding="utf-8")
            path = folder / "knowledge.sqlite"
            KnowledgeBase(path, embed).index_corpus(corpus)
            path.unlink()
            hits = KnowledgeBase(path, embed).search("LangGraph")
            self.assertEqual(hits, [])
            KnowledgeBase(path, embed).index_corpus(corpus)
            hits = KnowledgeBase(path, embed).search("LangGraph")
            self.assertEqual(hits[0].note_id, "graph")
            source = parse_source_text(raw, "corpus/graph.md")
            self.assertIn(hits[0].text, source.body)

    def test_changed_note_replaces_old_chunks(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            base = KnowledgeBase(folder / "knowledge.sqlite", embed)
            first = parse_source_text(
                note("LangGraph 用图来保存每一步的状态。", "graph"),
                "corpus/graph.md",
            )
            second = parse_source_text(
                note("LangGraph 后来改成了另一段说明，专门讲状态怎么保存。", "graph"),
                "corpus/graph.md",
            )
            base.add_source(first)
            base.add_source(second)
            hits = base.search("LangGraph", limit=10)
            texts = [hit.text for hit in hits]
            self.assertTrue(any("后来改成" in text for text in texts))
            self.assertFalse(any("每一步的状态" in text for text in texts))

    def test_same_note_is_not_indexed_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            corpus = folder / "corpus"
            corpus.mkdir()
            (corpus / "graph.md").write_text(
                note("LangGraph 用图来保存每一步的状态。", "graph"),
                encoding="utf-8",
            )
            base = KnowledgeBase(folder / "knowledge.sqlite", embed)
            base.index_corpus(corpus)
            base.index_corpus(corpus)
            hits = base.search("LangGraph", limit=10)
            self.assertEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main()
