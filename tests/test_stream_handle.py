import unittest

from aster.agent import SessionStore
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


def gen_strategy(chunks):
    def reply_text_stream(history):
        yield from chunks

    return reply_text_stream


class StreamHandleTest(unittest.TestCase):
    def test_iterator_strategy_yields_and_records(self) -> None:
        store = SessionStore(reply_text=gen_strategy(["你", "好"]))

        deltas = list(store.stream_handle(message("hi", "m1")))

        self.assertEqual(deltas, ["你", "好"])
        self.assertEqual(
            store.session_for(message("hi", "m1").conversation).history,
            [("user", "hi"), ("assistant", "你好")],
        )

    def test_string_strategy_streams_as_one_delta(self) -> None:
        store = SessionStore(reply_text=lambda history: "整段回复")

        self.assertEqual(list(store.stream_handle(message("hi", "m1"))), ["整段回复"])

    def test_duplicate_message_yields_recorded_text_once(self) -> None:
        calls = []

        def counting(history):
            calls.append(history)
            yield "唯一回复"

        store = SessionStore(reply_text=counting)
        list(store.stream_handle(message("hi", "m1")))
        deltas = list(store.stream_handle(message("hi", "m1")))

        self.assertEqual(deltas, ["唯一回复"])
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
