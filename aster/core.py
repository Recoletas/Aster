"""Minimal deterministic message handling for the M1 experiment."""

from aster.messages import IncomingMessage, Reply


def handle_message(message: IncomingMessage, turn: int = 1) -> Reply:
    """Return a deterministic reply without depending on a channel adapter.

    ``turn`` is the 1-based position of this message within its conversation;
    it is the only conversation state the strategy may read.
    """

    return Reply(
        conversation=message.conversation,
        in_reply_to_external_message_id=message.external_message_id,
        text=f"echo #{turn}: {message.text}",
    )
