import json
import unittest

from aster.agent import SessionStore
from aster.console import process_line
from aster.messages import ConversationRef, IncomingMessage


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


class ConversationFlowTest(unittest.TestCase):
    def test_turn_advances_within_one_conversation(self) -> None:
        store = SessionStore()

        first = store.handle(message("hello", "msg-1"))
        second = store.handle(message("again", "msg-2"))

        self.assertEqual(first.text, "echo #1: hello")
        self.assertEqual(second.text, "echo #2: again")
        self.assertEqual(
            store.session_for(first.conversation).user_texts,
            ["hello", "again"],
        )

    def test_conversations_do_not_share_state(self) -> None:
        store = SessionStore()

        room_a = store.handle(message("hi", "msg-1", room="room-a"))
        room_b = store.handle(message("hi", "msg-2", room="room-b"))

        self.assertEqual(room_a.text, "echo #1: hi")
        self.assertEqual(room_b.text, "echo #1: hi")
        self.assertNotEqual(room_a.conversation, room_b.conversation)

    def test_console_lines_share_one_session_store(self) -> None:
        store = SessionStore()

        first = process_line(
            '{"room":"room-7","event":"msg-1","user":"alice","body":"hello"}',
            store,
        )
        second = process_line(
            '{"room":"room-7","event":"msg-2","user":"alice","body":"again"}',
            store,
        )

        self.assertEqual(json.loads(first)["body"], "echo #1: hello")
        self.assertEqual(json.loads(second)["body"], "echo #2: again")


if __name__ == "__main__":
    unittest.main()
