"""Local history dashboard: stat tiles + searchable dictation log.

Binds to 127.0.0.1 only — the page and the /api/history JSON are unreachable
from the network, keeping the privacy guarantee intact. Runs on a daemon
thread so quitting the dictation app tears it down too.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import history

_HTML_PATH = Path(__file__).parent / "dashboard.html"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path in ("/", "/index.html"):
            body = _HTML_PATH.read_bytes()
            ctype = "text/html; charset=utf-8"
        elif self.path == "/api/history":
            body = json.dumps(history.read_all()).encode("utf-8")
            ctype = "application/json"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        pass  # keep the terminal clear for dictation feedback


def start_dashboard(port: int = 8765) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
