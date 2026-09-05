"""MiniMax text embeddings (embo-01) over the platform's own protocol.

Deliberately not OpenAI-compatible: the field is ``texts``, an asymmetric
``type`` (``db`` for stored content vs ``query`` for retrieval) is
required, and responses come back under ``vectors`` with ``base_resp``.
Transport is stdlib urllib; no new dependency.
"""

import json
import os
import urllib.request
from collections.abc import Callable
from typing import Any

EMBED_URL = "https://api.minimaxi.com/v1/embeddings"
MODEL = "embo-01"
TIMEOUT = 30.0

Poster = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]


def _post_json(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.load(response)


class MiniMaxEmbeddings:
    """Embedding client speaking MiniMax's embeddings protocol."""

    def __init__(self, api_key: str, poster: Poster = _post_json) -> None:
        self._api_key = api_key
        self._poster = poster

    def embed(self, texts: list[str], type: str) -> list[list[float]]:
        """Embed texts with ``type`` of ``db`` or ``query``; 1536-d vectors."""

        data = self._poster(
            EMBED_URL,
            {"model": MODEL, "type": type, "texts": texts},
            {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
        )
        status = data.get("base_resp", {}).get("status_code", -1)
        if status != 0:
            message = data.get("base_resp", {}).get("status_msg", "unknown error")
            raise RuntimeError(f"MiniMax embeddings: status {status}: {message}")
        return [list(map(float, vector)) for vector in data["vectors"]]


def embeddings_from_env() -> MiniMaxEmbeddings:
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY: environment variable not set")
    return MiniMaxEmbeddings(api_key)


def cosine(a: list[float], b: list[float]) -> float:
    """Plain cosine similarity; zero vectors score 0."""

    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if not norm_a or not norm_b:
        return 0.0
    return dot / (norm_a * norm_b)
