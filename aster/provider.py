"""MiniMax LLM provider behind the Anthropic-compatible Messages API.

This is the only module that knows the SDK and the provider endpoint;
core and agent stay provider-independent. Auth comes from the
MINIMAX_API_KEY environment variable and is never read from files here.
"""

import os
from collections.abc import Callable

from anthropic import Anthropic

# The Python SDK appends /v1/messages itself, so the base URL must not
# include /v1 (openmaic's JS AI SDK config uses the /anthropic/v1 form).
BASE_URL = "https://api.minimaxi.com/anthropic"
MODEL = "MiniMax-M3"
MAX_TOKENS = 1024
SYSTEM_PROMPT = "你是 Aster 的客服助手。用简体中文简洁、准确地回答用户问题。"


def to_api_messages(history: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Map Aster's alternating (role, text) history to Messages API shape."""

    return [{"role": role, "content": text} for role, text in history]


def extract_text(response: object) -> str:
    """Concatenate the text blocks of a Messages API response."""

    return "".join(block.text for block in response.content if block.type == "text")


def build_client() -> Anthropic:
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY: environment variable not set")

    return Anthropic(api_key=api_key, base_url=BASE_URL, timeout=60.0, max_retries=2)


def chat_reply(
    history: list[tuple[str, str]],
    client: Anthropic | Callable[[], object] | None = None,
) -> str:
    """Return the assistant text for the alternating conversation history.

    ``client`` is a test seam; production calls build one from the
    environment and keep the key out of the repository.
    """

    response = (client or build_client()).messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=to_api_messages(history),
    )
    return extract_text(response)
