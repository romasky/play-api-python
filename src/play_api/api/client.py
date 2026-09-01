"""HTTP client — port of src/api/restClient.js.

Design (keep it):
* ONE choke point `request()` for every verb → one Allure sub-step per HTTP call with
  path / params / headers / body / status as step parameters and the request + response
  bodies attached as JSON.
* httpx never raises on 4xx/5xx, so no `validateStatus` equivalent is needed; steps assert
  on the returned `Response`.
* `headers` are passed through untouched except for one normalisation: surrounding
  whitespace is trimmed, because h11 (httpx's HTTP/1.1 layer) refuses to send a value such
  as `"Bearer "` (RFC 7230 field-value grammar) and raises LocalProtocolError. axios trims
  the same way, so this is exactly what the JS port put on the wire (→ INVALID_TOKEN_FORMAT).
  Steps can still send any raw `Authorization` value or omit the header (→ MISSING_TOKEN).
"""

from __future__ import annotations

import json
from typing import Any

import allure
import httpx2 as httpx  # httpx2 == httpx maintained by Pydantic Services; API identical

from play_api.config import settings
from play_api.models.responses import contract_for

_client = httpx.Client(base_url=settings.base_url, timeout=settings.request_timeout)


def bearer_header(token: str | None) -> str:
    if token is None:
        raise ValueError("bearer_header: token is None")
    return token if token.startswith("Bearer ") else f"Bearer {token}"


def request(
    method: str,
    path: str,
    *,
    body: Any = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    # allure-python has no per-step parameters (unlike allure-js-commons ctx.parameter),
    # so every per-call datum goes in as a small attachment inside the sub-step.
    with allure.step(f"{method} {path}"):
        if params:
            allure.attach(json.dumps(params, indent=2), "Query Params", allure.attachment_type.JSON)
        if headers:
            allure.attach(json.dumps(headers, indent=2), "Request Headers", allure.attachment_type.JSON)
        if body is not None:
            allure.attach(json.dumps(body, indent=2, ensure_ascii=False), "Request Body", allure.attachment_type.JSON)

        # Attachment above shows the header exactly as the step wrote it; the wire gets the trimmed value.
        wire_headers = {k: v.strip() for k, v in headers.items()} if headers else headers
        response = _client.request(method, path, json=body, params=params, headers=wire_headers)

        allure.attach(str(response.status_code), "Status", allure.attachment_type.TEXT)
        parsed: Any = None
        if response.content:
            try:
                parsed = response.json()
                allure.attach(
                    json.dumps(parsed, indent=2, ensure_ascii=False), "Response Body", allure.attachment_type.JSON
                )
            except ValueError:
                allure.attach(response.text, "Response Body", allure.attachment_type.TEXT)
        # Schema check: every documented 2xx JSON shape must hold, whatever the scenario asserts later.
        contract = contract_for(method, path) if 200 <= response.status_code < 300 and parsed is not None else None
        if contract is not None:
            with allure.step(f"Contract: {contract.__name__}"):
                contract.check(parsed)
        return response


def post(path: str, body: Any = None, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("POST", path, body=body, headers=headers)


def get(path: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("GET", path, params=params, headers=headers)


def put(path: str, body: Any, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("PUT", path, body=body, headers=headers)


def patch(path: str, body: Any, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("PATCH", path, body=body, headers=headers)


def delete(path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("DELETE", path, headers=headers)


def head(path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("HEAD", path, headers=headers)


def options(path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    return request("OPTIONS", path, headers=headers)
