"""Conversation application layer.

Owns per-conversation state and produces replies from it. The reply text
comes from a strategy callable (default: the deterministic echo); the
layer is channel- and provider-independent.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from aster.core import echo_reply
from aster.messages import ConversationRef, IncomingMessage, Reply

History = list[tuple[str, str]]


@dataclass
class ConversationSession:
    """Alternating (role, text) history and delivery bookkeeping."""

    history: History = field(default_factory=list)
    turn_by_message_id: dict[str, int] = field(default_factory=dict)


class SessionStore:
    """All in-memory conversation sessions of one running process."""

    def __init__(self, reply_text: Callable[[History], str] = echo_reply) -> None:
        self._reply_text = reply_text
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

        The strategy sees the history candidate but the session is only
        updated on success, so a failed call leaves nothing half-written.
        A repeated external message id is answered from the assistant text
        already recorded for its turn, without calling the strategy again.
        """

        session = self.session_for(message.conversation)
        recorded_turn = session.turn_by_message_id.get(message.external_message_id)
        if recorded_turn is not None:
            return self._reply(message, session.history[2 * recorded_turn - 1][1])

        candidate = session.history + [("user", message.text)]
        assistant_text = self._reply_text(candidate)
        session.history = candidate + [("assistant", assistant_text)]
        turn = sum(1 for role, _ in session.history if role == "user")
        session.turn_by_message_id[message.external_message_id] = turn
        return self._reply(message, assistant_text)

    @staticmethod
    def _reply(message: IncomingMessage, text: str) -> Reply:
        return Reply(
            conversation=message.conversation,
            in_reply_to_external_message_id=message.external_message_id,
            text=text,
        )
