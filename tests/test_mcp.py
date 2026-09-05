import json
import os
import sys
import unittest
from queue import Queue

from aster.mcp import McpError, McpStdioClient, client_tools
from aster.tools import ToolRegistry, build_default_registry


def memory_transport(responses: list[str], sent: list[str]) -> tuple:
    """An in-process transport: server replies are popped in order."""

    queue: Queue[str] = Queue()
    for line in responses:
        queue.put(line)

    def write_line(line: str) -> None:
        sent.append(line)

    def read_line() -> str:
        item = queue.get()
        if isinstance(item, Exception):
            raise item
        return item

    return write_line, read_line, lambda: None


INITIALIZE_RESULT = json.dumps(
    {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "protocolVersion": "2025-06-18",
            "serverInfo": {"name": "fake-kb", "version": "0.1"},
        },
    }
)


class McpClientTest(unittest.TestCase):
    def test_handshake_list_and_call(self) -> None:
        sent: list[str] = []
        responses = [
            INITIALIZE_RESULT,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {
                        "tools": [
                            {
                                "name": "kb_search",
                                "description": "检索知识库",
                                "inputSchema": {"type": "object"},
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {
                        "content": [{"type": "text", "text": "【问题】答案"}],
                        "isError": False,
                    },
                }
            ),
        ]
        client = McpStdioClient(["fake"], transport=memory_transport(responses, sent))

        client.start()
        tools = client.tools()
        result = client.call_tool("kb_search", {"query": "数据库"})

        self.assertEqual(client.server_info["name"], "fake-kb")
        self.assertEqual(tools[0]["name"], "kb_search")
        self.assertEqual(result, "【问题】答案")
        self.assertEqual(json.loads(sent[0])["method"], "initialize")
        self.assertEqual(json.loads(sent[1])["method"], "notifications/initialized")
        self.assertEqual(json.loads(sent[2])["method"], "tools/list")
        self.assertEqual(json.loads(sent[3])["method"], "tools/call")

    def test_tool_level_is_error_returns_error_string(self) -> None:
        sent: list[str] = []
        responses = [
            INITIALIZE_RESULT,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {
                        "content": [{"type": "text", "text": "query 不能为空"}],
                        "isError": True,
                    },
                }
            ),
        ]
        client = McpStdioClient(["fake"], transport=memory_transport(responses, sent))
        client.start()

        self.assertEqual(client.call_tool("kb_search", {}), "error: query 不能为空")

    def test_json_rpc_error_raises_mcp_error(self) -> None:
        client = McpStdioClient(
            ["fake"],
            transport=memory_transport(
                [
                    json.dumps(
                        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "bad"}}
                    )
                ],
                [],
            ),
        )

        with self.assertRaisesRegex(McpError, "bad"):
            client.start()

    def test_notifications_are_skipped_while_awaiting_response(self) -> None:
        sent: list[str] = []
        notification = json.dumps(
            {"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}}
        )
        late_response = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "result": {"protocolVersion": "2025-06-18"}}
        )
        client = McpStdioClient(
            ["fake"],
            transport=memory_transport([notification, late_response], sent),
        )

        result = client._request("initialize", {})  # noqa: SLF001 - unit under test

        self.assertEqual(result["protocolVersion"], "2025-06-18")

    def test_remote_tools_join_registry_and_execute(self) -> None:
        sent: list[str] = []
        responses = [
            INITIALIZE_RESULT,
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "result": {
                        "tools": [
                            {
                                "name": "kb_search",
                                "description": "检索知识库",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                },
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "result": {
                        "content": [{"type": "text", "text": "【Aster 用什么数据库？】没有"}],
                        "isError": False,
                    },
                }
            ),
        ]
        client = McpStdioClient(["fake"], transport=memory_transport(responses, sent))
        client.start()

        registry = ToolRegistry([])
        for tool in client_tools(client):
            registry.add(tool)

        self.assertEqual(
            [spec["name"] for spec in registry.specs()],
            ["kb_search"],
        )
        result = registry.execute("kb_search", {"query": "数据库"})
        self.assertIn("没有", result)
        self.assertTrue(registry.audit[-1]["ok"])

    def test_duplicate_tool_registration_is_rejected(self) -> None:
        registry = ToolRegistry([])
        local = build_default_registry()
        tool = local._tools["create_ticket"]  # noqa: SLF001 - reuse one instance

        registry.add(tool)
        with self.assertRaisesRegex(ValueError, "already registered"):
            registry.add(tool)


class SubprocessEndToEndTest(unittest.TestCase):
    """Real process: our client against the example KB server."""

    @classmethod
    def setUpClass(cls):
        env = dict(
            os.environ,
            PYTHONPATH=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        cls.client = McpStdioClient([sys.executable, "-B", str(_example_path())], env=env)
        cls.client.start()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()

    def test_lists_and_calls_kb_search(self) -> None:
        tools = self.client.tools()

        self.assertEqual(tools[0]["name"], "kb_search")
        result = self.client.call_tool("kb_search", {"query": "Aster 用什么数据库？"})

        self.assertIn("【Aster 使用什么数据库？】", result)
        self.assertIn("sqlite3", result)


def _example_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples",
        "kb_mcp_server.py",
    )


if __name__ == "__main__":
    unittest.main()
