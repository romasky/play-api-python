from __future__ import annotations

import pytest

from play_api.utils.lookup import choose

TABLE = {"b": 2, "a": 1, "zero": 0}


@pytest.mark.parametrize(("name", "value"), [("a", 1), ("b", 2), ("zero", 0)])
def test_choose_returns_the_named_entry(name: str, value: int) -> None:
    assert choose(TABLE, name, "letter") == value


def test_an_unknown_name_lists_the_valid_ones_sorted() -> None:
    with pytest.raises(AssertionError, match=r"^unknown letter 'c', expected one of \['a', 'b', 'zero'\]$"):
        choose(TABLE, "c", "letter")
