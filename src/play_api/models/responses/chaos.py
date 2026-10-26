"""/chaos/* contracts. Flaky endpoints return their OWN body on every status (even 4xx/5xx from the roll),
so the 2xx contract covers only the success half — the failure half is asserted field by field."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from play_api.models.responses.base import Contract, entry


class CacheResponse(Contract):
    etag: str


class DelayResponse(Contract):
    delayed_seconds: float
    clamped: bool


class EchoResponse(Contract):
    method: str
    path: str
    headers: dict[str, str]
    query: dict[str, str]
    body: Any = Field(...)  # parsed JSON, or null
    raw_body: str | None = Field(...)
    truncated: bool
    client_ip: str
    request_id: str


class FlakyResponse(Contract):
    ok: bool
    failed: bool
    deterministic: bool
    seed: str | None = Field(...)
    roll: float


class FlakyStep(Contract):
    index: int
    roll: float
    status: int
    failed: bool


class FlakySequenceResponse(Contract):
    seed: str
    count: int
    fail_rate: float
    fail_status: int
    steps: list[FlakyStep]
    first_success_index: int
    fails_total: int


class FlakyStepResponse(FlakyStep):
    seed: str


class GzipResponse(Contract):
    gzipped: bool
    origin: str
    method: str


class RedirectDoneResponse(Contract):
    redirected: bool
    method: str
    body_length: int
    body_sha256: str
    message: str


class StatusResponse(Contract):
    status_code: int
    message: str


CONTRACTS_2XX = (
    entry("GET", r"/chaos/cache", CacheResponse),
    entry("GET", r"/chaos/delay/[^/]+", DelayResponse),
    entry("GET", r"/chaos/echo", EchoResponse),
    entry("POST", r"/chaos/echo", EchoResponse),
    entry("GET", r"/chaos/flaky", FlakyResponse),
    entry("GET", r"/chaos/flaky/sequence", FlakySequenceResponse),
    entry("GET", r"/chaos/flaky/step/[^/]+", FlakyStepResponse),
    entry("GET", r"/chaos/gzip", GzipResponse),
    entry("GET", r"/chaos/redirect/done", RedirectDoneResponse),
    entry("POST", r"/chaos/redirect/done", RedirectDoneResponse),
    entry("GET", r"/chaos/status/[^/]+", StatusResponse),
)
