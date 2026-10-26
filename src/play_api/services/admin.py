"""/admin/* — operator endpoints (TokenAuth → RequireAdmin → own-account scope)."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers, Params
from play_api.services import JsonBody


def stats(headers: Headers) -> httpx.Response:
    return client.get(paths.ADMIN_STATS, headers=headers)


def list_users(headers: Headers, params: Params | None = None) -> httpx.Response:
    return client.get(paths.ADMIN_USERS, params=params, headers=headers)


def set_role(user_id: str, body: JsonBody, headers: Headers) -> httpx.Response:
    return client.patch(paths.admin_user_role(user_id), body, headers=headers)


def delete_user(user_id: str, headers: Headers) -> httpx.Response:
    return client.delete(paths.admin_user(user_id), headers=headers)
