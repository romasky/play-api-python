"""`play_api.models.factories` — the request bodies steps send, checked as the wire dicts the API receives."""

from __future__ import annotations

from typing import Any

import pytest

from play_api.config import settings
from play_api.context import ScenarioContext
from play_api.models import factories

# ─── users ────────────────────────────────────────────────────────────────


def _assert_valid_identity(body: dict[str, Any]) -> None:
    assert body["email"].endswith("@play-qa.com")
    assert body["username"].startswith("user_")
    assert set(body["profile"]) == {"first_name", "last_name"}
    assert all(body["profile"].values())


def test_minimal_user_has_credentials_and_a_name_but_no_address() -> None:
    body = factories.minimal_user().to_body()
    assert set(body) == {"email", "username", "password", "profile"}
    _assert_valid_identity(body)
    assert body["password"]


def test_minimal_user_with_a_country_isolates_it_in_list_queries() -> None:
    assert factories.minimal_user(country="ZZQX").to_body()["address"] == {"country": "ZZQX"}


def test_minimal_user_with_an_empty_country_sends_no_address() -> None:
    assert "address" not in factories.minimal_user(country="").to_body()


def test_two_minimal_users_never_collide_on_unique_fields() -> None:
    first, second = factories.minimal_user().to_body(), factories.minimal_user().to_body()
    assert first["email"] != second["email"]
    assert first["username"] != second["username"]


def test_admin_defaults_to_the_published_seed_code() -> None:
    body = factories.admin().to_body()
    assert body["seed_code"] == settings.admin_seed_code == "play-qa-admin"
    assert set(body) == {"email", "username", "password", "profile", "seed_code"}
    _assert_valid_identity(body)


def test_admin_with_seed_none_omits_the_field() -> None:
    assert "seed_code" not in factories.admin(seed_code=None).to_body()


def test_admin_keeps_a_given_seed_and_email() -> None:
    body = factories.admin(seed_code="wrong", email="taken@play-qa.com").to_body()
    assert (body["seed_code"], body["email"]) == ("wrong", "taken@play-qa.com")


def test_random_update_is_a_put_body_without_password() -> None:
    body = factories.random_update().to_body()
    assert set(body) == {"email", "username", "profile"}
    _assert_valid_identity(body)


def test_random_patch_changes_only_the_username() -> None:
    body = factories.random_patch().to_body()
    assert list(body) == ["username"]
    assert body["username"].startswith("user_")


def test_user_with_all_optional_fields_fills_every_section() -> None:
    body = factories.user_with_all_optional_fields().to_body()
    assert set(body) == {"email", "username", "password", "profile", "contacts", "address", "employment", "settings"}
    assert len(body["profile"]) == 8
    assert len(body["contacts"]) == 6
    assert body["address"]["coordinates"] == {"latitude": 37.7749, "longitude": -122.4194}
    assert body["employment"]["salary"] == {"amount": 120000, "currency": "USD"}
    assert body["settings"] == {
        "language": "en",
        "timezone": "America/Los_Angeles",
        "theme": "dark",
        "notifications_enabled": True,
        "two_factor_enabled": False,
        "private_profile": False,
    }


# ─── user_from_context ───────────────────────────────────────────────────


def _ctx(**values: Any) -> ScenarioContext:
    ctx = ScenarioContext({})
    for key, value in values.items():
        ctx.save(key, value)
    return ctx


IDENTITY = {
    "email": "a@play-qa.com",
    "username": "user_a",
    "password": "Pass_1!",
    "firstName": "Ann",
    "lastName": "Lee",
}


def test_user_from_context_builds_the_body_from_saved_keys() -> None:
    assert factories.user_from_context(_ctx(**IDENTITY)).to_body() == {
        "email": "a@play-qa.com",
        "username": "user_a",
        "password": "Pass_1!",
        "profile": {"first_name": "Ann", "last_name": "Lee"},
    }


def test_user_from_context_without_password_is_an_update_body() -> None:
    body = factories.user_from_context(_ctx(**IDENTITY), with_password=False).to_body()
    assert "password" not in body
    assert body["email"] == "a@play-qa.com"


def test_user_from_context_maps_the_optional_profile_keys() -> None:
    ctx = _ctx(
        **IDENTITY,
        gender="female",
        profileBio="Tester",
        dateOfBirth="1990-01-15",
        interests=["qa"],
        avatarUrl="https://x.io/a.png",
    )
    assert factories.user_from_context(ctx).to_body()["profile"] == {
        "first_name": "Ann",
        "last_name": "Lee",
        "gender": "female",
        "bio": "Tester",
        "date_of_birth": "1990-01-15",
        "interests": ["qa"],
        "avatar_url": "https://x.io/a.png",
    }


def test_user_from_context_turns_saved_dicts_into_sections() -> None:
    ctx = _ctx(
        **IDENTITY,
        contacts={"phone": "+100"},
        address={"country": "DE", "coordinates": {"latitude": 1.0, "longitude": 2.0}},
        employment={"status": "employed"},
        settings={"theme": "dark"},
    )
    body = factories.user_from_context(ctx).to_body()
    assert body["contacts"] == {"phone": "+100"}
    assert body["address"] == {"country": "DE", "coordinates": {"latitude": 1.0, "longitude": 2.0}}
    assert body["employment"] == {"status": "employed"}
    assert body["settings"] == {"theme": "dark"}


def test_user_from_context_skips_an_empty_section() -> None:
    assert "contacts" not in factories.user_from_context(_ctx(**IDENTITY, contacts={})).to_body()


def test_user_from_context_reads_global_keys_and_sends_literals_for_unknown_ones() -> None:
    ctx = ScenarioContext({"email": "global@play-qa.com"})
    body = factories.user_from_context(ctx).to_body()
    assert body["email"] == "global@play-qa.com"
    assert body["username"] == "username"  # passthrough: an unsaved key is its own literal
    assert body["profile"] == {"first_name": "firstName", "last_name": "lastName"}


def test_user_from_context_rejects_an_unknown_section_field() -> None:
    with pytest.raises(ValueError, match="nickname"):
        factories.user_from_context(_ctx(**IDENTITY, contacts={"nickname": "x"}))


# ─── bug reports ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("bug_id", "method", "path", "severity"),
    [
        ("pagination-off-by-one", "GET", "/buggy/items", "low"),
        ("cart-total-wrong", "POST", "/buggy/cart/total", "high"),
        ("timezone-shift", "GET", "/buggy/schedule", "medium"),
        ("not-a-bug", "GET", "/buggy", "medium"),
    ],
)
def test_perfect_bug_report_meets_every_scoring_rule(bug_id: str, method: str, path: str, severity: str) -> None:
    report = factories.perfect_bug_report(bug_id)
    assert report["bug_id"] == bug_id
    assert report["severity"] == severity
    assert report["title"] == f"{method} {path} returns a wrong result"
    assert len(report["steps"]) == 2
    assert f"{method} {path} " in report["steps"][1]
    assert len(report["expected"]) >= 10
    assert len(report["actual"]) >= 10
    assert report["expected"] != report["actual"]


def test_perfect_bug_report_defaults_to_cart_total_wrong() -> None:
    assert factories.perfect_bug_report() == factories.perfect_bug_report("cart-total-wrong")


def test_perfect_bug_report_takes_an_explicit_severity() -> None:
    assert factories.perfect_bug_report("cart-total-wrong", "critical")["severity"] == "critical"


PERFECT = factories.perfect_bug_report()


@pytest.mark.parametrize(
    ("variant", "changes"),
    [
        (
            "zero score",
            {"title": "bug", "steps": ["do it"], "expected": "same", "actual": "same", "severity": "low"},
        ),
        ("lowercase method in steps", {"steps": ["Open the catalog", "call post /buggy/cart/total"]}),
        ("bug_id 65 chars", {"bug_id": "b" * 65}),
        ("blocker severity", {"severity": "blocker"}),
        ("capitalised severity", {"severity": "Medium"}),
        ("blank title", {"title": "   "}),
        ("title 201 chars", {"title": "t" * 201}),
        ("expected 2001 chars", {"expected": "e" * 2001}),
        ("no steps", {"steps": []}),
        ("21 steps", {"steps": [f"step {i}" for i in range(21)]}),
        ("a blank step", {"steps": ["first step", "   "]}),
        ("oversized body", {"padding": "x" * (64 * 1024 + 1)}),
    ],
)
def test_bug_report_variant_changes_only_its_fields(variant: str, changes: dict[str, Any]) -> None:
    assert factories.bug_report(variant) == {**PERFECT, **changes}


@pytest.mark.parametrize(("variant", "key"), [("missing bug_id", "bug_id"), ("missing severity", "severity")])
def test_bug_report_missing_variants_drop_exactly_one_key(variant: str, key: str) -> None:
    assert factories.bug_report(variant) == {k: v for k, v in PERFECT.items() if k != key}


def test_unknown_bug_report_variant_lists_the_valid_ones() -> None:
    with pytest.raises(AssertionError, match=r"unknown bug report variant 'nope', expected one of \[.*'zero score'"):
        factories.bug_report("nope")


# ─── cart ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("spec", "items"),
    [
        ("10x2, 5.50x3", [{"price": 10.0, "qty": 2}, {"price": 5.5, "qty": 3}]),
        ("0.1x3", [{"price": 0.1, "qty": 3}]),
        (" 1x1 ,2x0", [{"price": 1.0, "qty": 1}, {"price": 2.0, "qty": 0}]),
    ],
)
def test_cart_parses_price_x_qty_positions(spec: str, items: list[dict[str, Any]]) -> None:
    assert factories.cart(spec).to_body() == {"items": items}


@pytest.mark.parametrize("spec", ["10", "10x2x3", "ax2", "10x1.5"])
def test_cart_rejects_a_malformed_position(spec: str) -> None:
    with pytest.raises(ValueError):
        factories.cart(spec)


@pytest.mark.parametrize("count", [0, 1, 3])
def test_cart_of_has_count_unit_positions(count: int) -> None:
    assert factories.cart_of(count).to_body() == {"items": [{"price": 1, "qty": 1}] * count}
