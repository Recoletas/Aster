"""Conversation application layer for the M2 experiment.

Owns per-conversation in-memory state and produces replies from it. The
layer is channel-independent: it only knows the canonical message contract.
"""

from dataclasses import dataclass, field

from aster.core import handle_message
from aster.messages import ConversationRef, IncomingMessage, Reply


@dataclass
class ConversationSession:
    """State one conversation has accumulated, in arrival order."""

    user_texts: list[str] = field(default_factory=list)
    turn_by_message_id: dict[str, int] = field(default_factory=dict)


class SessionStore:
    """All in-memory conversation sessions of one running process."""

    def __init__(self) -> None:
        self._sessions: dict[ConversationRef, ConversationSession] = {}

    def session_for(self, conversation: ConversationRef) -> ConversationSession:
        if conversation not in self._sessions:
            self._sessions[conversation] = ConversationSession()
        return self._sessions[conversation]

    def sessions(self) -> dict[ConversationRef, ConversationSession]:
        """Snapshot of the sessions currently held in memory."""

        return dict(self._sessions)

    def handle(self, message: IncomingMessage) -> Reply:
        """Record an inbound message and reply using conversation state.

        A repeated external message id is answered from its recorded turn
        without changing the session again.
        """

        session = self.session_for(message.conversation)
        recorded_turn = session.turn_by_message_id.get(message.external_message_id)
        if recorded_turn is not None:
            return handle_message(message, turn=recorded_turn)

        session.user_texts.append(message.text)
        turn = len(session.user_texts)
        session.turn_by_message_id[message.external_message_id] = turn
        return handle_message(message, turn=turn)
