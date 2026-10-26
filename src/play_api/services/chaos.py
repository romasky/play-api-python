"""/chaos/* — HTTP-semantics playground: conditional requests, delays, echo, seeded flakiness, gzip,
redirect chains, arbitrary status codes and a gateway timeout.

Timeout-style calls take `read_timeout`: the client then raises `httpx.TimeoutException` instead of
returning, which the steps record as the outcome.
"""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers, Params


def cache(headers: Headers | None = None, method: str = "GET") -> httpx.Response:
    return client.request(method, paths.CHAOS_CACHE, headers=headers)


def delay(seconds: str, read_timeout: float | None = None) -> httpx.Response:
    return client.get(paths.chaos_delay(seconds), timeout=read_timeout)


def timeout(params: Params | None = None, read_timeout: float | None = None) -> httpx.Response:
    return client.get(paths.CHAOS_TIMEOUT, params=params, timeout=read_timeout)


def echo(
    method: str,
    *,
    params: Params | None = None,
    headers: Headers | None = None,
    content: str | bytes | None = None,
) -> httpx.Response:
    return client.request(method, paths.CHAOS_ECHO, params=params, headers=headers, content=content)


def flaky(params: Params | None = None) -> httpx.Response:
    return client.get(paths.CHAOS_FLAKY, params=params)


def flaky_sequence(params: Params | None = None) -> httpx.Response:
    return client.get(paths.CHAOS_FLAKY_SEQUENCE, params=params)


def flaky_step(index: str, params: Params | None = None) -> httpx.Response:
    return client.get(paths.chaos_flaky_step(index), params=params)


def gzip(headers: Headers) -> httpx.Response:
    return client.get(paths.CHAOS_GZIP, headers=headers)


def gzip_magic(headers: Headers) -> bytes:
    """The first two body bytes exactly as sent on the wire (before httpx decodes Content-Encoding)."""
    prefix = b""
    with client.stream("GET", paths.CHAOS_GZIP, headers=headers) as response:
        assert response.status_code == 200, f"GET /chaos/gzip answered {response.status_code}"
        for chunk in response.iter_raw():
            prefix += chunk
            if len(prefix) >= 2:
                break
    return prefix[:2]


def redirect(
    method: str,
    hops: str,
    *,
    params: Params | None = None,
    content: str | None = None,
    follow: bool = False,
) -> httpx.Response:
    return client.request(method, paths.chaos_redirect(hops), params=params, content=content, follow_redirects=follow)


def redirect_done(method: str, content: str | None = None) -> httpx.Response:
    """The chain's final destination, called directly (no redirect involved)."""
    return client.request(method, paths.chaos_redirect("done"), content=content)


def status(code: str) -> httpx.Response:
    return client.get(paths.chaos_status(code))
