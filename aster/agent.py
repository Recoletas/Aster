"""Conversation application layer for the M2 experiment.

Owns per-conversation in-memory state and produces replies from it. The
layer is channel-independent: it only knows the canonical message contract.
"""

from dataclasses import dataclass, field

from aster.core import handle_message
from aster.messages import ConversationRef, IncomingMessage, Reply


@dataclass
class ConversationSession:
    """Texts one conversation has sent, in arrival order."""

    user_texts: list[str] = field(default_factory=list)


class SessionStore:
    """All in-memory conversation sessions of one running process."""

    def __init__(self) -> None:
        self._sessions: dict[ConversationRef, ConversationSession] = {}

    def session_for(self, conversation: ConversationRef) -> ConversationSession:
        if conversation not in self._sessions:
            self._sessions[conversation] = ConversationSession()
        return self._sessions[conversation]

    def handle(self, message: IncomingMessage) -> Reply:
        """Record an inbound message and reply using conversation state."""

        session = self.session_for(message.conversation)
        session.user_texts.append(message.text)
        return handle_message(message, turn=len(session.user_texts))
