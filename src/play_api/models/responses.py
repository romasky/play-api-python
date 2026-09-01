"""Response contracts — port of src/models/*Response.js, but *typed*: pydantic validates the
shape, steps call the `assert_*` helpers. Keep only what steps use (no dead getters).

`extra="allow"` everywhere: the API may add fields; contracts assert presence of the documented ones.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from play_api.utils.json_path import has_path


class _Contract(BaseModel):
    model_config = ConfigDict(extra="allow")

    @classmethod
    def check(cls, body: Any):
        """Validate `body` against the contract; raise AssertionError with the pydantic details."""
        try:
            return cls.model_validate(body)
        except ValidationError as exc:
            raise AssertionError(f"{cls.__name__} contract violated:\n{exc}\nBody: {body}") from None


class ErrorDetails(_Contract):
    code: str
    message: str | None = None
    details: str | None = None


class ErrorEnvelope(_Contract):
    """Standard error shape (NOT used by GET /auth/basic)."""

    success: bool
    error: ErrorDetails
    request_id: str | None = None


class UserResponse(_Contract):
    id: str
    email: str
    username: str
    profile: dict[str, Any]
    metadata: dict[str, Any]


class LoginResponse(_Contract):
    success: bool
    access_token: str
    user_id: str
    email: str
    username: str
    expires_at: str


class UsersListResponse(_Contract):
    users: list[dict[str, Any]]
    page: int
    per_page: int
    total_pages: int


class MessagesListResponse(_Contract):
    messages: list[dict[str, Any]]
    count: int


# ─── assertion helpers used by steps ───────────────────────────────────────

def assert_error_code(body: Any, expected: str) -> None:
    env = ErrorEnvelope.check(body)
    assert env.error.code == expected, f"Expected error code '{expected}' but got '{env.error.code}'. Body: {body}"


def assert_has_request_id(body: Any) -> None:
    env = ErrorEnvelope.check(body)
    assert env.request_id and env.request_id.strip(), f"Expected non-empty 'request_id'. Body: {body}"


def assert_login_successful(body: Any) -> None:
    res = LoginResponse.check(body)
    assert res.success is True, f"Expected success=true. Body: {body}"


def assert_user_core_fields(body: Any) -> None:
    UserResponse.check(body)


def assert_list_items_have_no_field(body: Any, field: str) -> None:
    offenders = [u for u in UsersListResponse.check(body).users if has_path(u, field)]
    assert not offenders, f"{len(offenders)} user(s) in list expose '{field}'. First: {offenders[0]}"


def assert_messages_have_no_full_body(body: Any) -> None:
    messages = MessagesListResponse.check(body).messages
    assert messages, "Expected at least one message in the list to check its shape"
    for i, m in enumerate(messages):
        assert has_path(m, "body_preview"), f"messages[{i}] has no 'body_preview': {m}"
        leaked = [f for f in ("body", "html_body", "headers") if has_path(m, f)]
        assert not leaked, f"messages[{i}] exposes full-body fields {leaked}: {m}"
