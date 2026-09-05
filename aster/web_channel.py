"""Local web chat channel: the second adapter over the same boundary.

Standard-library HTTP server only — the web-framework decision stays
deferred until a real deployment needs one. Shares the Fake payload
family with the console adapter ({room, event, user, body}), so the same
boundary validation and session semantics apply.
"""

import argparse
import json
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from aster.agent import SessionStore
from aster.console import Runtime, build_runtime, incoming_from_console, process_payload
from aster.storage import save_store

PAGE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aster 本地客服</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
  #log { border: 1px solid #ccc; border-radius: 8px; min-height: 300px;
         padding: 1rem; margin-bottom: 1rem; }
  #log p { margin: 0.4rem 0; }
  form { display: flex; gap: 0.5rem; }
  input { flex: 1; padding: 0.5rem; }
</style>
</head>
<body>
<h1>Aster 本地客服</h1>
<p>会话 room=web-1；服务端策略由启动参数决定（离线 echo 或 MiniMax）。</p>
<div id="log"></div>
<form id="f">
<input id="text" autocomplete="off" placeholder="输入消息，回车发送">
<button>发送</button>
</form>
<script>
const log = document.getElementById('log');
function add(role, text) {
  const p = document.createElement('p');
  const b = document.createElement('b');
  b.textContent = role + '：';
  p.appendChild(b);
  p.appendChild(document.createTextNode(text));
  log.appendChild(p);
}
document.getElementById('f').onsubmit = async (event) => {
  event.preventDefault();
  const input = document.getElementById('text');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  add('你', text);
  try {
    const res = await fetch('/api/message', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        room: 'web-1', event: 'web-' + Date.now(), user: 'webuser', body: text,
      }),
    });
    const data = await res.json();
    add(res.ok ? '客服' : '错误', res.ok ? data.body : data.error);
  } catch (error) {
    add('错误', String(error));
  }
};
</script>
</body>
</html>
"""


class ChatHandler(BaseHTTPRequestHandler):
    """Bound per-server via subclass attributes."""

    store: SessionStore
    save_path: str | None = None
    streaming: bool = False

    def log_message(self, *args: object) -> None:  # keep test/CLI output quiet
        pass

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            page = PAGE_STREAM if self.streaming else PAGE
            self._respond(200, page.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._respond(404, self._error("not found"))

    def do_POST(self) -> None:
        if self.path == "/api/message":
            if self.streaming:
                self._respond(400, self._error("streaming mode: use /api/stream"))
            else:
                self._message()
        elif self.path == "/api/stream":
            if self.streaming:
                self._stream()
            else:
                self._respond(400, self._error("streaming not enabled (start with --stream --llm)"))
        else:
            self._respond(404, self._error("not found"))

    def _message(self) -> None:
        payload, error = self._read_payload()
        if error:
            self._respond(*error)
            return

        try:
            output = process_payload(payload, self.store)
        except ValueError as problem:
            self._respond(400, self._error(str(problem)))
            return
        except RuntimeError as problem:
            self._respond(502, self._error(str(problem)))
            return

        if self.save_path:
            save_store(self.save_path, self.store)
        self._respond(200, output.encode("utf-8"))

    def _stream(self) -> None:
        payload, error = self._read_payload()
        if error:
            self._respond(*error)
            return

        try:
            message = incoming_from_console(payload)
        except ValueError as problem:
            self._respond(400, self._error(str(problem)))
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            for delta in self.store.stream_handle(message):
                self._sse({"delta": delta})
            self._sse({"done": True})
        except RuntimeError as problem:
            self._sse({"error": str(problem)})
        if self.save_path:
            save_store(self.save_path, self.store)

    def _read_payload(self) -> tuple[object, None] | tuple[None, tuple[int, bytes]]:
        """Parse the request body; returns (payload, None) or (None, error)."""

        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length)), None
        except (json.JSONDecodeError, UnicodeDecodeError) as problem:
            return None, (400, self._error(f"payload: invalid JSON ({problem})"))

    def _sse(self, data: dict[str, Any]) -> None:
        self.wfile.write(f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
        self.wfile.flush()

    @staticmethod
    def _error(message: str) -> bytes:
        return json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")

    def _respond(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


PAGE_STREAM = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aster 本地客服（流式）</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
  #log { border: 1px solid #ccc; border-radius: 8px; min-height: 300px;
         padding: 1rem; margin-bottom: 1rem; }
  #log p { margin: 0.4rem 0; white-space: pre-wrap; }
  form { display: flex; gap: 0.5rem; }
  input { flex: 1; padding: 0.5rem; }
</style>
</head>
<body>
<h1>Aster 本地客服（流式）</h1>
<p>回复通过 SSE 增量返回；会话 room=web-stream。</p>
<div id="log"></div>
<form id="f">
<input id="text" autocomplete="off" placeholder="输入消息，回车发送">
<button>发送</button>
</form>
<script>
const log = document.getElementById('log');
function add(role) {
  const p = document.createElement('p');
  const b = document.createElement('b');
  b.textContent = role + '：';
  p.appendChild(b);
  log.appendChild(p);
  return p;
}
document.getElementById('f').onsubmit = async (event) => {
  event.preventDefault();
  const input = document.getElementById('text');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  add('你').appendChild(document.createTextNode(text));
  const p = add('客服');
  try {
    const res = await fetch('/api/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        room: 'web-stream', event: 'web-' + Date.now(), user: 'webuser', body: text,
      }),
    });
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, {stream: true});
      let index;
      while ((index = buffer.indexOf('\\n\\n')) >= 0) {
        const line = buffer.slice(0, index).trim();
        buffer = buffer.slice(index + 2);
        if (!line.startsWith('data: ')) continue;
        const data = JSON.parse(line.slice(6));
        if (data.delta) p.textContent += data.delta;
        if (data.error) p.textContent += '［错误：' + data.error + '］';
      }
    }
  } catch (error) {
    p.textContent += '［错误：' + String(error) + '］';
  }
};
</script>
</body>
</html>
"""


def make_server(args: argparse.Namespace) -> tuple[ThreadingHTTPServer, Runtime]:
    runtime = build_runtime(args)
    handler = type(
        "BoundChatHandler",
        (ChatHandler,),
        {
            "store": runtime.store,
            "save_path": args.store,
            "streaming": runtime.streaming,
        },
    )
    return ThreadingHTTPServer(("127.0.0.1", args.port), handler), runtime


def main() -> None:
    parser = argparse.ArgumentParser(description="Local web chat channel for Aster.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--store", help="SQLite database used to persist conversation sessions across runs"
    )
    parser.add_argument(
        "--llm", action="store_true", help="reply with MiniMax (requires MINIMAX_API_KEY)"
    )
    parser.add_argument(
        "--stream", action="store_true", help="SSE streaming replies (plain chat path, needs --llm)"
    )
    parser.add_argument("--knowledge", help="JSON knowledge base file (needs --llm)")
    parser.add_argument(
        "--kb-mode",
        choices=("keyword", "embedding"),
        default="keyword",
        help="knowledge retrieval mode; embedding uses MiniMax embo-01 (needs MINIMAX_API_KEY)",
    )
    parser.add_argument(
        "--mcp-command",
        action="append",
        metavar="CMD",
        help="MCP stdio server to attach as a tool source (repeatable, needs --llm, no --stream)",
    )
    args = parser.parse_args()

    server, runtime = make_server(args)
    print(f"Aster web channel serving on http://127.0.0.1:{server.server_address[1]}")
    try:
        with suppress(KeyboardInterrupt):
            server.serve_forever()
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
