"""Fixtures for the micrompx-monitor test suite.

The tool ships as a single file without a ``.py`` extension (that is the
install story the README sells), so it is loaded here through an explicit
source loader instead of an import.

``FakeUnit`` speaks the same JSON interface as a real decoder: it answers
``GET /json-1/list{"<id>":{}}``, returns ``ERROR_UNKNOWN_ID`` for ids it does
not know, and - like the hand-written parser in the firmware - silently
truncates a batch that is too large.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import socket
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "micrompx-monitor"

#: A realistic answer from MicroMPX Decoder 5.0.2 (values are strings).
SAMPLE_WIDGETS = {
    23185: {"enabled": "0", "value": "3.59658", "text": "Measured loss|3.6 %"},
    20252: {"enabled": "1", "value": "0.689731", "text": "|0.69"},
    7966: {"enabled": "1", "value": "0", "text": "Play backup file now|No"},
    8431: {"enabled": "1", "value": "2", "text": "MicroMPX inputs|2"},
    4647: {"enabled": "1", "value": "8854", "text": "Port|8854"},
    4648: {"enabled": "1", "value": "6.3", "text": "Delay|6.3"},
    21078: {"enabled": "1", "value": "5.0.2", "text": "Software version|5.0.2"},
    20855: {
        "enabled": "1",
        "value": "1Zwolle Zender Zwolle",
        "text": "Description|1Zwolle Zender Zwolle",
    },
    9727: {
        "enabled": "1",
        "value": "rist://192.0.2.10:8854",
        "text": "RIST|rist://192.0.2.10:8854",
    },
}


def load_monitor():
    """Import the extensionless script as a module named ``micrompx_monitor``."""
    loader = importlib.machinery.SourceFileLoader("micrompx_monitor", str(SCRIPT))
    spec = importlib.util.spec_from_loader("micrompx_monitor", loader)
    assert spec is not None, "could not build a spec for %s" % SCRIPT
    module = importlib.util.module_from_spec(spec)
    sys.modules["micrompx_monitor"] = module
    loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def micrompx_monitor():
    """The tool itself, imported from ``./micrompx-monitor``."""
    return load_monitor()


@pytest.fixture(scope="session")
def mm(micrompx_monitor):
    """Short alias for the same module."""
    return micrompx_monitor


class FakeUnit:
    """A MicroMPX JSON endpoint that records what was asked of it."""

    def __init__(self):
        self.widgets = {key: dict(value) for key, value in SAMPLE_WIDGETS.items()}
        self.requests = []  # list of {"ids": [...], "token": str|None}
        self.token = None  # None = no token required
        self.truncate_after = None  # batch keys the parser will return, max
        self.status = 200  # HTTP status to answer with
        self.raw_body = None  # answer with this text instead of JSON
        self.lock = threading.Lock()

    def ids_requested(self):
        with self.lock:
            return [entry["ids"] for entry in self.requests]

    def count_requests(self):
        with self.lock:
            return len(self.requests)

    def forget(self):
        with self.lock:
            self.requests = []


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep the test output clean
        return

    def do_GET(self):
        unit = self.server.unit
        path = urllib.parse.unquote(self.path)
        token = None
        if not path.startswith("/json-1"):
            self._send(404, b"not found")
            return
        rest = path[len("/json-1") :]
        if rest.startswith("."):
            token, _, tail = rest[1:].partition("/")
            rest = "/" + tail
        if not rest.startswith("/list"):
            self._send(404, b"not found")
            return
        body = rest[len("/list") :]
        try:
            requested = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._send(400, b"bad json")
            return
        ids = []
        for key in requested:
            try:
                ids.append(int(key))
            except (TypeError, ValueError):
                pass
        with unit.lock:
            unit.requests.append({"ids": ids, "token": token})
        if unit.token is not None and token != unit.token:
            self._send(401, b"unauthorized")
            return
        if unit.status != 200:
            self._send(unit.status, b"error")
            return
        if unit.raw_body is not None:
            self._send(200, unit.raw_body.encode())
            return
        answer = {}
        for emitted, widget_id in enumerate(ids):
            if unit.truncate_after is not None and emitted >= unit.truncate_after:
                break
            entry = unit.widgets.get(widget_id)
            answer[str(widget_id)] = dict(entry) if entry is not None else "ERROR_UNKNOWN_ID"
        self._send(200, json.dumps(answer).encode())

    def _send(self, status, payload: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def start_unit():
    """Start a fake unit on an ephemeral port and return ``(server, fake)``."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    fake = FakeUnit()
    fake.host, fake.port = server.server_address[0], server.server_address[1]
    server.unit = fake
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.02},
        daemon=True,
    )
    thread.start()
    return server, fake, thread


@pytest.fixture
def unit():
    server, fake, thread = start_unit()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def address(unit):
    """(host, port) of the fake unit."""
    return unit.host, unit.port


def closed_port() -> int:
    """A port nothing listens on, so a connection is refused immediately."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port
