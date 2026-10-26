"""JWT (/jwt/*) and Store persona login steps."""

from __future__ import annotations

from pytest_bdd import given, parsers, step, then, when

from play_api.api import auth
from play_api.models.requests import JwtLoginReq, StoreLoginReq
from play_api.services import jwt, session
from play_api.sessions import shared_jwt_session
from play_api.utils import jwt_tools
from play_api.utils.gherkin import raw_json
from tests.steps.parsing import quoted

# ─── Shared session (one rate-limited JWT login per run, see play_api.sessions) ───


@given("a shared JWT session")
def a_shared_jwt_session(ctx, global_ctx):
    s = shared_jwt_session(global_ctx)
    for key, value in {
        "jwtUserId": s.user_id,
        "jwtEmail": s.email,
        "jwtOpaqueToken": s.opaque_token,
        "jwtAccess": s.access,
        "jwtRefresh": s.refresh,
        "jwtExpiredAccess": s.expired_access,
    }.items():
        ctx.save(key, value)


@step(quoted('Craft "{kind}" JWT from "{src_key}" and save as "{dest_key}"'))
def craft_jwt(ctx, kind, src_key, dest_key):
    ctx.save(dest_key, jwt_tools.craft(kind, ctx.str(src_key)))


# ─── /jwt/login ────────────────────────────────────────────────────────────


@when(quoted('JWT login with "{email_key}" and "{password_key}" and save response as "{var}"'))
def jwt_login(ctx, email_key, password_key, var):
    ctx.save(var, jwt.login(JwtLoginReq(email=ctx.str(email_key), password=ctx.str(password_key))))


@when(quoted('JWT login with "{email_key}" and "{password_key}" and access ttl "{ttl}" and save response as "{var}"'))
def jwt_login_ttl(ctx, email_key, password_key, ttl, var):
    body = JwtLoginReq(email=ctx.str(email_key), password=ctx.str(password_key), access_ttl_seconds=int(ttl))
    ctx.save(var, jwt.login(body))


@when(parsers.parse('JWT login with raw body "{raw}" and save response as "{var}"'))
def jwt_login_raw(ctx, raw, var):
    ctx.save(var, jwt.login(raw_json(ctx.render(raw))))


_OVERSIZED = {"login": jwt.login, "refresh": jwt.refresh, "decode": jwt.decode}


@when(quoted('Send JWT "{endpoint}" request with an oversized body and save response as "{var}"'))
def jwt_oversized(ctx, endpoint, var):
    assert endpoint in _OVERSIZED, f"unknown JWT endpoint '{endpoint}', expected one of {sorted(_OVERSIZED)}"
    ctx.save(var, _OVERSIZED[endpoint]({"padding": "x" * (jwt.BODY_LIMIT + 1)}))


# ─── /jwt/me ───────────────────────────────────────────────────────────────


@when(quoted('Get JWT me with token "{token_key}" and save response as "{var}"'))
def jwt_me(ctx, token_key, var):
    ctx.save(var, jwt.me(auth.bearer(ctx.str(token_key))))


@when(quoted('Get JWT me with raw auth header "{header}" and save response as "{var}"'))
def jwt_me_raw(ctx, header, var):
    ctx.save(var, jwt.me(auth.raw(ctx.render(header))))


@when(parsers.parse('Get JWT me with no auth token and save response as "{var}"'))
def jwt_me_no_auth(ctx, var):
    ctx.save(var, jwt.me(auth.none()))


# ─── /jwt/refresh ──────────────────────────────────────────────────────────


@when(quoted('Refresh JWT with token "{token_key}" and save response as "{var}"'))
def jwt_refresh(ctx, token_key, var):
    ctx.save(var, jwt.refresh({"refresh_token": ctx.str(token_key)}))


@when(quoted('Refresh JWT with token "{token_key}" in the Authorization header only and save response as "{var}"'))
def jwt_refresh_header_only(ctx, token_key, var):
    ctx.save(var, jwt.refresh({}, auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Refresh JWT with raw body "{raw}" and save response as "{var}"'))
def jwt_refresh_raw(ctx, raw, var):
    ctx.save(var, jwt.refresh(raw_json(ctx.render(raw))))


# ─── /jwt/decode ───────────────────────────────────────────────────────────


@when(quoted('Decode JWT "{token_key}" and save response as "{var}"'))
def jwt_decode(ctx, token_key, var):
    ctx.save(var, jwt.decode({"token": ctx.str(token_key)}))


@when(parsers.parse('Decode JWT with raw body "{raw}" and save response as "{var}"'))
def jwt_decode_raw(ctx, raw, var):
    ctx.save(var, jwt.decode(raw_json(ctx.render(raw))))


# ─── Local (unverified) claim checks ───────────────────────────────────────


@then(quoted('Assert JWT "{token_key}" has claim "{claim}" equals "{expected}"'))
def assert_jwt_claim(ctx, token_key, claim, expected):
    _, payload = jwt_tools.parts(ctx.str(token_key))
    actual, resolved = str(payload.get(claim)), ctx.str(expected)
    assert actual == resolved, f"JWT claim '{claim}': expected '{resolved}' but got '{actual}'. Payload: {payload}"


@then(parsers.parse('Assert JWT "{token_key}" lifetime is {seconds:d} seconds'))
def assert_jwt_lifetime(ctx, token_key, seconds):
    _, payload = jwt_tools.parts(ctx.str(token_key))
    lifetime = payload["exp"] - payload["iat"]
    assert lifetime == seconds, f"JWT exp - iat = {lifetime}, expected {seconds}. Payload: {payload}"


# ─── /store/login ──────────────────────────────────────────────────────────


@when(quoted('Store login as "{username}" with password "{password}" and save response as "{var}"'))
def store_login(ctx, username, password, var):
    ctx.save(var, session.store_login(StoreLoginReq(username=ctx.str(username), password=ctx.str(password))))


@when(parsers.parse('Store login with raw body "{raw}" and save response as "{var}"'))
def store_login_raw(ctx, raw, var):
    ctx.save(var, session.store_login(raw_json(raw)))
