"""Streaming endpoints — Server-Sent Events (GET /sse/progress) and the WebSocket echo (GET /ws/echo).

httpx cannot speak WebSocket, so `/ws/echo` uses the `websockets` sync client; the same base URL is
rewritten https → wss. Both are wrapped in an Allure step like every other call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import allure
import httpx2 as httpx
from websockets.sync.client import ClientConnection, connect

from play_api.api import client, paths
from play_api.api.client import Params
from play_api.config import settings


@dataclass(frozen=True)
class SseEvent:
    event: str
    data: dict[str, Any]


def sse_progress(params: Params) -> list[SseEvent]:
    """Read the whole stream (it closes after `done`) and parse its `event:` / `data:` pairs."""
    events: list[SseEvent] = []
    event = "message"
    with client.stream("GET", paths.SSE_PROGRESS, params=params) as response:
        assert response.status_code == 200, f"SSE stream answered {response.status_code}"
        for line in response.iter_lines():
            if line.startswith("event:"):
                event = line.removeprefix("event:").strip()
            elif line.startswith("data:"):
                events.append(SseEvent(event, json.loads(line.removeprefix("data:").strip())))
                event = "message"
    allure.attach(json.dumps([e.__dict__ for e in events], indent=2), "SSE events", allure.attachment_type.JSON)
    return events


def sse_progress_response(params: Params) -> httpx.Response:
    """Non-streaming call — for the 400 validation answers."""
    return client.get(paths.SSE_PROGRESS, params=params)


def ws_connect() -> ClientConnection:
    url = settings.base_url.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + paths.WS_ECHO
    with allure.step(f"WebSocket connect {paths.WS_ECHO}"):
        return connect(url, open_timeout=settings.request_timeout)


def ws_plain_get() -> httpx.Response:
    """An ordinary HTTP GET without the Upgrade handshake → 426 UPGRADE_REQUIRED."""
    return client.get(paths.WS_ECHO)
