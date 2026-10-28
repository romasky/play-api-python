"""A fake wire for `play_api.api.client`: every request lands in `Wire.requests`, answers come from a queue.

`install(monkeypatch)` swaps the module-level `client._client` for one on `httpx.MockTransport`, records
`pacing.throttle` instead of sleeping, and records what the Allure report would show (sub-step titles and
attachments) instead of letting allure-python no-op outside a pytest-allure run.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from email.parser import BytesParser
from email.policy import default as email_policy
from typing import Any

import allure
import httpx2 as httpx
import pytest

from play_api import pacing
from play_api.api import client
from play_api.config import settings

Outcome = httpx.Response | Exception | Callable[[httpx.Request], httpx.Response]


# the headers every httpx client sends unless the caller overrides them (accept, accept-encoding, user-agent …)
def _client_default_headers() -> dict[str, str]:
    with httpx.Client() as plain:
        return dict(plain.headers)


_HTTPX_DEFAULTS = _client_default_headers()


@dataclass(frozen=True)
class Part:
    name: str
    filename: str | None
    content: bytes
    content_type: str | None


@dataclass
class Wire:
    requests: list[httpx.Request] = field(default_factory=list)
    outcomes: list[Outcome] = field(default_factory=list)
    throttled: list[tuple[str, str]] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    attachments: list[tuple[str, str, Any]] = field(default_factory=list)

    def reply(self, *outcomes: Outcome) -> None:
        """Answers for the next requests, in order; once they run out every request gets an empty 204."""
        self.outcomes.extend(outcomes)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        outcome = self.outcomes.pop(0) if self.outcomes else httpx.Response(204)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome(request) if callable(outcome) else outcome

    @property
    def last(self) -> httpx.Request:
        assert self.requests, "nothing was sent"
        return self.requests[-1]

    def attached(self, name: str) -> list[str]:
        return [text for text, attached_name, _ in self.attachments if attached_name == name]


def install(monkeypatch: pytest.MonkeyPatch) -> Wire:
    wire = Wire()
    fake = httpx.Client(
        base_url=settings.base_url, timeout=settings.request_timeout, transport=httpx.MockTransport(wire._handle)
    )
    monkeypatch.setattr(client, "_client", fake)
    monkeypatch.setattr(pacing, "throttle", lambda method, path: wire.throttled.append((method, path)))

    @contextmanager
    def step(title: str) -> Iterator[None]:
        wire.steps.append(title)
        yield

    monkeypatch.setattr(allure, "step", step)
    monkeypatch.setattr(
        allure,
        "attach",
        lambda body, name=None, attachment_type=None, **_: wire.attachments.append((body, name, attachment_type)),
    )
    return wire


def _added_by_httpx(name: str, value: str) -> bool:
    if name in ("host", "content-length"):
        return True
    if name == "content-type":  # derived from json= / files= (checked by json_body / multipart)
        return value == "application/json" or value.startswith("multipart/form-data")
    return _HTTPX_DEFAULTS.get(name) == value


def caller_headers(request: httpx.Request) -> list[tuple[str, str]]:
    """The headers the caller put on the request (httpx's own, unchanged defaults left out), as sent."""
    return [(name, value) for name, value in request.headers.multi_items() if not _added_by_httpx(name, value)]


def query(request: httpx.Request) -> list[tuple[str, str]]:
    return list(request.url.params.multi_items())


def json_body(request: httpx.Request) -> Any:
    assert request.headers.get("content-type") == "application/json", request.headers
    return json.loads(request.content)


def _payload(part: Any) -> bytes:
    payload = part.get_payload(decode=True)
    assert isinstance(payload, bytes), payload
    return payload


def multipart(request: httpx.Request) -> list[Part]:
    content_type = request.headers["content-type"]
    assert content_type.startswith("multipart/form-data"), content_type
    message = BytesParser(policy=email_policy).parsebytes(
        b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + request.content
    )
    return [
        Part(
            name=str(part.get_param("name", header="content-disposition")),
            filename=part.get_filename(),
            content=_payload(part),
            content_type=part["content-type"] and part.get_content_type(),
        )
        for part in message.iter_parts()
    ]
