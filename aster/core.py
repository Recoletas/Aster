"""Minimal deterministic message handling for the M1 experiment."""

from aster.messages import IncomingMessage, Reply


def handle_message(message: IncomingMessage) -> Reply:
    """Return a deterministic reply without depending on a channel adapter."""

    return Reply(
        conversation=message.conversation,
        in_reply_to_external_message_id=message.external_message_id,
        text=f"echo: {message.text}",
    )
