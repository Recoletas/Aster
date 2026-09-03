"""Fake console channel for exercising the M1 message boundary."""

import json
import sys

from aster.core import handle_message
from aster.messages import ConversationRef, IncomingMessage, Reply


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


def process_line(line: str) -> str:
    """Run one Console JSON line through the complete M1 flow."""

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as error:
        raise ValueError(f"payload: invalid JSON ({error.msg})") from error

    message = incoming_from_console(payload)
    reply = handle_message(message)
    output = reply_to_console(reply)
    return json.dumps(output, ensure_ascii=False, separators=(",", ":"))


def main() -> None:
    line = sys.stdin.readline()
    if not line:
        print("error: input: expected one JSON line", file=sys.stderr)
        raise SystemExit(2)

    try:
        output = process_line(line)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    print(output)


if __name__ == "__main__":
    main()
