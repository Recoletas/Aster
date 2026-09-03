"""JSON-file persistence for conversation sessions (M3 experiment).

A reversible first storage choice: one JSON file, replaced atomically, no
database. Load/save validate nothing beyond what JSON itself guarantees, so
a corrupt file fails loudly instead of silently degrading.
"""

import json
import os

from aster.agent import ConversationSession, SessionStore
from aster.messages import ConversationRef


def save_store(path: str, store: SessionStore) -> None:
    """Write every session to one JSON file, replacing it atomically."""

    sessions = [
        {
            "channel_id": conversation.channel_id,
            "external_conversation_id": conversation.external_conversation_id,
            "user_texts": session.user_texts,
            "turn_by_message_id": session.turn_by_message_id,
        }
        for conversation, session in store.sessions().items()
    ]

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temporary = f"{path}.tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump({"sessions": sessions}, file, ensure_ascii=False)
    os.replace(temporary, path)


def load_store(path: str) -> SessionStore:
    """Rebuild a SessionStore from a file written by save_store."""

    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    store = SessionStore()
    for item in data["sessions"]:
        session = store.session_for(
            ConversationRef(
                channel_id=item["channel_id"],
                external_conversation_id=item["external_conversation_id"],
            )
        )
        session.user_texts = list(item["user_texts"])
        session.turn_by_message_id = dict(item["turn_by_message_id"])
    return store
