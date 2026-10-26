"""/users/*, /login, /auth/basic contracts."""

from __future__ import annotations

from typing import Any

from play_api.models.responses.base import Contract, entry
from play_api.utils.json_path import has_path


class UserResponse(Contract):
    id: str
    email: str
    username: str
    profile: dict[str, Any]
    metadata: dict[str, Any]


class LoginResponse(Contract):
    success: bool
    access_token: str
    user_id: str
    email: str
    username: str
    expires_at: str


class UsersListResponse(Contract):
    users: list[dict[str, Any]]
    page: int
    per_page: int
    total: int
    total_pages: int


class BasicAuthResponse(Contract):
    """GET /auth/basic 200 (its 401 shape is non-standard and not covered by ErrorEnvelope)."""

    success: bool
    message: str
    user: str


class LogoutResponse(Contract):
    success: bool
    message: str


CONTRACTS_2XX = (
    entry("POST", r"/login", LoginResponse),
    entry("GET", r"/auth/basic", BasicAuthResponse),
    entry("POST", r"/users/create", UserResponse),
    entry("GET", r"/users/list", UsersListResponse),
    entry("GET", r"/users/get/[^/]+", UserResponse),
    entry("PUT", r"/users/update/[^/]+", UserResponse),
    entry("PATCH", r"/users/patch/[^/]+", UserResponse),
    entry("POST", r"/users/logout/[^/]+", LogoutResponse),
)


def assert_login_successful(body: Any) -> None:
    res = LoginResponse.check(body)
    assert res.success is True, f"Expected success=true. Body: {body}"


def assert_list_items_have_no_field(body: Any, field: str) -> None:
    offenders = [u for u in UsersListResponse.check(body).users if has_path(u, field)]
    assert not offenders, f"{len(offenders)} user(s) in list expose '{field}'. First: {offenders[0]}"
