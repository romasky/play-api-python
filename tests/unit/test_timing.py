from __future__ import annotations

import time
from collections.abc import Iterator

import httpx2 as httpx
import pytest

from play_api import timing

REQUEST = httpx.Request("GET", "https://x/chaos/latency")


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks: Iterator[float] = iter([100.0, 103.25])
    monkeypatch.setattr(time, "monotonic", lambda: next(ticks))


def test_timed_keeps_the_response_and_the_elapsed_seconds() -> None:
    response = httpx.Response(200, json={"ok": True}, request=REQUEST)
    outcome = timing.timed(lambda: response)
    assert outcome.result is response
    assert outcome.seconds == pytest.approx(3.25)


def test_timed_turns_a_client_timeout_into_the_outcome() -> None:
    timeout = httpx.ReadTimeout("read timed out", request=REQUEST)

    def call() -> httpx.Response:
        raise timeout

    outcome = timing.timed(call)
    assert outcome.result is timeout
    assert outcome.seconds == pytest.approx(3.25)


def test_timed_lets_other_errors_through() -> None:
    def call() -> httpx.Response:
        raise httpx.ConnectError("refused", request=REQUEST)

    with pytest.raises(httpx.ConnectError):
        timing.timed(call)
