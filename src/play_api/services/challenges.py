"""/challenges/* — guided exercises: start issues a sandbox user, the player acts on it, verify scores it."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers, Params
from play_api.services import JsonBody


def catalog(params: Params | None = None) -> httpx.Response:
    return client.get(paths.CHALLENGES, params=params)


def progress(headers: Headers) -> httpx.Response:
    return client.get(paths.CHALLENGES_PROGRESS, headers=headers)


def hints(challenge_id: str) -> httpx.Response:
    return client.get(paths.challenge_hints(challenge_id))


def reveal(challenge_id: str, body: JsonBody, headers: Headers) -> httpx.Response:
    return client.post(paths.challenge_reveal(challenge_id), body, headers=headers)


def start(challenge_id: str, headers: Headers, params: Params | None = None) -> httpx.Response:
    return client.post(paths.challenge_start(challenge_id), params=params, headers=headers)


def verify(challenge_id: str, headers: Headers, body: JsonBody = None) -> httpx.Response:
    return client.post(paths.challenge_verify(challenge_id), body, headers=headers)
