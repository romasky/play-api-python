"""/jwt/* — the second auth scheme: HS256 access + refresh pair, and a public token inspector."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers
from play_api.services import JsonBody

# The JWT endpoints cap request bodies at 16 KiB (→ 413 PAYLOAD_TOO_LARGE)
BODY_LIMIT = 16 * 1024


def login(body: JsonBody) -> httpx.Response:
    return client.post(paths.JWT_LOGIN, body)


def me(headers: Headers) -> httpx.Response:
    return client.get(paths.JWT_ME, headers=headers)


def refresh(body: JsonBody, headers: Headers | None = None) -> httpx.Response:
    return client.post(paths.JWT_REFRESH, body, headers=headers)


def decode(body: JsonBody) -> httpx.Response:
    return client.post(paths.JWT_DECODE, body)
