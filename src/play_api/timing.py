"""`timed(call)` — run an HTTP call and keep its OUTCOME: the response, or the client-side timeout
(an expected result in timeout scenarios), together with the wall time."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx2 as httpx


@dataclass(frozen=True)
class Outcome:
    result: httpx.Response | httpx.TimeoutException
    seconds: float


def timed(call: Callable[[], httpx.Response]) -> Outcome:
    started = time.monotonic()
    try:
        result: httpx.Response | httpx.TimeoutException = call()
    except httpx.TimeoutException as exc:
        result = exc
    return Outcome(result, time.monotonic() - started)
