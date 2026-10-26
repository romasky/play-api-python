"""Opaque-token login (POST /login), HTTP Basic (GET /auth/basic) and the Store persona login."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers
from play_api.services import JsonBody, to_json


def login(body: JsonBody) -> httpx.Response:
    return client.post(paths.LOGIN, to_json(body))


def basic_auth(headers: Headers | None = None) -> httpx.Response:
    return client.get(paths.AUTH_BASIC, headers=headers)


def store_login(body: JsonBody) -> httpx.Response:
    return client.post(paths.STORE_LOGIN, to_json(body))
