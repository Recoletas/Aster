"""Fake console channel for exercising the conversation boundary."""

import argparse
import json
import os
import sys
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

from aster.agent import History, SessionStore
from aster.core import echo_reply
from aster.messages import ConversationRef, IncomingMessage, Reply
from aster.storage import load_store, save_store

if TYPE_CHECKING:
    from aster.mcp import McpStdioClient
    from aster.provider import KnowledgeLike
    from aster.tools import ToolRegistry

CHANNEL_ID = "console"


def _required_text(payload: dict[str, object], field: str) -> str:
    if field not in payload:
        raise ValueError(f"{field}: missing required field")

    value = payload[field]
    if not isinstance(value, str):
        raise ValueError(f"{field}: expected string")
    if not value.strip():
        raise ValueError(f"{field}: must not be blank")

    return value


def incoming_from_console(payload: object) -> IncomingMessage:
    """Validate and convert a Console payload at the channel boundary."""

    if not isinstance(payload, dict):
        raise ValueError("payload: expected JSON object")

    return IncomingMessage(
        conversation=ConversationRef(
            channel_id=CHANNEL_ID,
            external_conversation_id=_required_text(payload, "room"),
        ),
        external_message_id=_required_text(payload, "event"),
        external_sender_id=_required_text(payload, "user"),
        text=_required_text(payload, "body"),
    )


def reply_to_console(reply: Reply) -> dict[str, str]:
    """Convert an Aster reply to the Fake/Console channel shape."""

    if reply.conversation.channel_id != CHANNEL_ID:
        raise ValueError(f"channel_id: expected {CHANNEL_ID!r}")

    return {
        "room": reply.conversation.external_conversation_id,
        "reply_to": reply.in_reply_to_external_message_id,
        "body": reply.text,
    }


def process_payload(payload: object, store: SessionStore) -> str:
    """Validate and run one already-parsed payload through the flow."""

    message = incoming_from_console(payload)
    reply = store.handle(message)
    output = reply_to_console(reply)
    return json.dumps(output, ensure_ascii=False, separators=(",", ":"))


def process_line(line: str, store: SessionStore) -> str:
    """Run one Console JSON line through the complete conversation flow."""

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as error:
        raise ValueError(f"payload: invalid JSON ({error.msg})") from error

    return process_payload(payload, store)


class Runtime:
    """Assembled channel dependencies shared by all channel entrypoints."""

    def __init__(
        self,
        store: SessionStore,
        registry: "ToolRegistry | None",
        streaming: bool,
        mcp_clients: "list[McpStdioClient] | None" = None,
    ) -> None:
        self.store = store
        self.registry = registry
        self.streaming = streaming
        self.mcp_clients = mcp_clients or []

    def close(self) -> None:
        for client in self.mcp_clients:
            client.close()


def build_runtime(args: argparse.Namespace) -> Runtime:
    """Shared channel wiring: reply strategy, knowledge, and store assembly."""

    knowledge: KnowledgeLike | None = None
    if getattr(args, "knowledge", None):
        from aster.knowledge import KnowledgeBase

        knowledge = KnowledgeBase.load(args.knowledge)

    registry = None
    mcp_clients = []
    reply_text: Callable[[History], str | Iterator[str]] = echo_reply
    streaming = False
    if args.llm:
        try:
            # imported here so offline runs need no SDK
            from aster.provider import make_chat_reply, make_stream_reply
            from aster.tools import build_default_registry
        except ImportError as error:
            print(
                f'error: --llm requires the anthropic SDK (pip install -e ".[dev]"): {error}',
                file=sys.stderr,
            )
            raise SystemExit(2) from error

        if getattr(args, "knowledge", None) and args.kb_mode == "embedding":
            from aster.embeddings import embeddings_from_env
            from aster.knowledge import EmbeddingKnowledgeBase

            knowledge = EmbeddingKnowledgeBase.load(args.knowledge, embeddings_from_env())

        streaming = bool(getattr(args, "stream", False))
        if streaming:
            # streaming covers the plain chat path only; tools stay non-streaming
            registry = None
            reply_text = make_stream_reply(knowledge=knowledge)
        else:
            registry = build_default_registry()
            mcp_clients = _attach_mcp_servers(args, registry)
            reply_text = make_chat_reply(registry, knowledge=knowledge)

    if args.store and os.path.exists(args.store):
        store = load_store(args.store, reply_text=reply_text)
    else:
        store = SessionStore(reply_text=reply_text)

    return Runtime(store, registry, streaming, mcp_clients)


def _attach_mcp_servers(args: argparse.Namespace, registry: "ToolRegistry") -> list:
    """Start configured MCP servers and register their tools; loud on failure."""

    from aster.mcp import McpError, McpStdioClient, client_tools

    clients = []
    for command_string in getattr(args, "mcp_command", None) or []:
        try:
            client = McpStdioClient.from_command_string(command_string)
            client.start()
            for tool in client_tools(client):
                registry.add(tool)
        except (McpError, RuntimeError, OSError, TimeoutError) as error:
            raise SystemExit(f"error: MCP server {command_string!r}: {error}") from error
        clients.append(client)
    return clients


def print_audit(registry: "ToolRegistry") -> None:
    """Tool/reconciliation events to stderr; stdout stays the JSON protocol."""

    from aster.tools import AUDIT_LIMIT

    for entry in registry.audit:
        line = (
            f"{entry['tool']} {json.dumps(entry['arguments'], ensure_ascii=False)}"
            f" -> {entry['result']}"
        )
        print(f"tool: {line[:AUDIT_LIMIT]}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fake console channel for Aster.")
    parser.add_argument(
        "--store",
        help="SQLite database file used to persist conversation sessions across runs",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="reply with MiniMax (requires MINIMAX_API_KEY) instead of the offline echo",
    )
    parser.add_argument(
        "--knowledge",
        help="JSON knowledge base file retrieved into the LLM context (needs --llm)",
    )
    parser.add_argument(
        "--kb-mode",
        choices=("keyword", "embedding"),
        default="keyword",
        help="knowledge retrieval mode; embedding uses MiniMax embo-01 (needs MINIMAX_API_KEY)",
    )
    parser.add_argument(
        "--mcp-command",
        action="append",
        metavar="CMD",
        help="MCP stdio server to attach as a tool source, e.g. "
        '"python3 examples/kb_mcp_server.py" (repeatable, needs --llm)',
    )
    args = parser.parse_args()

    runtime = build_runtime(args)
    store = runtime.store

    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                output = process_line(line, store)
            except (ValueError, RuntimeError) as error:
                print(f"error: {error}", file=sys.stderr)
                raise SystemExit(2) from error

            print(output)
            if args.store:
                save_store(args.store, store)

        if runtime.registry is not None:
            print_audit(runtime.registry)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
