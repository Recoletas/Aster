"""JSON-file persistence for conversation sessions (M3 experiment, M4 format).

A reversible first storage choice: one JSON file, replaced atomically, no
database. Since M4 a session's history is alternating (role, text) pairs;
older files with `user_texts` fail loudly on load and need re-creation.
"""

import json
import os
from collections.abc import Callable

from aster.agent import ConversationSession, History, SessionStore
from aster.core import echo_reply
from aster.messages import ConversationRef


def save_store(path: str, store: SessionStore) -> None:
    """Write every session to one JSON file, replacing it atomically."""

    sessions = [
        {
            "channel_id": conversation.channel_id,
            "external_conversation_id": conversation.external_conversation_id,
            "history": [list(entry) for entry in session.history],
            "turn_by_message_id": session.turn_by_message_id,
        }
        for conversation, session in store.sessions().items()
    ]

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump({"sessions": sessions}, file, ensure_ascii=False)
    os.replace(temporary, path)


def load_store(
    path: str,
    reply_text: Callable[[History], str] = echo_reply,
) -> SessionStore:
    """Rebuild a SessionStore from a file written by save_store."""

    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    store = SessionStore(reply_text=reply_text)
    for item in data["sessions"]:
        session = store.session_for(
            ConversationRef(
                channel_id=item["channel_id"],
                external_conversation_id=item["external_conversation_id"],
            )
        )
        session.history = [(role, text) for role, text in item["history"]]
        session.turn_by_message_id = dict(item["turn_by_message_id"])
    return store
