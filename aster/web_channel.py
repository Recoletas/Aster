"""Local web chat channel: the second adapter over the same boundary.

Standard-library HTTP server only — the web-framework decision stays
deferred until a real deployment needs one. Shares the Fake payload
family with the console adapter ({room, event, user, body}), so the same
boundary validation and session semantics apply.
"""

import argparse
import json

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from aster.agent import SessionStore
from aster.console import build_runtime, process_payload
from aster.storage import save_store

PAGE = """<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Aster 本地客服</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 2rem auto; padding: 0 1rem; }
  #log { border: 1px solid #ccc; border-radius: 8px; min-height: 300px; padding: 1rem; margin-bottom: 1rem; }
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
      body: JSON.stringify({room: 'web-1', event: 'web-' + Date.now(), user: 'webuser', body: text}),
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
    """Bound per-server via subclass attributes (store/save_path)."""

    store: SessionStore
    save_path: str | None = None

    def log_message(self, *args) -> None:  # keep test/CLI output quiet
        pass

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._respond(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._respond(404, self._error("not found"))

    def do_POST(self) -> None:
        if self.path != "/api/message":
            self._respond(404, self._error("not found"))
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            self._respond(400, self._error(f"payload: invalid JSON ({error})"))
            return

        try:
            output = process_payload(payload, self.store)
        except ValueError as error:
            self._respond(400, self._error(str(error)))
            return
        except RuntimeError as error:
            self._respond(502, self._error(str(error)))
            return

        if self.save_path:
            save_store(self.save_path, self.store)
        self._respond(200, output.encode("utf-8"), "application/json")

    @staticmethod
    def _error(message: str) -> bytes:
        return json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")

    def _respond(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(args) -> ThreadingHTTPServer:
    store, _registry = build_runtime(args)
    handler = type("BoundChatHandler", (ChatHandler,), {"store": store, "save_path": args.store})
    return ThreadingHTTPServer(("127.0.0.1", args.port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local web chat channel for Aster.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--store", help="JSON file used to persist conversation sessions across runs")
    parser.add_argument("--llm", action="store_true", help="reply with MiniMax (requires MINIMAX_API_KEY)")
    parser.add_argument("--knowledge", help="JSON knowledge base file (needs --llm)")
    args = parser.parse_args()

    server = make_server(args)
    print(f"Aster web channel serving on http://127.0.0.1:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
