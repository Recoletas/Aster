"""Knowledge bases with a shared retrieval interface.

Two implementations behind the same ``search``/``as_context`` shape:
``KnowledgeBase`` (keyword baseline, offline) and
``EmbeddingKnowledgeBase`` (MiniMax embo-01, asymmetric db/query
retrieval). Strategies only see the interface.
"""

import json
import re

from aster.embeddings import MiniMaxEmbeddings, cosine

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


class EmbeddingKnowledgeBase:
    """Retrieval by MiniMax embeddings with the asymmetric db/query split.

    Document vectors are computed once at load time (``type=db``); each
    query embeds the question (``type=query``). Not persisted — small
    knowledge bases re-embed in one call at startup.
    """

    def __init__(self, entries: list[dict], embeddings: MiniMaxEmbeddings) -> None:
        self._entries = entries
        self._embeddings = embeddings
        self._doc_vectors = embeddings.embed(
            [entry["question"] + " " + entry["answer"] for entry in entries],
            type="db",
        )

    @classmethod
    def load(cls, path: str, embeddings: MiniMaxEmbeddings) -> "EmbeddingKnowledgeBase":
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return cls(data["entries"], embeddings)

    def search(self, query: str, k: int = TOP_K) -> list[dict]:
        """Return the top-k entries most similar to the query vector."""

        [query_vector] = self._embeddings.embed([query], type="query")
        scored = [
            (cosine(query_vector, doc_vector), entry)
            for entry, doc_vector in zip(self._entries, self._doc_vectors, strict=True)
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for score, entry in scored[:k] if score > 0]

    @staticmethod
    def as_context(hits: list[dict]) -> str:
        return KnowledgeBase.as_context(hits)
