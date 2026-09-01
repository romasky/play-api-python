"""User / login / logout steps — port of src/steps/accountsSteps.js.

The three Authorization variants are the heart of the negative coverage (see CLAUDE.md):
  auth.bearer(key)  → "Bearer <token>"   wrong/revoked token → INVALID_TOKEN
  auth.raw(value)   → verbatim value     malformed           → INVALID_TOKEN_FORMAT
  auth.none()       → no header          missing             → MISSING_TOKEN

TODO: port every step from accountsSteps.js (create minimal/body/full/all-optional/raw,
Set employment status/theme/interests/bio, Generate username of length, GET user, list (+ string
page/per_page), exists HEAD/GET, update/patch/delete/logout × {token, raw auth header, no auth token},
login (+ raw body), typed assertions: error code, user core fields, login successful, list not empty,
list items have no field).
"""

from __future__ import annotations

from pytest_bdd import given, then, when, parsers

from play_api.api import client, paths
from play_api.models.requests import CreateUserReq, ProfileReq
from play_api.models.responses import assert_error_code
from play_api.utils import generator as gen


class auth:
    @staticmethod
    def bearer(ctx, token_key: str) -> dict[str, str]:
        return {"Authorization": client.bearer_header(ctx.str(token_key))}

    @staticmethod
    def raw(value: str) -> dict[str, str]:
        return {"Authorization": value}

    @staticmethod
    def none() -> dict[str, str]:
        return {}


def _minimal_profile() -> ProfileReq:
    return ProfileReq(first_name=gen.first_name(), last_name=gen.last_name())


# ─── Create user (example of the pattern) ──────────────────────────────────

@given(parsers.parse('Create minimal user and save response as "{var}"'))
def create_minimal_user(ctx, var):
    email, password = gen.email(), gen.password()
    body = CreateUserReq(email=email, username=gen.username(), password=password, profile=_minimal_profile())
    ctx.save(var, client.post(paths.USERS_CREATE, body.to_body()))
    ctx.save("generatedEmail", email)
    ctx.save("generatedPassword", password)


# ─── Patch user — the three auth variants (example) ────────────────────────

@when(parsers.parse('Patch user "{id_key}" with raw body "{raw_json}" token "{token_key}" and save response as "{var}"'))
def patch_user_raw_body(ctx, id_key, raw_json, token_key, var):
    import json
    ctx.save(var, client.patch(paths.users_patch(ctx.str(id_key)), json.loads(raw_json), auth.bearer(ctx, token_key)))


@when(parsers.parse('Patch user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def patch_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, client.patch(paths.users_patch(ctx.str(id_key)), {"username": gen.username()}, auth.raw(header)))


@when(parsers.parse('Patch user "{id_key}" with no auth token and save response as "{var}"'))
def patch_user_no_auth(ctx, id_key, var):
    ctx.save(var, client.patch(paths.users_patch(ctx.str(id_key)), {"username": gen.username()}, auth.none()))


# ─── Typed assertions ──────────────────────────────────────────────────────

@then(parsers.parse('Assert error code is "{code}" in response "{var}"'))
def assert_error_code_step(ctx, code, var):
    assert_error_code(ctx.body(var), code)
