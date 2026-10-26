"""Authentication schemes other than the opaque user token: HTTP Basic, JWT (/jwt/*) and the Store personas."""

from __future__ import annotations

from pytest_bdd import given, parsers, step, then, when

from play_api.api import auth
from play_api.assertions import assert_jwt_claim, assert_jwt_lifetime
from play_api.jwt_session import shared_jwt_session
from play_api.models.requests import JwtDecodeReq, JwtLoginReq, JwtRefreshReq, StoreLoginReq
from play_api.services import jwt, login
from play_api.utils import jwt_tools
from play_api.utils.gherkin import raw_json
from play_api.utils.lookup import choose
from tests.steps.support import bearer, quoted, raw_header

# ─── HTTP Basic (GET /auth/basic — non-standard error shape { error, message }) ───


@when(parsers.parse('Send GET basic auth request with no auth header and save as "{var}"'))
def basic_no_header(ctx, var):
    ctx.save(var, login.basic_auth())


@when(parsers.parse('Send GET basic auth request with credentials "{user_pass}" and save as "{var}"'))
def basic_credentials(ctx, user_pass, var):
    ctx.save(var, login.basic_auth(auth.basic(user_pass)))


@when(parsers.parse('Send GET basic auth request with raw auth header "{header}" and save as "{var}"'))
def basic_raw_header(ctx, header, var):
    ctx.save(var, login.basic_auth(raw_header(ctx, header)))


# ─── Shared JWT session (one rate-limited JWT login pair per run, see play_api.jwt_session) ───


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


# deliberately not a request model: one oversized field is all the 413 check needs
@when(quoted('Send JWT "{endpoint}" request with an oversized body and save response as "{var}"'))
def jwt_oversized(ctx, endpoint, var):
    ctx.save(var, choose(_OVERSIZED, endpoint, "JWT endpoint")({"padding": "x" * (jwt.BODY_LIMIT + 1)}))


# ─── /jwt/me ───────────────────────────────────────────────────────────────


@when(quoted('Get JWT me with token "{token_key}" and save response as "{var}"'))
def jwt_me(ctx, token_key, var):
    ctx.save(var, jwt.me(bearer(ctx, token_key)))


@when(quoted('Get JWT me with raw auth header "{header}" and save response as "{var}"'))
def jwt_me_raw(ctx, header, var):
    ctx.save(var, jwt.me(raw_header(ctx, header)))


@when(parsers.parse('Get JWT me with no auth token and save response as "{var}"'))
def jwt_me_no_auth(ctx, var):
    ctx.save(var, jwt.me(auth.none()))


# ─── /jwt/refresh ──────────────────────────────────────────────────────────


@when(quoted('Refresh JWT with token "{token_key}" and save response as "{var}"'))
def jwt_refresh(ctx, token_key, var):
    ctx.save(var, jwt.refresh(JwtRefreshReq(refresh_token=ctx.str(token_key))))


@when(quoted('Refresh JWT with token "{token_key}" in the Authorization header only and save response as "{var}"'))
def jwt_refresh_header_only(ctx, token_key, var):
    ctx.save(var, jwt.refresh({}, bearer(ctx, token_key)))


@when(parsers.parse('Refresh JWT with raw body "{raw}" and save response as "{var}"'))
def jwt_refresh_raw(ctx, raw, var):
    ctx.save(var, jwt.refresh(raw_json(ctx.render(raw))))


# ─── /jwt/decode ───────────────────────────────────────────────────────────


@when(quoted('Decode JWT "{token_key}" and save response as "{var}"'))
def jwt_decode(ctx, token_key, var):
    ctx.save(var, jwt.decode(JwtDecodeReq(token=ctx.str(token_key))))


@when(parsers.parse('Decode JWT with raw body "{raw}" and save response as "{var}"'))
def jwt_decode_raw(ctx, raw, var):
    ctx.save(var, jwt.decode(raw_json(ctx.render(raw))))


# ─── Local (unverified) claim checks ───────────────────────────────────────


@then(quoted('Assert JWT "{token_key}" has claim "{claim}" equals "{expected}"'))
def assert_claim(ctx, token_key, claim, expected):
    assert_jwt_claim(ctx.str(token_key), claim, ctx.str(expected))


@then(parsers.parse('Assert JWT "{token_key}" lifetime is {seconds:d} seconds'))
def assert_lifetime(ctx, token_key, seconds):
    assert_jwt_lifetime(ctx.str(token_key), seconds)


# ─── /store/login ──────────────────────────────────────────────────────────


@when(quoted('Store login as "{username}" with password "{password}" and save response as "{var}"'))
def store_login(ctx, username, password, var):
    ctx.save(var, login.store_login(StoreLoginReq(username=ctx.str(username), password=ctx.str(password))))


@when(parsers.parse('Store login with raw body "{raw}" and save response as "{var}"'))
def store_login_raw(ctx, raw, var):
    ctx.save(var, login.store_login(raw_json(ctx.render(raw))))
