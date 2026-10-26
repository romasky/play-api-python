"""/challenges/* steps. A solve flow uses the ordinary user steps (Delete / Logout / Login / Patch user) on
the sandbox user that `start` hands out — exactly what a player would do."""

from __future__ import annotations

from collections.abc import Callable

import httpx2 as httpx
from pytest_bdd import parsers, step, when

from play_api.api import auth
from play_api.api.client import Headers
from play_api.models.requests import RevealHintReq
from play_api.services import challenges
from play_api.utils.gherkin import query_pairs, raw_json
from play_api.utils.json_path import get_path
from tests.steps.support import bearer, quoted, raw_header, route_call

_SANDBOX_KEYS = {
    "sandboxId": "user_id",
    "sandboxToken": "access_token",
    "sandboxEmail": "email",
    "sandboxPassword": "password",
}


def _routes(challenge_id: str) -> dict[str, Callable[[Headers], httpx.Response]]:
    """The protected routes by name; auth is checked before the challenge id, so any id exercises it."""
    return {
        "progress": challenges.progress,
        "start": lambda headers: challenges.start(challenge_id, headers),
        "verify": lambda headers: challenges.verify(challenge_id, headers),
        "reveal": lambda headers: challenges.reveal(challenge_id, RevealHintReq(level=1), headers),
    }


@when(quoted('List challenges with query "{query}" and save response as "{var}"'))
def list_challenges(ctx, query, var):
    ctx.save(var, challenges.catalog(query_pairs(query)))


@when(quoted('Get hints of challenge "{challenge_id}" and save response as "{var}"'))
def get_hints(ctx, challenge_id, var):
    ctx.save(var, challenges.hints(challenge_id))


@when(quoted('Get challenge progress with token "{token_key}" and save response as "{var}"'))
def get_progress(ctx, token_key, var):
    ctx.save(var, challenges.progress(bearer(ctx, token_key)))


@when(quoted('Send challenge "{route}" request for "{challenge_id}" with no auth token and save response as "{var}"'))
def challenge_no_auth(ctx, route, challenge_id, var):
    ctx.save(var, route_call(_routes(challenge_id), route)(auth.none()))


@when(
    quoted(
        'Send challenge "{route}" request for "{challenge_id}" with raw auth header "{header}" and save response as "{var}"'  # noqa: E501
    )
)
def challenge_raw_auth(ctx, route, challenge_id, header, var):
    ctx.save(var, route_call(_routes(challenge_id), route)(raw_header(ctx, header)))


@when(quoted('Start challenge "{challenge_id}" with token "{token_key}" and save response as "{var}"'))
def start_challenge(ctx, challenge_id, token_key, var):
    ctx.save(var, challenges.start(challenge_id, bearer(ctx, token_key)))


@when(
    quoted('Start challenge "{challenge_id}" with query "{query}" and token "{token_key}" and save response as "{var}"')
)
def start_challenge_query(ctx, challenge_id, query, token_key, var):
    ctx.save(var, challenges.start(challenge_id, bearer(ctx, token_key), query_pairs(query)))


@step(quoted('Extract the sandbox from "{var}"'))
def extract_sandbox(ctx, var):
    """sandboxId / sandboxToken / sandboxEmail / sandboxPassword from a fresh (201) start."""
    target = get_path(ctx.body(var), "target")
    assert target and target.get("access_token"), f"no fresh sandbox in '{var}': {ctx.body(var)}"
    for key, field in _SANDBOX_KEYS.items():
        ctx.save(key, target[field])


@when(quoted('Verify challenge "{challenge_id}" with token "{token_key}" and save response as "{var}"'))
def verify_challenge(ctx, challenge_id, token_key, var):
    ctx.save(var, challenges.verify(challenge_id, bearer(ctx, token_key)))


@when(
    parsers.parse(
        'Verify challenge "{challenge_id}" with raw body "{raw}" and token "{token_key}" and save response as "{var}"'
    )
)
def verify_challenge_raw(ctx, challenge_id, raw, token_key, var):
    ctx.save(var, challenges.verify(challenge_id, bearer(ctx, token_key), raw_json(ctx.render(raw))))


@when(
    parsers.parse(
        'Reveal hint {level:d} of challenge "{challenge_id}" with token "{token_key}" and save response as "{var}"'
    )
)
def reveal_hint(ctx, level, challenge_id, token_key, var):
    ctx.save(var, challenges.reveal(challenge_id, RevealHintReq(level=level), bearer(ctx, token_key)))


@when(
    parsers.parse(
        'Reveal a hint of challenge "{challenge_id}" with raw body "{raw}" and token "{token_key}" and save response as "{var}"'  # noqa: E501
    )
)
def reveal_hint_raw(ctx, challenge_id, raw, token_key, var):
    ctx.save(var, challenges.reveal(challenge_id, raw_json(ctx.render(raw)), bearer(ctx, token_key)))
