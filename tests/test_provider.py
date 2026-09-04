import unittest
from types import SimpleNamespace

try:
    from aster.provider import chat_reply, echo_content, extract_text, make_chat_reply, to_api_messages
except ImportError:  # anthropic SDK not installed; offline-only environments skip these
    raise unittest.SkipTest("anthropic SDK not installed (use .venv for provider tests)")


def fake_response(text):
    return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)])


def tool_use_response():
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[
            SimpleNamespace(type="thinking", text="需要建工单", signature="sig"),
            SimpleNamespace(type="tool_use", id="tu_1", name="create_ticket", input={"subject": "打印机", "priority": "high"}),
        ],
    )


class FakeMessages:
    def __init__(self, client):
        self._client = client

    def create(self, **kwargs):
        self._client.requests.append(kwargs)
        return self._client.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = FakeMessages(self)


class FakeRegistry:
    def __init__(self):
        self.calls = []
        self.audit = []
        self.problems = []

    def specs(self):
        return [{"name": "create_ticket", "description": "d", "input_schema": {"type": "object"}}]

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        self.audit.append({"tool": name, "arguments": arguments, "result": "created ticket 1", "ok": True})
        return "created ticket 1"

    def reconcile(self, reply, since=0):
        return self.problems

    def note(self, tool, arguments, result):
        self.audit.append({"tool": tool, "arguments": arguments, "result": result, "ok": True})


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

    def test_chat_reply_sends_expected_request_and_extracts_text(self) -> None:
        response = SimpleNamespace(
            stop_reason="end_turn",
            content=[
                SimpleNamespace(type="text", text="好的"),
                SimpleNamespace(type="thinking", text="hidden reasoning"),
                SimpleNamespace(type="text", text="，已记录。"),
            ],
        )
        client = FakeClient([response])

        reply = chat_reply([("user", "你好")], client=client)

        self.assertEqual(reply, "好的，已记录。")
        request = client.requests[0]
        self.assertEqual(request["model"], "MiniMax-M3")
        self.assertEqual(request["max_tokens"], 1024)
        self.assertTrue(request["system"])
        self.assertEqual(request["messages"], [{"role": "user", "content": "你好"}])
        self.assertNotIn("tools", request)


class ToolLoopTest(unittest.TestCase):
    def test_tool_round_completes_with_result_fed_back(self) -> None:
        registry = FakeRegistry()
        client = FakeClient([tool_use_response(), fake_response("已创建工单 1")])

        reply = make_chat_reply(registry, client=client)([("user", "帮我建个工单")])

        self.assertEqual(reply, "已创建工单 1")
        self.assertEqual(
            registry.calls,
            [("create_ticket", {"subject": "打印机", "priority": "high"})],
        )
        messages = client.requests[1]["messages"]
        assistant_echo, tool_result = messages[-2], messages[-1]
        self.assertEqual(assistant_echo["role"], "assistant")
        self.assertEqual(assistant_echo["content"][0].text, "需要建工单")
        self.assertEqual(assistant_echo["content"][1].type, "tool_use")
        self.assertEqual(tool_result["content"][0]["tool_use_id"], "tu_1")
        self.assertEqual(tool_result["content"][0]["content"], "created ticket 1")

    def test_tool_loop_bounds_rounds(self) -> None:
        client = FakeClient([tool_use_response() for _ in range(6)])

        with self.assertRaisesRegex(RuntimeError, "rounds"):
            make_chat_reply(FakeRegistry(), client=client)([("user", "hi")])

    def test_reconciliation_triggers_one_corrective_round(self) -> None:
        registry = FakeRegistry()
        registry.problems = ["create_ticket: 2"]
        client = FakeClient([fake_response("已创建工单号 2"), fake_response("该操作没有完成")])

        reply = make_chat_reply(registry, client=client)([("user", "hi")])

        self.assertEqual(reply, "该操作没有完成")
        corrective = client.requests[1]["messages"][-1]
        self.assertEqual(corrective["role"], "user")
        self.assertIn("create_ticket: 2", corrective["content"][0]["text"])
        self.assertTrue(any(entry["tool"] == "__reconcile__" for entry in registry.audit))

    def test_clean_reply_needs_no_correction(self) -> None:
        client = FakeClient([fake_response("好的")])

        reply = make_chat_reply(FakeRegistry(), client=client)([("user", "hi")])

        self.assertEqual(reply, "好的")
        self.assertEqual(len(client.requests), 1)

    def test_echo_content_dumps_models_and_passes_plain_objects(self) -> None:
        class Model:
            def model_dump(self, exclude_none=True):
                return {"type": "text", "text": "hi"}

        self.assertEqual(
            echo_content([Model(), {"type": "text", "text": "raw"}]),
            [{"type": "text", "text": "hi"}, {"type": "text", "text": "raw"}],
        )


if __name__ == "__main__":
    unittest.main()
