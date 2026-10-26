"""/admin/* and /users/create-admin contracts."""

from __future__ import annotations

from typing import Any

from play_api.models.responses.base import Contract, entry
from play_api.models.responses.users import UserResponse, UsersListResponse


class RoleCounts(Contract):
    admin: int
    moderator: int
    user: int


class AdminStatsResponse(Contract):
    total: int
    by_role: RoleCounts
    with_active_token: int
    generated_at: str


class AdminUsersListResponse(UsersListResponse):
    """Same envelope as /users/list (but no X-Total-Count / Link headers); rows add `has_active_token`."""


CONTRACTS_2XX = (
    entry("POST", r"/users/create-admin", UserResponse),
    entry("GET", r"/admin/stats", AdminStatsResponse),
    entry("GET", r"/admin/users", AdminUsersListResponse),
    entry("PATCH", r"/admin/users/[^/]+/role", UserResponse),
)


def assert_admin_stats_consistent(body: Any) -> None:
    """One aggregation, so the parts add up; the caller's own admin account is counted."""
    stats = AdminStatsResponse.check(body)
    roles = stats.by_role
    assert roles.admin + roles.moderator + roles.user == stats.total, f"by_role does not sum to total: {body}"
    assert 0 <= stats.with_active_token <= stats.total, f"with_active_token out of range: {body}"
    assert roles.admin >= 1, f"caller is an admin, expected by_role.admin >= 1: {body}"
