"""`play_api.models.requests` — what `Body.to_body()` puts on the wire."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from play_api.models.requests import (
    AddressReq,
    CartItem,
    CartReq,
    Coordinates,
    CreateAdminReq,
    CreateUserReq,
    JwtLoginReq,
    ProfileReq,
    SendMessageReq,
    SettingsReq,
)


def test_unset_optional_fields_are_absent_never_null() -> None:
    assert CreateUserReq(username="u").to_body() == {"username": "u"}


def test_nested_models_serialise_recursively_and_drop_their_unset_fields() -> None:
    body = CreateUserReq(
        profile=ProfileReq(first_name="Ann"),
        address=AddressReq(country="DE", coordinates=Coordinates(latitude=1.5)),
    ).to_body()
    assert body == {"profile": {"first_name": "Ann"}, "address": {"country": "DE", "coordinates": {"latitude": 1.5}}}


def test_falsy_values_that_are_not_none_are_sent() -> None:
    body = CreateUserReq(
        username="",
        profile=ProfileReq(interests=[]),
        settings=SettingsReq(notifications_enabled=False),
    ).to_body()
    assert body == {"username": "", "profile": {"interests": []}, "settings": {"notifications_enabled": False}}


def test_admin_body_is_the_user_body_plus_the_seed_code() -> None:
    assert CreateAdminReq(email="a@b.c", seed_code="seed").to_body() == {"email": "a@b.c", "seed_code": "seed"}
    assert "seed_code" not in CreateAdminReq(email="a@b.c").to_body()


def test_python_name_from_underscore_serialises_as_the_api_key_from() -> None:
    message = SendMessageReq(from_="me@x.io", subject="s", body="b")
    assert message.to_body() == {"from": "me@x.io", "subject": "s", "body": "b"}


def test_the_api_alias_from_is_accepted_on_input_too() -> None:
    message = SendMessageReq.model_validate({"from": "me@x.io", "subject": "s", "body": "b"})
    assert message.to_body()["from"] == "me@x.io"


def test_unknown_fields_are_rejected_so_a_typo_cannot_silently_vanish() -> None:
    with pytest.raises(ValidationError, match="emial"):
        CreateUserReq.model_validate({"emial": "a@b.c"})


def test_required_fields_are_enforced() -> None:
    with pytest.raises(ValidationError, match="password"):
        JwtLoginReq.model_validate({"email": "a@b.c"})


def test_optional_ttl_is_sent_only_when_given() -> None:
    assert JwtLoginReq(email="a@b.c", password="p").to_body() == {"email": "a@b.c", "password": "p"}
    assert JwtLoginReq(email="a@b.c", password="p", access_ttl_seconds=60).to_body()["access_ttl_seconds"] == 60


def test_cart_serialises_its_positions_in_order() -> None:
    cart = CartReq(items=[CartItem(price=10, qty=2), CartItem(price=5.5, qty=3)])
    assert cart.to_body() == {"items": [{"price": 10, "qty": 2}, {"price": 5.5, "qty": 3}]}
