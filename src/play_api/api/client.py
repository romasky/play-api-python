"""HTTP client — port of src/api/restClient.js.

Design (keep it):
* ONE choke point `request()` for every verb → one Allure sub-step per HTTP call with
  path / params / headers / body / status as step parameters and the request + response
  bodies attached as JSON.
* httpx never raises on 4xx/5xx, so no `validateStatus` equivalent is needed; steps assert
  on the returned `Response`.
* `headers` are passed verbatim — that is what lets steps send a raw `Authorization`
  value (`"Bearer "`, `"Basic …"`) or omit the header entirely (→ MISSING_TOKEN).
"""

from __future__ import annotations

import json
from typing import Any

import allure
import httpx2 as httpx  # httpx2 == httpx maintained by Pydantic Services; API identical

from play_api.config import settings

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

        response = _client.request(method, path, json=body, params=params, headers=headers)

        allure.attach(str(response.status_code), "Status", allure.attachment_type.TEXT)
        if response.content:
            try:
                pretty = json.dumps(response.json(), indent=2, ensure_ascii=False)
                allure.attach(pretty, "Response Body", allure.attachment_type.JSON)
            except ValueError:
                allure.attach(response.text, "Response Body", allure.attachment_type.TEXT)
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
