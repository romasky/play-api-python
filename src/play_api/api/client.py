"""HTTP transport — the ONE choke point every service goes through (port of src/api/restClient.js).

Design (keep it):
* `request()` opens one Allure sub-step per HTTP call and attaches params / headers / body /
  status / response body inside it.
* httpx never raises on 4xx/5xx, so no `validateStatus` equivalent is needed; steps assert
  on the returned `Response`. Redirects are NOT followed unless asked (`follow_redirects=True`).
* `headers` are passed through untouched except for one normalisation: surrounding
  whitespace is trimmed, because h11 (httpx's HTTP/1.1 layer) refuses to send a value such
  as `"Bearer "` (RFC 7230 field-value grammar) and raises LocalProtocolError. axios trims
  the same way, so this is exactly what the JS port put on the wire (→ INVALID_TOKEN_FORMAT).
  `headers` may also be a list of pairs when a header repeats.
* Bodies: `json=` — a request model (serialised with `to_body()`), any JSON value, or `RawJson`
  (verbatim malformed JSON); `content=` (raw text/bytes — send your own Content-Type); or `files=`
  (multipart parts, form fields included). Large or binary payloads are summarised in the report.
* Every 2xx JSON body is validated against its registered contract (`contract_for`). A violation raises
  `ContractViolation`, which still carries the response — so a create step can register its cleanup.
* A client-side timeout is recorded inside the sub-step (which stays green) and re-raised after it.
"""

from __future__ import annotations

import json as jsonlib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

import allure
import httpx2 as httpx  # httpx2 == httpx maintained by Pydantic Services; API identical

from play_api import pacing
from play_api.config import settings
from play_api.models.requests import Body
from play_api.models.responses import contract_for

Headers = dict[str, str]
# a list of pairs when a header repeats (`X-Custom: one` + `X-Custom: two`)
HeaderPairs = list[tuple[str, str]]
_Scalar = str | int | float | bool | None
# Mapping for plain params; a list of pairs when a key repeats (`filter=a:1&filter=b:2`).
Params = Mapping[str, _Scalar] | list[tuple[str, _Scalar]]
# multipart parts: [("file", (filename, bytes, content_type)), ("description", (None, b"text", None))]
Files = list[tuple[str, tuple[str | None, bytes, str | None]]]

_ATTACH_LIMIT = 64 * 1024

_client = httpx.Client(base_url=settings.base_url, timeout=settings.request_timeout)


class RawJson(str):
    """A `json=` value to send VERBATIM as `application/json` — for deliberately malformed payloads
    (truncated JSON) that cannot be represented as a Python value."""


class ContractViolation(AssertionError):
    """A 2xx body broke its contract. `response` is the real response, so callers can still clean up."""

    def __init__(self, message: str, response: httpx.Response) -> None:
        super().__init__(message)
        self.response = response


def _wire_headers(headers: Headers | HeaderPairs | None) -> HeaderPairs:
    """Pairs with trimmed values (the attachment keeps the value exactly as the step wrote it)."""
    pairs = list(headers.items()) if isinstance(headers, dict) else list(headers or [])
    return [(name, value.strip()) for name, value in pairs]


def _attach_text(text: str, name: str, kind: Any) -> None:
    if len(text) > _ATTACH_LIMIT:
        text = f"{text[:_ATTACH_LIMIT]}\n… truncated ({len(text)} chars in total)"
    allure.attach(text, name, kind)


def _attach_request(
    params: Params | None,
    headers: Headers | HeaderPairs | None,
    json: Any,
    content: str | bytes | None,
    files: Files | None,
) -> None:
    if params:
        pairs = list(params.items()) if isinstance(params, Mapping) else list(params)
        allure.attach(jsonlib.dumps(pairs, indent=2), "Query Params", allure.attachment_type.JSON)
    if headers:
        allure.attach(jsonlib.dumps(headers, indent=2), "Request Headers", allure.attachment_type.JSON)
    if json is not None:
        _attach_text(jsonlib.dumps(json, indent=2, ensure_ascii=False), "Request Body", allure.attachment_type.JSON)
    if isinstance(content, str):
        _attach_text(content, "Request Body", allure.attachment_type.TEXT)
    elif isinstance(content, bytes):
        allure.attach(f"<{len(content)} bytes>", "Request Body", allure.attachment_type.TEXT)
    if files:
        summary = [{"field": name, "filename": f[0], "bytes": len(f[1]), "content_type": f[2]} for name, f in files]
        allure.attach(jsonlib.dumps(summary, indent=2), "Multipart Files", allure.attachment_type.JSON)


def _attach_response(response: httpx.Response) -> Any:
    """Attach status, headers and body; return the parsed JSON body (None when not JSON)."""
    allure.attach(str(response.status_code), "Status", allure.attachment_type.TEXT)
    allure.attach(jsonlib.dumps(dict(response.headers), indent=2), "Response Headers", allure.attachment_type.JSON)
    if not response.content:
        return None
    try:
        parsed = response.json()
    except ValueError:
        if response.headers.get("content-type", "").startswith(("text/", "application/x-yaml", "application/yaml")):
            _attach_text(response.text, "Response Body", allure.attachment_type.TEXT)
        else:
            content_type = response.headers.get("content-type")
            allure.attach(
                f"<{len(response.content)} bytes, {content_type}>", "Response Body", allure.attachment_type.TEXT
            )
        return None
    _attach_text(jsonlib.dumps(parsed, indent=2, ensure_ascii=False), "Response Body", allure.attachment_type.JSON)
    return parsed


def _check_contract(method: str, path: str, response: httpx.Response, parsed: Any) -> None:
    # Schema check: every documented 2xx JSON shape must hold, whatever the scenario asserts later.
    # 204/304 and HEAD carry no body, so `parsed` is None and nothing is checked.
    contract = contract_for(method, path) if 200 <= response.status_code < 300 and parsed is not None else None
    if contract is not None:
        with allure.step(f"Contract: {contract.__name__}"):
            try:
                contract.check(parsed)
            except AssertionError as exc:
                raise ContractViolation(str(exc), response) from None


def request(
    method: str,
    path: str,
    *,
    json: Any = None,
    content: str | bytes | None = None,
    files: Files | None = None,
    params: Params | None = None,
    headers: Headers | HeaderPairs | None = None,
    follow_redirects: bool = False,
    timeout: float | None = None,
) -> httpx.Response:
    # allure-python has no per-step parameters (unlike allure-js-commons ctx.parameter),
    # so every per-call datum goes in as a small attachment inside the sub-step.
    if isinstance(json, Body):
        json = json.to_body()
    elif isinstance(json, RawJson):
        json, content = None, str(json)
        headers = [("Content-Type", "application/json"), *_wire_headers(headers)]
    timed_out: httpx.TimeoutException | None = None
    with allure.step(f"{method} {path}"):
        _attach_request(params, headers, json, content, files)
        pacing.throttle(method, path)
        try:
            response = _client.request(
                method,
                path,
                json=json,
                content=content,
                files=files,
                params=params,
                headers=_wire_headers(headers),
                follow_redirects=follow_redirects,
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.TimeoutException as exc:
            # an expected outcome in timeout scenarios: note it, leave the sub-step green, re-raise below
            allure.attach(f"{type(exc).__name__} after the {timeout} s client timeout", "Timeout", "text/plain")
            timed_out = exc
        else:
            for hop in response.history:
                allure.attach(f"{hop.status_code} → {hop.headers.get('location')}", "Redirect", "text/plain")
            parsed = _attach_response(response)
            _check_contract(method, path, response, parsed)
    if timed_out is not None:
        raise timed_out
    return response


@contextmanager
def stream(
    method: str, path: str, *, params: Params | None = None, headers: Headers | None = None
) -> Iterator[httpx.Response]:
    """Streaming variant (SSE, raw bytes): the body is NOT read up front — iterate the response."""
    with allure.step(f"{method} {path} (stream)"):
        _attach_request(params, headers, None, None, None)
        pacing.throttle(method, path)
        with _client.stream(method, path, params=params, headers=_wire_headers(headers)) as response:
            allure.attach(str(response.status_code), "Status", allure.attachment_type.TEXT)
            yield response


def get(path: str, *, params: Params | None = None, headers: Headers | None = None, **kwargs: Any) -> httpx.Response:
    return request("GET", path, params=params, headers=headers, **kwargs)


def post(path: str, json: Any = None, *, headers: Headers | None = None, **kwargs: Any) -> httpx.Response:
    return request("POST", path, json=json, headers=headers, **kwargs)


def put(path: str, json: Any, *, headers: Headers | None = None) -> httpx.Response:
    return request("PUT", path, json=json, headers=headers)


def patch(path: str, json: Any, *, headers: Headers | None = None) -> httpx.Response:
    return request("PATCH", path, json=json, headers=headers)


def delete(path: str, *, headers: Headers | None = None) -> httpx.Response:
    return request("DELETE", path, headers=headers)


def options(path: str, *, headers: Headers | None = None) -> httpx.Response:
    return request("OPTIONS", path, headers=headers)
