"""Ready-made valid request bodies for scenarios that test something *other* than payload validation
(auth, ownership, flows). Validation scenarios build their bodies field by field in the steps."""

from __future__ import annotations

from typing import Any

from play_api.config import settings
from play_api.models.requests import (
    AddressReq,
    ContactsReq,
    Coordinates,
    CreateAdminReq,
    CreateUserReq,
    EmploymentReq,
    ProfileReq,
    Salary,
    SettingsReq,
)
from play_api.utils import generator as gen


def minimal_profile() -> ProfileReq:
    return ProfileReq(first_name=gen.first_name(), last_name=gen.last_name())


def minimal_user(country: str | None = None) -> CreateUserReq:
    """Valid create body; `country` isolates the user in shared list queries (`filter=address.country:…`)."""
    return CreateUserReq(
        email=gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=minimal_profile(),
        address=AddressReq(country=country) if country else None,
    )


def admin(seed_code: str | None = settings.admin_seed_code, email: str | None = None) -> CreateAdminReq:
    """Valid create-admin body; `seed_code=None` omits the field entirely."""
    return CreateAdminReq(
        email=email or gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=minimal_profile(),
        seed_code=seed_code,
    )


def random_update() -> CreateUserReq:
    """Valid PUT body (no password)."""
    return CreateUserReq(email=gen.email(), username=gen.username(), profile=minimal_profile())


def random_patch() -> CreateUserReq:
    return CreateUserReq(username=gen.username())


def user_with_all_optional_fields() -> CreateUserReq:
    return CreateUserReq(
        email=gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=ProfileReq(
            first_name=gen.first_name(),
            last_name=gen.last_name(),
            middle_name="Michael",
            gender="other",
            bio="Short bio here.",
            date_of_birth="1990-01-15",
            interests=["coding", "travel"],
            avatar_url="https://example.com/avatar.jpg",
        ),
        contacts=ContactsReq(
            phone=gen.phone_number(),
            telegram="@tester",
            whatsapp=gen.phone_number(),
            linkedin="https://linkedin.com/in/tester",
            github="https://github.com/tester",
            website="https://tester.dev",
        ),
        address=AddressReq(
            country="US",
            state="California",
            city="San Francisco",
            street="Market St",
            building="100",
            apartment="5A",
            zip_code="94105",
            coordinates=Coordinates(latitude=37.7749, longitude=-122.4194),
        ),
        employment=EmploymentReq(
            status="employed",
            company="Acme Inc",
            position="Engineer",
            department="R&D",
            start_date="2020-03-01",
            salary=Salary(amount=120000, currency="USD"),
        ),
        settings=SettingsReq(
            language="en",
            timezone="America/Los_Angeles",
            theme="dark",
            notifications_enabled=True,
            two_factor_enabled=False,
            private_profile=False,
        ),
    )


# ─── Bug reports (POST /bug-reports, auto-scored) ──────────────────────────
# A report scores 100 when: ≥ 2 steps, one step names the bug's METHOD + path, expected/actual are
# ≥ 10 chars and differ, the severity is in the bug's allowed set, and the title is ≥ 12 chars.

_BUG_ENDPOINTS = {
    "pagination-off-by-one": ("GET", "/buggy/items"),
    "cart-total-wrong": ("POST", "/buggy/cart/total"),
    "timezone-shift": ("GET", "/buggy/schedule"),
}
_ALLOWED_SEVERITY = {"pagination-off-by-one": "low", "cart-total-wrong": "high", "timezone-shift": "medium"}


def perfect_bug_report(bug_id: str = "cart-total-wrong", severity: str | None = None) -> dict[str, Any]:
    method, path = _BUG_ENDPOINTS.get(bug_id, ("GET", "/buggy"))
    return {
        "bug_id": bug_id,
        "title": f"{method} {path} returns a wrong result",
        "steps": ["Open the Buggy API catalog", f"Call {method} {path} with the documented example"],
        "expected": "The documented, mathematically correct result",
        "actual": "A result that differs from the documented one",
        "severity": severity or _ALLOWED_SEVERITY.get(bug_id, "medium"),
    }


def _without(body: dict[str, Any], key: str) -> dict[str, Any]:
    return {k: v for k, v in body.items() if k != key}


# every variant starts from a perfect cart-total-wrong report
_BUG_REPORT_VARIANTS = {
    "zero score": lambda b: {
        **b,
        "title": "bug",
        "steps": ["do it"],
        "expected": "same",
        "actual": "same",
        "severity": "low",
    },
    "lowercase method in steps": lambda b: {**b, "steps": ["Open the catalog", "call post /buggy/cart/total"]},
    "missing bug_id": lambda b: _without(b, "bug_id"),
    "bug_id 65 chars": lambda b: {**b, "bug_id": "b" * 65},
    "missing severity": lambda b: _without(b, "severity"),
    "blocker severity": lambda b: {**b, "severity": "blocker"},
    "capitalised severity": lambda b: {**b, "severity": "Medium"},
    "blank title": lambda b: {**b, "title": "   "},
    "title 201 chars": lambda b: {**b, "title": "t" * 201},
    "expected 2001 chars": lambda b: {**b, "expected": "e" * 2001},
    "no steps": lambda b: {**b, "steps": []},
    "21 steps": lambda b: {**b, "steps": [f"step {i}" for i in range(21)]},
    "a blank step": lambda b: {**b, "steps": ["first step", "   "]},
    "oversized body": lambda b: {**b, "padding": "x" * (64 * 1024 + 1)},
}


def bug_report(variant: str) -> dict[str, Any]:
    assert variant in _BUG_REPORT_VARIANTS, (
        f"unknown variant '{variant}', expected one of {sorted(_BUG_REPORT_VARIANTS)}"
    )
    return _BUG_REPORT_VARIANTS[variant](perfect_bug_report())
