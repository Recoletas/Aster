import unittest

from aster.embeddings import cosine
from aster.knowledge import EmbeddingKnowledgeBase, KnowledgeBase

ENTRIES = [
    {"question": "Aster 使用什么数据库？", "answer": "当前没有数据库。"},
    {"question": "Aster 如何运行测试？", "answer": "make check。"},
]


class FakeEmbeddings:
    """Embeds by keyword lookup so tests control similarity exactly."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[str], str]] = []

    def embed(self, texts: list[str], type: str) -> list[list[float]]:
        self.calls.append((texts, type))
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        return [
            1.0 if "数据库" in text else 0.0,
            1.0 if "测试" in text else 0.0,
        ]


class CosineTest(unittest.TestCase):
    def test_identical_and_orthogonal(self) -> None:
        self.assertAlmostEqual(cosine([1.0, 0.0], [1.0, 0.0]), 1.0)
        self.assertAlmostEqual(cosine([1.0, 0.0], [0.0, 1.0]), 0.0)

    def test_zero_vectors_score_zero(self) -> None:
        self.assertEqual(cosine([0.0, 0.0], [1.0, 1.0]), 0.0)


class EmbeddingKnowledgeBaseTest(unittest.TestCase):
    def test_search_ranks_by_cosine_and_splits_db_query(self) -> None:
        fake = FakeEmbeddings()
        kb = EmbeddingKnowledgeBase(ENTRIES, fake)

        hits = kb.search("用什么数据库")

        self.assertEqual(hits[0]["question"], ENTRIES[0]["question"])
        types = [t for _, t in fake.calls]
        self.assertIn("db", types)
        self.assertIn("query", types)
        self.assertEqual(fake.calls[0][1], "db")
        self.assertEqual(fake.calls[-1][1], "query")

    def test_orthogonal_entry_not_returned(self) -> None:
        kb = EmbeddingKnowledgeBase(ENTRIES, FakeEmbeddings())

        self.assertEqual(kb.search("如何运行测试")[0]["question"], ENTRIES[1]["question"])

    def test_load_reads_entries_and_embeds_docs(self) -> None:
        import json
        import os
        import tempfile

        fake = FakeEmbeddings()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "kb.json")
            with open(path, "w", encoding="utf-8") as file:
                json.dump({"entries": ENTRIES}, file, ensure_ascii=False)

            kb = EmbeddingKnowledgeBase.load(path, fake)

        self.assertEqual(len(kb.search("数据库")), 1)
        self.assertEqual(len(fake.calls[0][0]), len(ENTRIES))

    def test_context_format_matches_keyword_base(self) -> None:
        hits = [ENTRIES[0]]

        self.assertEqual(
            EmbeddingKnowledgeBase.as_context(hits),
            KnowledgeBase.as_context(hits),
        )


if __name__ == "__main__":
    unittest.main()
