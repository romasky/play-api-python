from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, cast

import httpx2 as httpx
import pytest
from websockets.sync.client import ClientConnection

from play_api.config import settings
from play_api.services import realtime
from play_api.services.realtime import SseEvent, WsSession
from tests.unit.wire import Wire, install, query


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Wire:
    return install(monkeypatch)


# ─── SSE ────────────────────────────────────────────────────────────────────

STREAM = (
    b": keep-alive comment\n"
    b"id: 1\n"
    b"event: progress\n"
    b'data: {"step": 1}\n'
    b"\n"
    b'data: {"step": 2}\n'  # no event line → "message", the previous name does not stick
    b"\n"
    b"event:done\n"
    b"data:{}\n"
    b"\n"
)


def test_sse_progress_parses_event_and_data_pairs(wire: Wire) -> None:
    wire.reply(httpx.Response(200, content=iter([STREAM[:30], STREAM[30:]])))

    events = realtime.sse_progress([("steps", "2"), ("interval_ms", "100")])

    assert events == [SseEvent("progress", {"step": 1}), SseEvent("message", {"step": 2}), SseEvent("done", {})]
    assert (wire.last.method, wire.last.url.path, query(wire.last)) == (
        "GET",
        "/api/v1/sse/progress",
        [("steps", "2"), ("interval_ms", "100")],
    )
    assert json.loads(wire.attached("SSE events")[0]) == [
        {"event": "progress", "data": {"step": 1}},
        {"event": "message", "data": {"step": 2}},
        {"event": "done", "data": {}},
    ]


def test_sse_progress_refuses_a_non_200(wire: Wire) -> None:
    wire.reply(httpx.Response(400, json={"error": {"code": "INVALID_PARAMS"}}))

    with pytest.raises(AssertionError, match="SSE stream answered 400"):
        realtime.sse_progress({"steps": 1})


# ─── WebSocket ──────────────────────────────────────────────────────────────


@dataclass
class FakeConnection:
    """Stands in for `websockets.sync.client.ClientConnection`: queued frames in, sent frames recorded."""

    incoming: list[str | bytes] = field(default_factory=list)
    sent: list[str | bytes] = field(default_factory=list)
    recv_timeouts: list[float | None] = field(default_factory=list)
    closed: bool = False

    def recv(self, timeout: float | None = None) -> str | bytes:
        self.recv_timeouts.append(timeout)
        return self.incoming.pop(0)

    def send(self, message: str | bytes) -> None:
        self.sent.append(message)

    def close(self) -> None:
        self.closed = True


def _session(*incoming: str | bytes) -> tuple[WsSession, FakeConnection]:
    connection = FakeConnection(incoming=list(incoming))
    return WsSession(cast(ClientConnection, connection)), connection


def test_receive_json_parses_one_frame(wire: Wire) -> None:
    session, connection = _session('{"type": "welcome", "max": 32768}')

    assert session.receive_json() == {"type": "welcome", "max": 32768}
    assert connection.recv_timeouts == [settings.request_timeout]
    assert wire.steps == ["WebSocket receive (JSON)"]
    assert wire.attached("Frame") == ['{"type": "welcome", "max": 32768}']


@pytest.mark.parametrize(
    ("frame", "kind", "attached"),
    [("héllo", "text", "'héllo'"), (b"\x00\xff", "binary", "b'\\x00\\xff'")],
)
def test_echo_sends_the_frame_and_returns_the_reply(wire: Wire, frame: str | bytes, kind: str, attached: str) -> None:
    session, connection = _session(frame)

    assert session.echo(frame) == frame
    assert connection.sent == [frame]
    assert connection.recv_timeouts == [settings.request_timeout]
    assert wire.steps == [f"WebSocket echo ({kind})"]
    assert wire.attached("Reply") == [attached]


def test_close_closes_the_connection() -> None:
    session, connection = _session()

    session.close()

    assert connection.closed is True


@pytest.mark.parametrize(
    ("base_url", "url"),
    [
        ("https://www.play-qa.com", "wss://www.play-qa.com/api/v1/ws/echo"),
        ("http://localhost:8080", "ws://localhost:8080/api/v1/ws/echo"),
        ("https://http.example", "wss://http.example/api/v1/ws/echo"),  # only the scheme is rewritten
    ],
)
def test_ws_connect_opens_the_echo_socket_on_the_base_url(
    wire: Wire, monkeypatch: pytest.MonkeyPatch, base_url: str, url: str
) -> None:
    opened: list[tuple[str, Any]] = []
    connection = FakeConnection(incoming=['{"type": "welcome"}'])

    def connect(uri: str, *, open_timeout: float) -> FakeConnection:
        opened.append((uri, open_timeout))
        return connection

    monkeypatch.setattr(settings, "base_url", base_url)
    monkeypatch.setattr(realtime, "connect", connect)

    session = realtime.ws_connect()

    assert opened == [(url, settings.request_timeout)]
    assert wire.steps == ["WebSocket connect /api/v1/ws/echo"]
    assert session.receive_json() == {"type": "welcome"}  # the session talks to the opened connection
