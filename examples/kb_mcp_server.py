"""Dress rehearsal for utopia integration: knowledge search as an MCP tool.

Serves examples/kb.json keyword search over the MCP stdio transport —
the same shape utopia uses (read-only knowledge tools over MCP). Point
Aster at it:

    python -m aster.console --llm --mcp-command "python3 examples/kb_mcp_server.py"

The server logs only to stderr; stdout carries MCP messages.
"""

import json
import sys
from pathlib import Path

# Standalone example: make the repo root importable no matter which
# python launches this script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aster.knowledge import KnowledgeBase  # noqa: E402

KB_PATH = Path(__file__).resolve().parent.parent / "examples" / "kb.json"
PROTOCOL_VERSION = "2025-06-18"


def log(message: str) -> None:
    print(f"[kb-mcp] {message}", file=sys.stderr)


def write(message: dict) -> None:
    sys.stdout.write(json.dumps(message, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> None:
    kb = KnowledgeBase.load(str(KB_PATH))

    for line in sys.stdin:
        if not line.strip():
            continue
        message = json.loads(line)
        method = message.get("method")

        if method == "initialize":
            write(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "aster-kb", "version": "0.1.0"},
                    },
                }
            )
        elif method == "notifications/initialized":
            log("initialized")
        elif method == "tools/list":
            write(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "tools": [
                            {
                                "name": "kb_search",
                                "description": "在 Aster 本地知识库中检索条目",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "检索问题"}
                                    },
                                    "required": ["query"],
                                },
                            }
                        ]
                    },
                }
            )
        elif method == "tools/call":
            params = message.get("params", {})
            query = str(params.get("arguments", {}).get("query", ""))
            hits = kb.search(query)
            text = kb.as_context(hits) or "知识库中没有相关条目。"
            write(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "result": {
                        "content": [{"type": "text", "text": text}],
                        "isError": False,
                    },
                }
            )
        elif method == "ping":
            write({"jsonrpc": "2.0", "id": message["id"], "result": {}})
        elif "id" in message:
            write(
                {
                    "jsonrpc": "2.0",
                    "id": message["id"],
                    "error": {"code": -32601, "message": f"unknown method {method}"},
                }
            )


if __name__ == "__main__":
    main()
