"""Keyword baseline retrieval over a local JSON knowledge base.

Retrieval is deliberately simple: CJK character bigrams plus lowercase
ASCII words, scored by overlap with the query. Embeddings and a vector
store are a later step once keyword quality stops being enough.
"""

import json
import re

MIN_SCORE = 0.1
TOP_K = 2


def tokenize(text: str) -> list[str]:
    """CJK character bigrams plus lowercase ASCII words."""

    tokens = [word for word in re.findall(r"[a-zA-Z0-9]+", text.lower())]
    cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
    tokens.extend(cjk[i : i + 2] for i in range(len(cjk) - 1))
    return tokens


class KnowledgeBase:
    """Ordered FAQ entries with in-memory keyword search."""

    def __init__(self, entries: list[dict]) -> None:
        self._entries = entries
        self._token_sets = [
            set(tokenize(entry["question"] + " " + entry["answer"])) for entry in entries
        ]

    @classmethod
    def load(cls, path: str) -> "KnowledgeBase":
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return cls(data["entries"])

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        """Return up to ``k`` entries overlapping the query above MIN_SCORE."""

        query_tokens = set(tokenize(query))
        if not query_tokens:
            return []

        scored = []
        for entry, doc_tokens in zip(self._entries, self._token_sets, strict=True):
            score = len(query_tokens & doc_tokens) / len(query_tokens)
            if score >= MIN_SCORE:
                scored.append((score, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:k]]

    @staticmethod
    def as_context(hits: list[dict]) -> str:
        """Format hits for the system prompt; empty when nothing hit."""

        return "\n\n".join(f"【{entry['question']}】\n{entry['answer']}" for entry in hits)
