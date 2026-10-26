"""System endpoints — GET /health."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers


def health(headers: Headers | None = None) -> httpx.Response:
    return client.get(paths.HEALTH, headers=headers)
