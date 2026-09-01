"""Response contracts — port of src/models/*Response.js, but *typed*: pydantic validates the
shape (docs/API_REFERENCE.md is the source), steps call the `assert_*` helpers.

Two uses:
* explicit step assertions (`assert_error_code`, `assert_user_core_fields`, …) — the JS parity path;
* `contract_for(method, path)` — `client.request()` validates **every 2xx JSON response** against the
  documented shape automatically, so a field disappearing from `POST /mail/create` fails the request
  step even in a scenario that only asserts the status code (Python-only upgrade over the JS port).

`extra="allow"` everywhere: the API may add fields; contracts assert presence of the documented ones.
"""

from __future__ import annotations

import re
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from play_api.utils.json_path import has_path


class _Contract(BaseModel):
    model_config = ConfigDict(extra="allow")

    @classmethod
    def check(cls, body: Any) -> Self:
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


class HealthResponse(_Contract):
    status: str
    time: str


class BasicAuthResponse(_Contract):
    """GET /auth/basic 200 (its 401 shape is non-standard and not covered by ErrorEnvelope)."""

    success: bool
    message: str
    user: str


class LogoutResponse(_Contract):
    success: bool
    message: str


class MailboxResponse(_Contract):
    id: str
    token: str
    email_address: str
    domain: str
    expires_at: str
    created_at: str


class MessageResponse(_Contract):
    """Single message (GET /mail/:token/messages/:id and POST /mail/:token/send 201)."""

    id: str
    from_: str = Field(alias="from")
    subject: str
    body_preview: str
    body: str
    html_body: str | None = None
    headers: dict[str, Any] | None = None
    received_at: str


# ─── 2xx contract registry (method, path regex, contract) ──────────────────
# Endpoints answering 2xx with an empty body (DELETE, HEAD/GET exists, OPTIONS) have no entry.

_CONTRACTS_2XX: tuple[tuple[str, re.Pattern[str], type[_Contract]], ...] = (
    ("GET", re.compile(r"/api/v1/health$"), HealthResponse),
    ("POST", re.compile(r"/api/v1/login$"), LoginResponse),
    ("GET", re.compile(r"/api/v1/auth/basic$"), BasicAuthResponse),
    ("POST", re.compile(r"/api/v1/users/create$"), UserResponse),
    ("GET", re.compile(r"/api/v1/users/list$"), UsersListResponse),
    ("GET", re.compile(r"/api/v1/users/get/[^/]+$"), UserResponse),
    ("PUT", re.compile(r"/api/v1/users/update/[^/]+$"), UserResponse),
    ("PATCH", re.compile(r"/api/v1/users/patch/[^/]+$"), UserResponse),
    ("POST", re.compile(r"/api/v1/users/logout/[^/]+$"), LogoutResponse),
    ("POST", re.compile(r"/api/v1/mail/create$"), MailboxResponse),
    ("GET", re.compile(r"/api/v1/mail/[^/]+$"), MailboxResponse),
    ("GET", re.compile(r"/api/v1/mail/[^/]+/messages$"), MessagesListResponse),
    ("GET", re.compile(r"/api/v1/mail/[^/]+/messages/[^/]+$"), MessageResponse),
    ("POST", re.compile(r"/api/v1/mail/[^/]+/send$"), MessageResponse),
)


def contract_for(method: str, path: str) -> type[_Contract] | None:
    """The documented 2xx contract for an endpoint, or None if it has none (empty-body responses)."""
    return next((c for m, rx, c in _CONTRACTS_2XX if m == method and rx.search(path)), None)


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
