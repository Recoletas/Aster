import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from aster.agent import SessionStore
from aster.messages import ConversationRef, IncomingMessage
from aster.storage import load_store, save_store


def message(text: str, event: str, room: str = "room-7") -> IncomingMessage:
    return IncomingMessage(
        conversation=ConversationRef(
            channel_id="console",
            external_conversation_id=room,
        ),
        external_message_id=event,
        external_sender_id="alice",
        text=text,
    )


class PersistenceTest(unittest.TestCase):
    def test_roundtrip_preserves_sessions(self) -> None:
        store = SessionStore()
        store.handle(message("hello", "msg-1"))
        store.handle(message("again", "msg-2"))
        store.handle(message("other room", "msg-3", room="room-8"))

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "sessions.db")
            save_store(path, store)
            restored = load_store(path)

        self.assertEqual(restored.handle(message("next", "msg-4")).text, "echo #3: next")
        self.assertEqual(
            restored.handle(message("next room", "msg-5", room="room-8")).text,
            "echo #2: next room",
        )

    def test_duplicate_message_id_reuses_recorded_reply(self) -> None:
        calls = []

        def counting_reply(history):
            calls.append(history)
            return f"reply {len(calls)}"

        store = SessionStore(reply_text=counting_reply)

        first = store.handle(message("hello", "msg-1"))
        duplicate = store.handle(message("hello", "msg-1"))
        following = store.handle(message("again", "msg-2"))

        self.assertEqual(first.text, "reply 1")
        self.assertEqual(duplicate.text, first.text)
        self.assertEqual(following.text, "reply 2")
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            store.session_for(first.conversation).history,
            [
                ("user", "hello"),
                ("assistant", "reply 1"),
                ("user", "again"),
                ("assistant", "reply 2"),
            ],
        )

    def test_roundtrip_preserves_reply_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "sessions.db")
            store = SessionStore(reply_text=lambda history: "custom reply")
            store.handle(message("hello", "msg-1"))
            save_store(path, store)

            restored = load_store(path, reply_text=lambda history: "custom reply")
            following = restored.handle(message("again", "msg-2"))

        self.assertEqual(following.text, "custom reply")

    def test_retired_json_format_fails_loudly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "legacy.json")
            with open(path, "w", encoding="utf-8") as file:
                file.write('{"sessions": []}')

            with self.assertRaises(sqlite3.DatabaseError):
                load_store(path)

    def test_console_restarts_continue_turn_numbering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "sessions.db")
            first_run = subprocess.run(
                [sys.executable, "-B", "-m", "aster.console", "--store", path],
                input=(
                    '{"room":"room-7","event":"msg-1","user":"alice","body":"hello"}\n'
                    '{"room":"room-7","event":"msg-2","user":"alice","body":"again"}\n'
                ),
                capture_output=True,
                text=True,
                check=True,
            )
            second_run = subprocess.run(
                [sys.executable, "-B", "-m", "aster.console", "--store", path],
                input='{"room":"room-7","event":"msg-3","user":"alice","body":"back"}\n',
                capture_output=True,
                text=True,
                check=True,
            )

        first_lines = first_run.stdout.strip().splitlines()
        self.assertEqual(json.loads(first_lines[-1])["body"], "echo #2: again")
        self.assertEqual(json.loads(second_run.stdout)["body"], "echo #3: back")


if __name__ == "__main__":
    unittest.main()
