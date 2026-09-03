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
MAX_TOOL_ROUNDS = 4
SYSTEM_PROMPT = (
    "你是 Aster 的客服助手。用简体中文简洁、准确地回答用户问题。"
    "创建、查询或修改任何工单等数据时，必须调用相应工具获取真实结果；"
    "即使你认为自己已从对话中知道答案，查询类问题也必须调用工具确认；"
    "严禁编造工单号、查询结果或工具输出。"
)


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


def chat_reply(history: list[tuple[str, str]], client=None) -> str:
    """Return the assistant text for the alternating conversation history.

    Plain model call without tools (M4 behavior). ``client`` is a test
    seam; production calls build one from the environment.
    """

    return _chat(history, None, client)


def make_chat_reply(registry, client=None):
    """Build a reply strategy that lets the model call registry tools."""

    def reply_text(history: list[tuple[str, str]]) -> str:
        return _chat(history, registry, client)

    return reply_text


def echo_content(blocks: list) -> list:
    """Assistant content as JSON-able dicts.

    MiniMax requires thinking and tool_use blocks echoed back verbatim;
    SDK models become dicts, plain objects pass through (tests).
    """

    return [block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else block for block in blocks]


def _chat(history: list[tuple[str, str]], registry, client) -> str:
    active_client = client or build_client()
    messages = to_api_messages(history)
    specs = registry.specs() if registry else None

    for _ in range(MAX_TOOL_ROUNDS + 1):
        response = active_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
            **({"tools": specs} if specs else {}),
        )

        if specs and response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": echo_content(response.content)})
            for block in response.content:
                if block.type == "tool_use":
                    result = registry.execute(block.name, dict(block.input))
                    messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result,
                                },
                            ],
                        }
                    )
            continue

        return extract_text(response)

    raise RuntimeError(f"tool calling: no final reply within {MAX_TOOL_ROUNDS} rounds")
