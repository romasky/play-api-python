"""Shared step plumbing: the quote-safe parser, header and cleanup helpers, named-route dispatch.

`quoted()` — step parser for phrases whose arguments are all quoted strings.
`parsers.parse('… for "{id}" and save response as "{var}"')` compiles `{id}` to a lazy `.+?` that can
swallow quotes, so it ALSO matches `… for "x" with raw auth header "Bearer" and save response as "r"`
(id = `x" with raw auth header "Bearer`) — two definitions match one step and pytest-bdd silently picks
one. `quoted()` keeps the same readable template but every `"{name}"` matches a quote-free string
(empty allowed, unlike parse's ≥ 1 char), so sibling phrasings can never overlap.
Not for `… with raw body "{…}"` steps: their JSON carries escaped quotes (`{\\"role\\":…}`) — keep `parsers.parse`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from typing import Any

import httpx2 as httpx
from pytest_bdd import parsers

from play_api.api import auth
from play_api.api.client import ContractViolation, Headers
from play_api.context import ScenarioContext
from play_api.utils.lookup import choose

_FIELD = re.compile(r"\{(\w+)\}")


def quoted(template: str) -> parsers.re:
    pattern = "".join(
        f'(?P<{part}>[^"]*)' if i % 2 else re.escape(part) for i, part in enumerate(_FIELD.split(template))
    )
    return parsers.re(pattern)


def bearer(ctx: ScenarioContext, token_key: str) -> Headers:
    return auth.bearer(ctx.str(token_key))


def raw_header(ctx: ScenarioContext, header: str) -> Headers:
    """A verbatim Authorization value; `${key}` placeholders are interpolated (e.g. `bearer ${token}`)."""
    return auth.raw(ctx.render(header))


def save_created(
    ctx: ScenarioContext,
    var: str,
    create: Callable[[], httpx.Response],
    cleanup: Callable[[dict[str, Any]], object],
) -> None:
    """Create something server-side, register its deletion (from the 201 body), save the response.

    The cleanup is registered even when the 201 body violates its contract — the client raises
    `ContractViolation` after the resource exists, and a leaked inbox / upload counts against a per-IP quota.
    """
    try:
        response = create()
    except ContractViolation as violation:
        created = violation.response  # bind now: Python unbinds `violation` when the except block ends
        if created.status_code == 201:
            ctx.defer(lambda: cleanup(created.json()))
        raise
    if response.status_code == 201:
        body = response.json()
        ctx.defer(lambda: cleanup(body))
    ctx.save(var, response)


def route_call(
    routes: Mapping[str, Callable[[Headers], httpx.Response]], name: str
) -> Callable[[Headers], httpx.Response]:
    """Auth-matrix outlines address protected routes by name — one call per route, any credentials."""
    return choose(routes, name, "route")
