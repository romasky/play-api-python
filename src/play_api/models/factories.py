"""Request bodies built for scenarios: valid ready-made ones (for tests of auth, ownership, flows), bodies
assembled from context keys, and named invalid variants."""

from __future__ import annotations

from typing import Any

from play_api.api import paths
from play_api.config import settings
from play_api.context import ScenarioContext
from play_api.models.requests import (
    AddressReq,
    Body,
    CartItem,
    CartReq,
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
from play_api.utils.lookup import choose


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


def user_from_context(ctx: ScenarioContext, *, with_password: bool = True) -> CreateUserReq:
    """A create/update body from context keys set by earlier steps: email, username, (password),
    firstName, lastName, plus whatever optional parts were set (gender, profileBio, contacts, address, …)."""

    def part(key: str, model: type[Body]) -> Any:
        value = ctx.opt(key)
        return model(**value) if value else None

    return CreateUserReq(
        email=ctx.str("email"),
        username=ctx.str("username"),
        password=ctx.str("password") if with_password else None,
        profile=ProfileReq(
            first_name=ctx.str("firstName"),
            last_name=ctx.str("lastName"),
            gender=ctx.opt("gender"),
            bio=ctx.opt("profileBio"),
            date_of_birth=ctx.opt("dateOfBirth"),
            interests=ctx.opt("interests"),
            avatar_url=ctx.opt("avatarUrl"),
        ),
        contacts=part("contacts", ContactsReq),
        address=part("address", AddressReq),
        employment=part("employment", EmploymentReq),
        settings=part("settings", SettingsReq),
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

# bug_id → (method, catalogued path, one allowed severity); paths are relative to /api/v1 as in GET /buggy
_BUGS = {
    "pagination-off-by-one": ("GET", paths.BUGGY_ITEMS, "low"),
    "cart-total-wrong": ("POST", paths.BUGGY_CART_TOTAL, "high"),
    "timezone-shift": ("GET", paths.BUGGY_SCHEDULE, "medium"),
}


def perfect_bug_report(bug_id: str = "cart-total-wrong", severity: str | None = None) -> dict[str, Any]:
    method, full_path, allowed = _BUGS.get(bug_id, ("GET", paths.BUGGY, "medium"))
    path = full_path.removeprefix(paths.BASE)
    return {
        "bug_id": bug_id,
        "title": f"{method} {path} returns a wrong result",
        "steps": ["Open the Buggy API catalog", f"Call {method} {path} with the documented example"],
        "expected": "The documented, mathematically correct result",
        "actual": "A result that differs from the documented one",
        "severity": severity or allowed,
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
    return choose(_BUG_REPORT_VARIANTS, variant, "bug report variant")(perfect_bug_report())


# ─── Buggy cart (POST /buggy/cart/total) ───────────────────────────────────


def cart(spec: str) -> CartReq:
    """`10x2, 5.50x3` → two positions: price 10 × qty 2, price 5.50 × qty 3."""
    positions = (position.strip().split("x") for position in spec.split(","))
    return CartReq(items=[CartItem(price=float(price), qty=int(qty)) for price, qty in positions])


def cart_of(count: int) -> CartReq:
    return CartReq(items=[CartItem(price=1, qty=1)] * count)
