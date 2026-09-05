import json
import unittest

from aster.agent import SessionStore
from aster.console import incoming_from_console, process_line, reply_to_console
from aster.core import echo_reply
from aster.messages import ConversationRef, IncomingMessage

VALID_PAYLOAD = {
    "room": "room-7",
    "event": "msg-42",
    "user": "alice",
    "body": "hello",
}


class MessageFlowTest(unittest.TestCase):
    def test_valid_console_payload_becomes_incoming_message(self) -> None:
        message = incoming_from_console(VALID_PAYLOAD)

        self.assertEqual(
            message,
            IncomingMessage(
                conversation=ConversationRef(
                    channel_id="console",
                    external_conversation_id="room-7",
                ),
                external_message_id="msg-42",
                external_sender_id="alice",
                text="hello",
            ),
        )

    def test_invalid_console_payload_never_reaches_the_strategy(self) -> None:
        invalid_cases = (
            ({"event": "msg-42", "user": "alice", "body": "hello"}, "room"),
            ({**VALID_PAYLOAD, "event": 42}, "event"),
            ({**VALID_PAYLOAD, "body": "   "}, "body"),
        )
        calls = []

        def recording_reply(history):
            calls.append(history)
            return "unreachable"

        store = SessionStore(reply_text=recording_reply)
        for payload, field in invalid_cases:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                process_line(json.dumps(payload), store)

        self.assertEqual(calls, [])

    def test_echo_strategy_counts_user_turns(self) -> None:
        self.assertEqual(echo_reply([("user", "hello")]), "echo #1: hello")
        self.assertEqual(
            echo_reply(
                [
                    ("user", "hello"),
                    ("assistant", "echo #1: hello"),
                    ("user", "again"),
                ]
            ),
            "echo #2: again",
        )

    def test_reply_becomes_console_output(self) -> None:
        reply = SessionStore().handle(incoming_from_console(VALID_PAYLOAD))

        self.assertEqual(
            reply_to_console(reply),
            {"room": "room-7", "reply_to": "msg-42", "body": "echo #1: hello"},
        )

    def test_complete_console_flow(self) -> None:
        output = process_line(json.dumps(VALID_PAYLOAD), SessionStore())

        self.assertEqual(
            json.loads(output),
            {"room": "room-7", "reply_to": "msg-42", "body": "echo #1: hello"},
        )


if __name__ == "__main__":
    unittest.main()
