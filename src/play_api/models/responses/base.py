"""Contract base class, the shared error envelope, and the registry entry type."""

from __future__ import annotations

import re
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, ValidationError


class Contract(BaseModel):
    # strict: an int field rejects "900", a bool rejects "true" / 1 (an int still satisfies a float field)
    model_config = ConfigDict(extra="allow", strict=True)

    @classmethod
    def check(cls, body: Any) -> Self:
        """Validate `body` against the contract; raise AssertionError with the pydantic details."""
        try:
            return cls.model_validate(body)
        except ValidationError as exc:
            raise AssertionError(f"{cls.__name__} contract violated:\n{exc}\nBody: {body}") from None


# (method, path regex, contract) — one row per documented 2xx JSON shape
Entry = tuple[str, re.Pattern[str], type[Contract]]


def entry(method: str, path_regex: str, contract: type[Contract]) -> Entry:
    return method, re.compile(rf"/api/v1{path_regex}$"), contract


class ErrorDetails(Contract):
    code: str
    message: str | None = None
    details: str | None = None


class ErrorEnvelope(Contract):
    """Standard error shape (NOT used by GET /auth/basic, Cloudflare 52x pages or chaos/flaky)."""

    success: bool
    error: ErrorDetails
    request_id: str | None = None


def assert_error_code(body: Any, expected: str) -> None:
    env = ErrorEnvelope.check(body)
    assert env.error.code == expected, f"Expected error code '{expected}' but got '{env.error.code}'. Body: {body}"


def assert_has_request_id(body: Any) -> None:
    env = ErrorEnvelope.check(body)
    assert env.request_id and env.request_id.strip(), f"Expected non-empty 'request_id'. Body: {body}"
