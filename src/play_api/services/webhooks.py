"""/webhooks/* — inbox lifecycle (private `token`) and capture via any method on the public `ingest_token`."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import HeaderPairs, Headers, Params


def create_inbox() -> httpx.Response:
    return client.post(paths.WEBHOOKS_INBOX)


def get_inbox(token: str) -> httpx.Response:
    return client.get(paths.webhook(token))


def delete_inbox(token: str) -> httpx.Response:
    return client.delete(paths.webhook(token))


def ingest(
    ingest_token: str,
    method: str = "POST",
    *,
    content: str | bytes | None = None,
    headers: Headers | HeaderPairs | None = None,
    params: Params | None = None,
) -> httpx.Response:
    return client.request(method, paths.webhook_ingest(ingest_token), content=content, headers=headers, params=params)


def list_events(token: str, params: Params | None = None) -> httpx.Response:
    return client.get(paths.webhook_events(token), params=params)


def get_event(token: str, event_id: str) -> httpx.Response:
    return client.get(paths.webhook_event(token, event_id))
