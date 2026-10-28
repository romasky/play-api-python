from __future__ import annotations

import pytest

from play_api.utils.json_path import get_path, has_path

BODY = {"metadata": {"role": "user", "bio": None}, "messages": [{"subject": "hi"}], "count": 0}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("metadata.role", "user"),
        ("messages.0.subject", "hi"),
        ("count", 0),
        ("metadata.bio", None),
        ("metadata.missing", None),
        ("messages.1.subject", None),
        ("messages.x", None),
        ("count.deeper", None),
    ],
)
def test_get_path_returns_the_value_or_none(path: str, expected: object) -> None:
    assert get_path(BODY, path) == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("metadata.role", True),
        ("metadata.bio", True),  # present but null still exists
        ("messages.0", True),
        ("metadata.missing", False),
        ("messages.1", False),
        ("messages.-1", False),
        ("count.deeper", False),
    ],
)
def test_has_path_is_true_only_for_real_keys_and_indexes(path: str, expected: bool) -> None:
    assert has_path(BODY, path) is expected
