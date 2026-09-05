import json
import threading
import unittest
import urllib.error
import urllib.request
from types import SimpleNamespace

from aster import web_channel


class WebChannelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        args = SimpleNamespace(
            port=0, store=None, llm=False, knowledge=None, kb_mode="keyword", mcp_command=None
        )
        cls.server, cls.runtime = web_channel.make_server(args)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.runtime.close()

    def request(self, path: str, raw: bytes | None = None):
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=raw,
            method="POST" if raw is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def payload(self, room: str, event: str, body: str) -> bytes:
        message = {"room": room, "event": event, "user": "webuser", "body": body}
        return json.dumps(message, ensure_ascii=False).encode("utf-8")

    def test_index_serves_chat_page(self) -> None:
        status, raw = self.request("/")

        self.assertEqual(status, 200)
        self.assertIn("Aster 本地客服".encode(), raw)

    def test_valid_message_gets_reply(self) -> None:
        status, raw = self.request("/api/message", self.payload("room-a", "m1", "你好"))

        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)["body"], "echo #1: 你好")
        self.assertEqual(json.loads(raw)["room"], "room-a")

    def test_turns_advance_across_requests(self) -> None:
        self.request("/api/message", self.payload("room-b", "mb1", "第一条"))
        status, raw = self.request("/api/message", self.payload("room-b", "mb2", "第二条"))

        self.assertEqual(json.loads(raw)["body"], "echo #2: 第二条")

    def test_duplicate_event_is_idempotent(self) -> None:
        first = self.request("/api/message", self.payload("room-c", "dup", "重复投递"))
        second = self.request("/api/message", self.payload("room-c", "dup", "重复投递"))

        self.assertEqual(first[1], second[1])
        self.assertEqual(json.loads(second[1])["body"], "echo #1: 重复投递")

    def test_missing_field_is_400_with_field_name(self) -> None:
        status, raw = self.request("/api/message", json.dumps({"room": "r"}).encode())

        self.assertEqual(status, 400)
        self.assertIn("event", json.loads(raw)["error"])

    def test_invalid_json_is_400(self) -> None:
        status, raw = self.request("/api/message", b"{bad json")

        self.assertEqual(status, 400)
        self.assertIn("invalid JSON", json.loads(raw)["error"])

    def test_stream_endpoint_disabled_without_flag(self) -> None:
        status, raw = self.request("/api/stream", self.payload("room-d", "m1", "hi"))

        self.assertEqual(status, 400)
        self.assertIn("streaming", json.loads(raw)["error"])

    def test_unknown_path_is_404(self) -> None:
        status, _ = self.request("/api/nope", b"{}")

        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
