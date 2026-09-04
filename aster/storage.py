"""SQLite persistence for conversation sessions (M9 experiment).

Standard-library sqlite3 in one file: SQLite owns atomicity and write
locking, replacing the M3 hand-rolled tmp+rename JSON format (retired;
old JSON files fail loudly when opened as databases).
"""

import json
import os
import sqlite3
from collections.abc import Callable

from aster.agent import ConversationSession, History, SessionStore
from aster.core import echo_reply
from aster.messages import ConversationRef

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    channel_id TEXT NOT NULL,
    external_conversation_id TEXT NOT NULL,
    history TEXT NOT NULL,
    turn_by_message_id TEXT NOT NULL,
    PRIMARY KEY (channel_id, external_conversation_id)
)
"""


def save_store(path: str, store: SessionStore) -> None:
    """Upsert every session row; SQLite owns atomic replacement."""

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.execute(_SCHEMA)
            for conversation, session in store.sessions().items():
                connection.execute(
                    "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?)",
                    (
                        conversation.channel_id,
                        conversation.external_conversation_id,
                        json.dumps(session.history, ensure_ascii=False),
                        json.dumps(session.turn_by_message_id, ensure_ascii=False),
                    ),
                )
    finally:
        connection.close()


def load_store(
    path: str,
    reply_text: Callable[[History], str] = echo_reply,
) -> SessionStore:
    """Rebuild a SessionStore from a database written by save_store."""

    connection = sqlite3.connect(path)
    try:
        connection.execute(_SCHEMA)
        rows = connection.execute(
            "SELECT channel_id, external_conversation_id, history, turn_by_message_id FROM sessions"
        ).fetchall()
    finally:
        connection.close()

    store = SessionStore(reply_text=reply_text)
    for channel_id, external_id, history_raw, turns_raw in rows:
        session = store.session_for(
            ConversationRef(channel_id=channel_id, external_conversation_id=external_id)
        )
        session.history = [(role, text) for role, text in json.loads(history_raw)]
        session.turn_by_message_id = dict(json.loads(turns_raw))
    return store
