import unittest
from types import SimpleNamespace

from aster.provider import chat_reply, extract_text, to_api_messages


class FakeMessages:
    def __init__(self, client):
        self._client = client

    def create(self, **kwargs):
        self._client.kwargs = kwargs
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="好的"),
                SimpleNamespace(type="thinking", text="hidden reasoning"),
                SimpleNamespace(type="text", text="，已记录。"),
            ]
        )


class FakeClient:
    def __init__(self):
        self.kwargs = None
        self.messages = FakeMessages(self)


class ProviderBoundaryTest(unittest.TestCase):
    def test_history_maps_to_api_messages(self) -> None:
        self.assertEqual(
            to_api_messages([("user", "hi"), ("assistant", "hello")]),
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )

    def test_extract_text_joins_only_text_blocks(self) -> None:
        response = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="A"),
                SimpleNamespace(type="thinking", text="B"),
                SimpleNamespace(type="text", text="C"),
            ]
        )

        self.assertEqual(extract_text(response), "AC")

    def test_chat_reply_sends_expected_request(self) -> None:
        client = FakeClient()

        reply = chat_reply([("user", "你好")], client=client)

        self.assertEqual(reply, "好的，已记录。")
        self.assertEqual(client.kwargs["model"], "MiniMax-M3")
        self.assertEqual(client.kwargs["max_tokens"], 1024)
        self.assertTrue(client.kwargs["system"])
        self.assertEqual(
            client.kwargs["messages"],
            [{"role": "user", "content": "你好"}],
        )


if __name__ == "__main__":
    unittest.main()
