import json
import unittest
from unittest.mock import patch

from aster.console import incoming_from_console, process_line, reply_to_console
from aster.core import handle_message
from aster.messages import ConversationRef, IncomingMessage, Reply


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

    def test_invalid_console_payload_does_not_enter_core(self) -> None:
        invalid_cases = (
            ({"event": "msg-42", "user": "alice", "body": "hello"}, "room"),
            ({**VALID_PAYLOAD, "event": 42}, "event"),
            ({**VALID_PAYLOAD, "body": "   "}, "body"),
        )

        with patch("aster.console.handle_message") as core_handler:
            for payload, field in invalid_cases:
                with self.subTest(field=field):
                    with self.assertRaisesRegex(ValueError, field):
                        process_line(json.dumps(payload))

        core_handler.assert_not_called()

    def test_core_returns_deterministic_reply(self) -> None:
        message = incoming_from_console(VALID_PAYLOAD)

        self.assertEqual(
            handle_message(message),
            Reply(
                conversation=message.conversation,
                in_reply_to_external_message_id="msg-42",
                text="echo: hello",
            ),
        )

    def test_reply_becomes_console_output(self) -> None:
        reply = handle_message(incoming_from_console(VALID_PAYLOAD))

        self.assertEqual(
            reply_to_console(reply),
            {"room": "room-7", "reply_to": "msg-42", "body": "echo: hello"},
        )

    def test_complete_console_flow(self) -> None:
        output = process_line(json.dumps(VALID_PAYLOAD))

        self.assertEqual(
            json.loads(output),
            {"room": "room-7", "reply_to": "msg-42", "body": "echo: hello"},
        )


if __name__ == "__main__":
    unittest.main()
