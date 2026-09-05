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
        """Reply to one validated message and return the canonical Reply.

        The full-text view of stream_handle, with the same guarantees: the
        strategy sees the history candidate, the session only updates on
        success, and a repeated external message id replays its recorded
        turn without calling the strategy again.
        """

        text = "".join(self.stream_handle(message))
        return self._reply(message, text)

    @staticmethod
    def _reply(message: IncomingMessage, text: str) -> Reply:
        return Reply(
            conversation=message.conversation,
            in_reply_to_external_message_id=message.external_message_id,
            text=text,
        )

    def stream_handle(self, message: IncomingMessage):
        """Yield reply deltas, then record the completed exchange.

        The single message flow of the store: works with strategies that
        return either a full string or an iterator of deltas. A repeated
        external message id yields the recorded text once and never
        re-calls the strategy.
        """

        session = self.session_for(message.conversation)
        recorded_turn = session.turn_by_message_id.get(message.external_message_id)
        if recorded_turn is not None:
            yield self._reply(message, session.history[2 * recorded_turn - 1][1]).text
            return

        candidate = session.history + [("user", message.text)]
        out = self._reply_text(candidate)
        if isinstance(out, str):
            chunks = [out]
            yield out
        else:
            chunks = []
            for delta in out:
                chunks.append(delta)
                yield delta

        text = "".join(chunks)
        session.history = candidate + [("assistant", text)]
        turn = sum(1 for role, _ in session.history if role == "user")
        session.turn_by_message_id[message.external_message_id] = turn
