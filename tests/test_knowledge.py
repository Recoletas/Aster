import json
import os
import tempfile
import unittest

from aster.knowledge import KnowledgeBase, tokenize

ENTRIES = [
    {
        "question": "Aster 使用什么数据库？",
        "answer": "当前没有数据库，持久化是单 JSON 文件实验。",
    },
    {
        "question": "Aster 如何运行测试？",
        "answer": "执行 .venv/bin/python -m unittest discover -s tests。",
    },
]


class TokenizeTest(unittest.TestCase):
    def test_ascii_words_and_cjk_bigrams(self) -> None:
        self.assertEqual(tokenize("Aster 用SQLite"), ["aster", "sqlite"])
        self.assertEqual(tokenize("数据库"), ["数据", "据库"])
        self.assertEqual(tokenize("！"), [])

    def test_single_cjk_char_yields_no_bigram(self) -> None:
        self.assertEqual(tokenize("库"), [])


class KnowledgeBaseTest(unittest.TestCase):
    def test_search_ranks_relevant_entry_first(self) -> None:
        kb = KnowledgeBase(ENTRIES)

        hits = kb.search("aster 用什么数据库存储会话？")

        self.assertEqual(hits[0]["question"], ENTRIES[0]["question"])

    def test_search_returns_empty_without_overlap(self) -> None:
        kb = KnowledgeBase(ENTRIES)

        self.assertEqual(kb.search("xyz"), [])

    def test_load_reads_entries_from_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "kb.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump({"entries": ENTRIES}, file, ensure_ascii=False)

            kb = KnowledgeBase.load(path)

        self.assertEqual(kb.search("怎么运行测试")[0]["question"], ENTRIES[1]["question"])

    def test_as_context_formats_and_handles_empty(self) -> None:
        self.assertEqual(KnowledgeBase.as_context([]), "")
        context = KnowledgeBase.as_context([ENTRIES[0]])

        self.assertIn("【Aster 使用什么数据库？】", context)
        self.assertIn("单 JSON 文件实验", context)


if __name__ == "__main__":
    unittest.main()
