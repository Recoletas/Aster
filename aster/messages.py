"""Channel-independent message values used by Aster Core."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConversationRef:
    """Identify a replyable conversation within a channel instance."""

    channel_id: str
    external_conversation_id: str


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """A validated inbound text message in Aster's canonical form."""

    conversation: ConversationRef
    external_message_id: str
    external_sender_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Reply:
    """A text response associated with the external message that triggered it."""

    conversation: ConversationRef
    in_reply_to_external_message_id: str
    text: str
