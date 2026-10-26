"""/users/* — create, read, list, exists, update, patch, delete, logout, options, create-admin."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers, Params
from play_api.services import JsonBody


def create(body: JsonBody) -> httpx.Response:
    return client.post(paths.USERS_CREATE, body)


def create_admin(body: JsonBody) -> httpx.Response:
    return client.post(paths.USERS_CREATE_ADMIN, body)


def get(user_id: str, headers: Headers | None = None) -> httpx.Response:
    return client.get(paths.users_get(user_id), headers=headers)


def list_users(params: Params | None = None, headers: Headers | None = None) -> httpx.Response:
    return client.get(paths.USERS_LIST, params=params, headers=headers)


def exists(user_id: str, method: str) -> httpx.Response:
    """HEAD or GET — both answer 200/404 with an X-User-Exists header."""
    return client.request(method, paths.users_exists(user_id))


def update(user_id: str, body: JsonBody, headers: Headers) -> httpx.Response:
    return client.put(paths.users_update(user_id), body, headers=headers)


def patch(user_id: str, body: JsonBody, headers: Headers) -> httpx.Response:
    return client.patch(paths.users_patch(user_id), body, headers=headers)


def delete(user_id: str, headers: Headers) -> httpx.Response:
    return client.delete(paths.users_delete(user_id), headers=headers)


def logout(user_id: str, headers: Headers) -> httpx.Response:
    return client.post(paths.users_logout(user_id), None, headers=headers)


def options() -> httpx.Response:
    return client.options(paths.USERS_OPTIONS)
