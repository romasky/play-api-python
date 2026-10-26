"""/challenges/* steps. A solve flow uses the ordinary user steps (Delete / Logout / Login / Patch user) on
the sandbox user that `start` hands out — exactly what a player would do."""

from __future__ import annotations

from collections.abc import Callable

import httpx2 as httpx
from pytest_bdd import parsers, when

from play_api.api import auth
from play_api.api.client import Headers
from play_api.services import challenges
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.parsing import quoted

# Auth-matrix outlines address the protected routes by name; auth is checked before the challenge id.
_ROUTES: dict[str, Callable[[str, Headers], httpx.Response]] = {
    "progress": lambda _cid, headers: challenges.progress(headers),
    "start": lambda cid, headers: challenges.start(cid, headers),
    "verify": lambda cid, headers: challenges.verify(cid, headers),
    "reveal": lambda cid, headers: challenges.reveal(cid, {"level": 1}, headers),
}


def _route(name: str) -> Callable[[str, Headers], httpx.Response]:
    assert name in _ROUTES, f"unknown challenge route '{name}', expected one of {sorted(_ROUTES)}"
    return _ROUTES[name]


@when(quoted('List challenges with query "{query}" and save response as "{var}"'))
def list_challenges(ctx, query, var):
    ctx.save(var, challenges.catalog(query_pairs(query)))


@when(quoted('Get hints of challenge "{challenge_id}" and save response as "{var}"'))
def get_hints(ctx, challenge_id, var):
    ctx.save(var, challenges.hints(challenge_id))


@when(quoted('Get challenge progress with token "{token_key}" and save response as "{var}"'))
def get_progress(ctx, token_key, var):
    ctx.save(var, challenges.progress(auth.bearer(ctx.str(token_key))))


@when(quoted('Send challenge "{route}" request for "{challenge_id}" with no auth token and save response as "{var}"'))
def challenge_no_auth(ctx, route, challenge_id, var):
    ctx.save(var, _route(route)(challenge_id, auth.none()))


@when(
    quoted(
        'Send challenge "{route}" request for "{challenge_id}" with raw auth header "{header}" and save response as "{var}"'  # noqa: E501
    )
)
def challenge_raw_auth(ctx, route, challenge_id, header, var):
    ctx.save(var, _route(route)(challenge_id, auth.raw(header)))


@when(quoted('Start challenge "{challenge_id}" with token "{token_key}" and save response as "{var}"'))
def start_challenge(ctx, challenge_id, token_key, var):
    ctx.save(var, challenges.start(challenge_id, auth.bearer(ctx.str(token_key))))


@when(
    quoted('Start challenge "{challenge_id}" with query "{query}" and token "{token_key}" and save response as "{var}"')
)
def start_challenge_query(ctx, challenge_id, query, token_key, var):
    ctx.save(var, challenges.start(challenge_id, auth.bearer(ctx.str(token_key)), query_pairs(query)))


@when(quoted('Verify challenge "{challenge_id}" with token "{token_key}" and save response as "{var}"'))
def verify_challenge(ctx, challenge_id, token_key, var):
    ctx.save(var, challenges.verify(challenge_id, auth.bearer(ctx.str(token_key))))


@when(
    parsers.parse(
        'Verify challenge "{challenge_id}" with raw body "{raw}" and token "{token_key}" and save response as "{var}"'
    )
)
def verify_challenge_raw(ctx, challenge_id, raw, token_key, var):
    ctx.save(var, challenges.verify(challenge_id, auth.bearer(ctx.str(token_key)), raw_json(raw)))


@when(
    parsers.parse(
        'Reveal hint {level:d} of challenge "{challenge_id}" with token "{token_key}" and save response as "{var}"'
    )
)
def reveal_hint(ctx, level, challenge_id, token_key, var):
    ctx.save(var, challenges.reveal(challenge_id, {"level": level}, auth.bearer(ctx.str(token_key))))


@when(
    parsers.parse(
        'Reveal a hint of challenge "{challenge_id}" with raw body "{raw}" and token "{token_key}" and save response as "{var}"'  # noqa: E501
    )
)
def reveal_hint_raw(ctx, challenge_id, raw, token_key, var):
    ctx.save(var, challenges.reveal(challenge_id, raw_json(raw), auth.bearer(ctx.str(token_key))))
