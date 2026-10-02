import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from coderagent.chunk import chunk_text, split_units


class ChunkTest(unittest.TestCase):
    def test_sentences_stay_whole_and_overlap(self):
        sentences = [
            "甲" * 120 + "。",
            "乙" * 120 + "。",
            "丙" * 120 + "。",
            "丁" * 120 + "。",
        ]
        text = "".join(sentences)
        chunks = chunk_text(text, size=250, overlap=60)

        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, sentences[0] + sentences[1])
        self.assertTrue(chunks[1].text.startswith(sentences[1]))
        self.assertLess(chunks[1].start, chunks[0].end)
        for chunk in chunks:
            self.assertEqual(text[chunk.start : chunk.end], chunk.text)
            self.assertTrue(chunk.text.endswith("。"))

    def test_long_sentence_is_not_cut(self):
        sentence = "长" * 500 + "。"
        chunks = chunk_text(sentence, size=200, overlap=50)
        self.assertEqual(chunks, [chunks[0]])
        self.assertEqual(chunks[0].text, sentence)

    def test_blank_line_is_a_boundary(self):
        text = "第一段没有句号\n\n第二段也没有句号"
        units = split_units(text)
        self.assertEqual([text[start:end] for start, end in units], ["第一段没有句号", "第二段也没有句号"])

    def test_short_sentence_is_merged(self):
        text = "甲" * 80 + "。加入我们！" + "乙" * 400 + "。"
        chunks = chunk_text(text, size=320, overlap=64)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertTrue(all(len(chunk.text.strip()) >= 40 for chunk in chunks))
        self.assertNotEqual([chunk.text.strip() for chunk in chunks], ["加入我们！"])
        self.assertTrue(any("加入我们！" in chunk.text for chunk in chunks))
        self.assertTrue(any("乙" in chunk.text for chunk in chunks))

    def test_empty_text_has_no_chunks(self):
        self.assertEqual(chunk_text("   \n\n  "), [])


if __name__ == "__main__":
    unittest.main()
