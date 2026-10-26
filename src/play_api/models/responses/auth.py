"""Authentication contracts — POST /login, GET /auth/basic, /jwt/*, POST /store/login."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from play_api.models.responses.base import Contract, entry


class LoginResponse(Contract):
    success: bool
    access_token: str
    user_id: str
    email: str
    username: str
    expires_at: str


class BasicAuthResponse(Contract):
    """GET /auth/basic 200 (its 401 shape is non-standard and not covered by ErrorEnvelope)."""

    success: bool
    message: str
    user: str


class JwtLoginResponse(Contract):
    success: bool
    token_type: str
    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int
    user_id: str
    email: str


class JwtRefreshResponse(Contract):
    success: bool
    token_type: str
    access_token: str
    access_expires_in: int


class JwtMeResponse(Contract):
    success: bool
    sub: str
    email: str
    claims: dict[str, Any]


class JwtDecodeResponse(Contract):
    """The nullable keys are ALWAYS present (null, never missing) — so no defaults: absent = violation."""

    success: bool
    header: dict[str, Any]
    payload: dict[str, Any]
    signature_valid: bool | None = Field(...)
    expired: bool | None = Field(...)
    expires_at: str | None = Field(...)
    issued_at: str | None = Field(...)


class StoreBehavior(Contract):
    login_latency_ms: int
    catalog_latency_ms: int
    visual_bugs: bool
    flaky_add_to_cart: bool


class StoreLoginResponse(Contract):
    success: bool
    persona: str
    session: str
    behavior: StoreBehavior
    message: str


CONTRACTS_2XX = (
    entry("POST", r"/login", LoginResponse),
    entry("GET", r"/auth/basic", BasicAuthResponse),
    entry("POST", r"/jwt/login", JwtLoginResponse),
    entry("POST", r"/jwt/refresh", JwtRefreshResponse),
    entry("GET", r"/jwt/me", JwtMeResponse),
    entry("POST", r"/jwt/decode", JwtDecodeResponse),
    entry("POST", r"/store/login", StoreLoginResponse),
)


def assert_login_successful(body: Any) -> None:
    res = LoginResponse.check(body)
    assert res.success is True, f"Expected success=true. Body: {body}"
