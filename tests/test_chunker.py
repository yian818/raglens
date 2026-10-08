import unittest

from rag_lens.chunker import (
    chunk_document,
    fixed_split,
    markdown_heading_split,
    sentence_split,
)


class TestFixedSplit(unittest.TestCase):
    def test_basic(self):
        text = "一二三四五六七八九十" * 10  # 100 字
        pieces = fixed_split(text, chunk_size=30, overlap=5)
        self.assertTrue(all(len(p) <= 30 for p, _ in pieces))
        self.assertGreater(len(pieces), 3)

    def test_overlap_not_larger_than_size(self):
        with self.assertRaises(ValueError):
            fixed_split("abcdefgh", chunk_size=10, overlap=10)

    def test_empty_text(self):
        self.assertEqual(fixed_split("", chunk_size=10, overlap=2), [])


class TestSentenceSplit(unittest.TestCase):
    def test_short_text_one_chunk(self):
        pieces = sentence_split("第一句。第二句！第三句？", max_len=100)
        self.assertEqual(len(pieces), 1)

    def test_long_text_splits(self):
        text = "句子。" * 50  # 200 字
        pieces = sentence_split(text, max_len=30)
        self.assertGreater(len(pieces), 1)


class TestChunkDocument(unittest.TestCase):
    def test_metadata(self):
        chunks = chunk_document("a.md", "句子一。句子二。", {"name": "s", "type": "sentence", "max_len": 100})
        self.assertTrue(all(c.doc_id == "a.md" for c in chunks))
        self.assertTrue(all(c.chunk_id.startswith("s:a.md:") for c in chunks))

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            chunk_document("a.md", "任意文本", {"name": "x", "type": "weird"})


class TestMarkdownHeading(unittest.TestCase):
    def test_sections_split_by_heading(self):
        text = "# 标题一\n内容一。\n## 标题二\n内容二。"
        pieces = markdown_heading_split(text)
        self.assertEqual(len(pieces), 2)
        self.assertTrue(pieces[0][0].startswith("# 标题一"))

    def test_no_heading_falls_back(self):
        pieces = markdown_heading_split("没有标题的一段文本。")
        self.assertEqual(len(pieces), 1)

    def test_long_section_resplits(self):
        text = "# 长章节\n" + "句子。" * 50
        pieces = markdown_heading_split(text, max_len=80)
        self.assertGreater(len(pieces), 1)
        # 二次切分后每段仍保留标题
        self.assertTrue(all("长章节" in p[0] for p in pieces))


if __name__ == "__main__":
    unittest.main()
