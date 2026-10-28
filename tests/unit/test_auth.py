from __future__ import annotations

import pytest

from play_api.api import auth


@pytest.mark.parametrize(
    ("token", "header"),
    [
        ("abc", "Bearer abc"),
        ("Bearer abc", "Bearer abc"),  # already prefixed: kept as is
        ("bearer abc", "Bearer bearer abc"),  # the prefix check is case-sensitive
        ("Bearer", "Bearer Bearer"),  # no space → not a prefix
        ("", "Bearer "),  # the client trims it to "Bearer" on the wire
    ],
)
def test_bearer_prefixes_the_token_once(token: str, header: str) -> None:
    assert auth.bearer(token) == {"Authorization": header}


def test_bearer_refuses_a_missing_token() -> None:
    with pytest.raises(ValueError, match="token is None"):
        auth.bearer(None)


@pytest.mark.parametrize("value", ["Token abc", "", "Basic x"])
def test_raw_sends_the_value_verbatim(value: str) -> None:
    assert auth.raw(value) == {"Authorization": value}


def test_none_sends_no_header() -> None:
    assert auth.none() == {}


@pytest.mark.parametrize(
    ("user_pass", "header"),
    [("admin:admin", "Basic YWRtaW46YWRtaW4="), ("ü:", "Basic w7w6")],
)
def test_basic_base64_encodes_the_utf8_credentials(user_pass: str, header: str) -> None:
    assert auth.basic(user_pass) == {"Authorization": header}
