"""Minimal synchronous MCP client over the stdio transport.

Speaks newline-delimited JSON-RPC 2.0 per the MCP spec (initialize →
notifications/initialized → tools/list → tools/call). Hand-rolled on
purpose: the official SDK is asyncio-based and our agent loop is sync;
this keeps the process model unchanged and the protocol visible.

Utopia is the target tool source: its read-only knowledge tools are
exposed over MCP, so pointing ``--mcp-command`` at a utopia MCP server
attaches its knowledge as remote Aster tools.
"""

import json
import select
import shlex
import subprocess
from collections.abc import Callable
from functools import partial
from typing import Any

from aster.tools import RemoteTool

PROTOCOL_VERSION = "2025-06-18"
CLIENT_INFO = {"name": "aster", "version": "0.1.0"}
REQUEST_TIMEOUT = 30.0

Transport = tuple[
    Callable[[str], None],  # write_line
    Callable[[], str],  # read_line
    Callable[[], None],  # close
]


class McpError(RuntimeError):
    """A JSON-RPC error response from the MCP server."""


def _subprocess_transport(command: list[str], env: dict[str, str] | None = None) -> Transport:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        # stderr inherits: MCP servers log there, and crash output stays visible
        text=True,
        bufsize=1,
        env=env,
    )

    assert process.stdin is not None and process.stdout is not None
    stdin, stdout = process.stdin, process.stdout

    def write_line(line: str) -> None:
        stdin.write(line + "\n")
        stdin.flush()

    def read_line() -> str:
        import time

        deadline = time.monotonic() + REQUEST_TIMEOUT
        fd = stdout.fileno()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"MCP: no response within {REQUEST_TIMEOUT}s")
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                continue
            line = stdout.readline()
            if line:
                return line
            raise RuntimeError("MCP: server closed stdout")

    def close() -> None:
        stdin.close()
        process.wait(timeout=5)

    return write_line, read_line, close


class McpStdioClient:
    """One MCP session with a stdio server subprocess."""

    def __init__(
        self,
        command: list[str],
        transport: Transport | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.server_info: dict[str, Any] = {}
        self.protocol_version: str | None = None
        self._next_id = 0
        self._write_line, self._read_line, self._close = transport or _subprocess_transport(
            command, env
        )

    @classmethod
    def from_command_string(cls, command_string: str) -> "McpStdioClient":
        return cls(shlex.split(command_string))

    def start(self) -> None:
        """Initialize the session; tolerant of a different protocol version."""

        response = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self.protocol_version = response.get("protocolVersion")
        self.server_info = response.get("serverInfo", {})
        self._notify("notifications/initialized")

    def tools(self) -> list[dict[str, Any]]:
        """The server's tool descriptors (name, description, inputSchema)."""

        result = self._request("tools/list", {})
        return list(result.get("tools", []))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Call one tool; tool-level failures come back as error strings."""

        result = self._request("tools/call", {"name": name, "arguments": arguments})
        texts = [
            str(block.get("text", ""))
            for block in result.get("content", [])
            if block.get("type") == "text"
        ]
        text = "".join(texts) or json.dumps(result.get("content", []), ensure_ascii=False)
        if result.get("isError"):
            return f"error: {text}"
        return text

    def close(self) -> None:
        self._close()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._next_id += 1
        request_id = self._next_id
        self._write_line(
            json.dumps(
                {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params},
                ensure_ascii=False,
            )
        )
        while True:
            message = json.loads(self._read_line())
            if "id" not in message:  # notification or server request: not ours
                continue
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise McpError(f"MCP {method}: {error.get('message', error)}")
            result = message.get("result", {})
            return result if isinstance(result, dict) else {}

    def _notify(self, method: str) -> None:
        self._write_line(json.dumps({"jsonrpc": "2.0", "method": method}, ensure_ascii=False))


def client_tools(client: McpStdioClient, prefix: str = "") -> list[RemoteTool]:
    """Advertise the server's tools as remote Aster tools.

    Arguments pass through unvalidated: the serving side owns its
    contract and reports its own errors, which flow into our audit.
    """

    remote: list[RemoteTool] = []
    for descriptor in client.tools():
        name = str(descriptor.get("name", ""))
        remote.append(
            RemoteTool(
                name=prefix + name,
                description=str(descriptor.get("description", "")),
                input_schema=dict(descriptor.get("inputSchema", {"type": "object"})),
                execute_fn=partial(client.call_tool, name),
            )
        )
    return remote
