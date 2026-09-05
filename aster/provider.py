"""MiniMax LLM provider behind the Anthropic-compatible Messages API.

This is the only module that knows the SDK and the provider endpoint;
core and agent stay provider-independent. Auth comes from the
MINIMAX_API_KEY environment variable and is never read from files here.
"""

import os
from collections.abc import Callable, Iterator, Sequence
from typing import Any, Protocol, cast

from anthropic import Anthropic
from anthropic.types import MessageParam

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

History = list[tuple[str, str]]


class RegistryLike(Protocol):
    """What the tool loop needs from a tool registry."""

    audit: list[dict[str, Any]]

    def specs(self) -> list[dict[str, Any]]: ...

    def execute(self, name: str, arguments: dict[str, Any]) -> str: ...

    def reconcile(self, reply: str, since: int = 0) -> list[str]: ...

    def note(self, tool: str, arguments: dict[str, Any], result: str) -> None: ...


class KnowledgeLike(Protocol):
    """What the strategies need from a knowledge base."""

    def search(self, query: str) -> list[dict[str, Any]]: ...

    def as_context(self, hits: list[dict[str, Any]]) -> str: ...


class _BlockLike(Protocol):
    type: str


class _TextBlockLike(_BlockLike):
    text: str


class _ToolUseBlockLike(_BlockLike):
    id: str
    name: str
    input: dict[str, Any]


class _ResponseLike(Protocol):
    content: Sequence[_BlockLike]


def to_api_messages(history: History) -> list[MessageParam]:
    """Map Aster's alternating (role, text) history to Messages API shape."""

    return cast(
        "list[MessageParam]",
        [{"role": role, "content": text} for role, text in history],
    )


def extract_text(response: _ResponseLike) -> str:
    """Concatenate the text blocks of a Messages API response."""

    return "".join(
        cast("_TextBlockLike", block).text for block in response.content if block.type == "text"
    )


def build_client() -> Anthropic:
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        raise RuntimeError("MINIMAX_API_KEY: environment variable not set")

    return Anthropic(api_key=api_key, base_url=BASE_URL, timeout=60.0, max_retries=2)


def make_chat_reply(
    registry: RegistryLike | None = None,
    client: Anthropic | None = None,
    knowledge: KnowledgeLike | None = None,
) -> Callable[[History], str]:
    """Build a reply strategy that may use registry tools and KB context."""

    def reply_text(history: History) -> str:
        return _chat(history, registry, client, context=_retrieved_context(knowledge, history))

    return reply_text


def make_stream_reply(
    client: Anthropic | None = None,
    knowledge: KnowledgeLike | None = None,
) -> Callable[[History], Iterator[str]]:
    """Streaming strategy: yields text deltas (plain chat, no tools).

    Tool rounds interleave with non-text blocks, so streaming is limited
    to the plain chat path by design.
    """

    def reply_text_stream(history: History) -> Iterator[str]:
        active_client = client or build_client()
        with active_client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=_system_prompt(_retrieved_context(knowledge, history)),
            messages=to_api_messages(history),
        ) as stream:
            yield from stream.text_stream

    return reply_text_stream


def _retrieved_context(knowledge: KnowledgeLike | None, history: History) -> str:
    """KB hits for the latest user message, or empty string."""

    if knowledge is None or not history:
        return ""
    return knowledge.as_context(knowledge.search(history[-1][1]))


def _system_prompt(context: str) -> str:
    if not context:
        return SYSTEM_PROMPT
    return (
        SYSTEM_PROMPT
        + "\n\n【知识库参考】回答时如相关请优先引用；以下是全部可用内容，不要编造未提供的部分：\n"
        + context
    )


def echo_content(blocks: list[Any]) -> list[Any]:
    """Assistant content as JSON-able dicts.

    MiniMax requires thinking and tool_use blocks echoed back verbatim;
    SDK models become dicts, plain objects pass through (tests).
    """

    return [
        block.model_dump(exclude_none=True) if hasattr(block, "model_dump") else block
        for block in blocks
    ]


def _chat(
    history: History,
    registry: RegistryLike | None,
    client: Anthropic | None,
    context: str = "",
) -> str:
    """Run the model/tool loop for one strategy call and return the final text.

    Per round: send the conversation, then either apply a tool round, ask
    for one reconciliation correction, or accept the reply.
    """

    active_client = client or build_client()
    messages = to_api_messages(history)
    specs = registry.specs() if registry else None
    system = _system_prompt(context)
    audit_start = len(registry.audit) if registry else 0
    corrected = False

    for _ in range(MAX_TOOL_ROUNDS + 1):
        # the SDK's overloads are strict, so dynamic kwargs go through Any
        kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "system": system,
            "messages": messages,
        }
        if specs:
            kwargs["tools"] = specs

        response = active_client.messages.create(**kwargs)

        if registry is not None and specs and response.stop_reason == "tool_use":
            _apply_tool_round(messages, response, registry)
            continue

        text = extract_text(response)
        if _reconciliation(registry, messages, text, audit_start, corrected):
            corrected = True
            continue

        return text

    raise RuntimeError(f"tool calling: no final reply within {MAX_TOOL_ROUNDS} rounds")


def _apply_tool_round(
    messages: list[MessageParam], response: _ResponseLike, registry: RegistryLike
) -> None:
    """Echo the full assistant content back (MiniMax requires thinking
    blocks verbatim) and answer every tool_use with a tool_result."""

    messages.append({"role": "assistant", "content": echo_content(list(response.content))})
    for block in response.content:
        if block.type != "tool_use":
            continue
        tool_use = cast("_ToolUseBlockLike", block)
        result = registry.execute(tool_use.name, dict(tool_use.input))
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": result,
                    },
                ],
            }
        )


def _reconciliation(
    registry: RegistryLike | None,
    messages: list[MessageParam],
    text: str,
    audit_start: int,
    corrected: bool,
) -> bool:
    """Detect claims without matching executions; append one correction.

    Returns True when a correction was requested and the loop should run
    another round; at most one correction happens per strategy call.
    """

    if registry is None or corrected:
        return False

    problems = registry.reconcile(text, since=audit_start)
    if not problems:
        return False

    registry.note("__reconcile__", {"problems": problems}, "correction requested")
    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "系统对账发现你的回复引用了没有对应工具调用的结果："
                        + "；".join(problems)
                        + "。请先调用工具核实；若无对应记录，明确告知用户该操作没有完成，不要虚构。"
                    ),
                },
            ],
        }
    )
    return True
