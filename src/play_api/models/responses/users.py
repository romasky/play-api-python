"""/users/* contracts."""

from __future__ import annotations

from typing import Any

from play_api.models.responses.base import Contract, entry


class UserResponse(Contract):
    id: str
    email: str
    username: str
    profile: dict[str, Any]
    metadata: dict[str, Any]


class UsersListResponse(Contract):
    users: list[dict[str, Any]]
    page: int
    per_page: int
    total: int
    total_pages: int


class LogoutResponse(Contract):
    success: bool
    message: str


CONTRACTS_2XX = (
    entry("POST", r"/users/create", UserResponse),
    entry("GET", r"/users/list", UsersListResponse),
    entry("GET", r"/users/get/[^/]+", UserResponse),
    entry("PUT", r"/users/update/[^/]+", UserResponse),
    entry("PATCH", r"/users/patch/[^/]+", UserResponse),
    entry("POST", r"/users/logout/[^/]+", LogoutResponse),
)
