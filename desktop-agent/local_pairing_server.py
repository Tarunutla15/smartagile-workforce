"""
Localhost-only HTTP server so the web app can push JWTs to the agent (one click, no copy-paste).

Listens on 127.0.0.1 — not reachable from the network.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

import agent_status
import auth_store
import auth_session

logger = logging.getLogger(__name__)

DEFAULT_PORT = 38475

_server: ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None
_pairing_start_lock = threading.Lock()
_pairing_thread_started = False


def pairing_port() -> int:
    try:
        return int(os.environ.get("SMARTAGILE_LOCAL_PORT", str(DEFAULT_PORT)))
    except ValueError:
        return DEFAULT_PORT


class _Handler(BaseHTTPRequestHandler):
    server_version = "SmartAgilePairing/1.0"

    def log_message(self, fmt, *args):
        logger.info("%s - %s", self.address_string(), fmt % args)

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/health", "/health/"):
            self.send_error(404)
            return
        has_tokens = bool(
            auth_store.get_refresh() or os.environ.get("SMARTAGILE_ACCESS_TOKEN")
        )
        paired_user_id = auth_store.get_paired_user_id()
        body = json.dumps(
            {
                "ok": True,
                "has_tokens": has_tokens,
                "port": pairing_port(),
                "paired_user_id": paired_user_id,
                "api_base": auth_store.get_api_base(),
                # Live upload state so Settings can show "tracking active" vs.
                # "reconnect needed" (e.g. a silently expired token).
                "upload": agent_status.snapshot(),
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/pair", "/pair/"):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 1_000_000:
            self.send_error(413)
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data: Any = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        if not isinstance(data, dict):
            self.send_error(400, "Body must be a JSON object")
            return
        access = data.get("access")
        refresh = data.get("refresh")
        api_base = data.get("api_base")
        if not access or not refresh:
            out = json.dumps(
                {"error": "access and refresh are required", "ok": False}
            ).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(out)
            return
        if api_base is not None and not isinstance(api_base, str):
            self.send_error(400, "api_base must be a string")
            return
        ab = (api_base or auth_store.get_api_base()).rstrip("/")
        auth_store.save(
            access=str(access),
            refresh=str(refresh),
            api_base=ab,
        )
        auth_session.clear_memory_cache()
        out = json.dumps(
            {
                "ok": True,
                "message": "Tokens stored",
                "paired_user_id": auth_store.get_paired_user_id(),
                "api_base": auth_store.get_api_base(),
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.end_headers()
        self.wfile.write(out)
        logger.info("Paired: tokens written to %s", auth_store.store_path())


def start_pairing_server() -> int:
    """Start background server on 127.0.0.1. Idempotent. Returns port."""
    global _server, _server_thread, _pairing_thread_started
    port = pairing_port()
    with _pairing_start_lock:
        if _pairing_thread_started:
            return port
        _pairing_thread_started = True

    def run() -> None:
        global _server
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            _server = srv
            logger.info("Pairing server: http://127.0.0.1:%s/health  POST /pair", port)
            srv.serve_forever()
        except OSError as e:
            logger.error("Pairing server bind 127.0.0.1:%s failed: %s", port, e)
            _server = None

    t = threading.Thread(target=run, name="smartagile-pairing", daemon=True)
    t.start()
    _server_thread = t
    return port
