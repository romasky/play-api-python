"""/buggy/* — endpoints with INTENTIONAL, permanent bugs (off-by-one, wrong cart sum, timezone shift)."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Params
from play_api.services import JsonBody, to_json


def catalog() -> httpx.Response:
    return client.get(paths.BUGGY)


def items(params: Params | None = None) -> httpx.Response:
    return client.get(paths.BUGGY_ITEMS, params=params)


def cart_total(body: JsonBody) -> httpx.Response:
    return client.post(paths.BUGGY_CART_TOTAL, to_json(body))


def schedule(params: Params | None = None) -> httpx.Response:
    return client.get(paths.BUGGY_SCHEDULE, params=params)
