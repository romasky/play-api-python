"""/jwt/* — the second auth scheme: HS256 access + refresh pair, and a public token inspector."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers
from play_api.services import JsonBody, to_json

# The JWT endpoints cap request bodies at 16 KiB (→ 413 PAYLOAD_TOO_LARGE)
BODY_LIMIT = 16 * 1024


def login(body: JsonBody) -> httpx.Response:
    return client.post(paths.JWT_LOGIN, to_json(body))


def me(headers: Headers) -> httpx.Response:
    return client.get(paths.JWT_ME, headers=headers)


def refresh(body: JsonBody, headers: Headers | None = None) -> httpx.Response:
    return client.post(paths.JWT_REFRESH, to_json(body), headers)


def decode(body: JsonBody) -> httpx.Response:
    return client.post(paths.JWT_DECODE, to_json(body))
