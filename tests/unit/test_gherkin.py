from __future__ import annotations

import pytest

from play_api.api.client import RawJson
from play_api.utils.gherkin import query_pairs, raw_json, unescape_quotes


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r"{\"a\":1}", '{"a":1}'),  # step text
        ('{\\\\"a\\\\":1}', '{"a":1}'),  # Examples cell: doubled backslash
        (r"\\\"", '\\"'),  # three backslashes: only the last two belong to the escape
        ('{"plain":true}', '{"plain":true}'),
        (r"back\slash", r"back\slash"),
    ],
)
def test_unescape_quotes_undoes_exactly_the_step_and_cell_escaping(text: str, expected: str) -> None:
    assert unescape_quotes(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (r"{\"email\":\"x\"}", {"email": "x"}),
        ('{\\\\"n\\\\":1}', {"n": 1}),
        ("[]", []),
        ("0", 0),
        ("false", False),
        ('""', ""),
    ],
)
def test_raw_json_parses_valid_json_including_falsy_values(text: str, expected: object) -> None:
    value = raw_json(text)
    assert value == expected
    assert type(value) is type(expected)


@pytest.mark.parametrize(
    ("text", "sent"),
    [
        (r"{\"email\":", '{"email":'),  # truncated on purpose
        ("null", "null"),  # the client would read a None value as "no body"
        ("", ""),
    ],
)
def test_raw_json_returns_unparseable_text_and_null_verbatim(text: str, sent: str) -> None:
    value = raw_json(text)
    assert isinstance(value, RawJson)
    assert value == sent


@pytest.mark.parametrize(
    ("query", "pairs"),
    [
        ("limit=3&filter=a:1&filter=b:2&sort=", [("limit", "3"), ("filter", "a:1"), ("filter", "b:2"), ("sort", "")]),
        ("q=a%20b+c", [("q", "a b c")]),
        ("", []),
    ],
)
def test_query_pairs_keeps_order_repeats_and_blank_values(query: str, pairs: list[tuple[str, str]]) -> None:
    assert query_pairs(query) == pairs
