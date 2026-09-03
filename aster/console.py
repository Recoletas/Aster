"""Fake console channel for exercising the conversation boundary."""

import argparse
import json
import os
import sys

from aster.agent import SessionStore
from aster.core import echo_reply
from aster.messages import ConversationRef, IncomingMessage, Reply
from aster.storage import load_store, save_store


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


def process_line(line: str, store: SessionStore) -> str:
    """Run one Console JSON line through the complete conversation flow."""

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as error:
        raise ValueError(f"payload: invalid JSON ({error.msg})") from error

    message = incoming_from_console(payload)
    reply = store.handle(message)
    output = reply_to_console(reply)
    return json.dumps(output, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fake console channel for Aster.")
    parser.add_argument(
        "--store",
        help="JSON file used to persist conversation sessions across runs",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="reply with MiniMax (requires MINIMAX_API_KEY) instead of the offline echo",
    )
    args = parser.parse_args()

    reply_text = echo_reply
    if args.llm:
        from aster.provider import chat_reply  # imported here so offline runs need no SDK

        reply_text = chat_reply

    if args.store and os.path.exists(args.store):
        store = load_store(args.store, reply_text=reply_text)
    else:
        store = SessionStore(reply_text=reply_text)

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


if __name__ == "__main__":
    main()
