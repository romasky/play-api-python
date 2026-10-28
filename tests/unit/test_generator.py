"""Random data: assert the shapes the API demands and the uniqueness the scenarios rely on, never values."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

import pytest

from play_api.utils import generator

SHAPES: list[tuple[Callable[[], str], str]] = [
    (generator.email, r"[a-z0-9]{10}@play-qa\.com"),
    (generator.username, r"user_[a-z0-9]{8}"),
    (generator.password, r"Pass_[a-z0-9]{10}!1"),
    (generator.phone_number, r"\+1[0-9]{10}"),
    (generator.invalid_email, r"notanemail_[a-z0-9]{4}"),
    (generator.fake_mongo_id, r"[0-9]{24}"),
    (generator.unique_country, r"Country[a-z0-9]{12}"),
    (generator.fake_uuid, r"00000000-0000-0000-0000-[0-9]{12}"),
    (generator.sender_email, r"[^@\s]+\.[a-z0-9]{4}@example\.com"),
    (generator.message_subject, r"[^.]+ [a-z0-9]{6}"),
    (generator.message_body, r".+ [a-z0-9]{10}"),
    (generator.first_name, r"[A-Za-z]{2,}"),
    (generator.last_name, r"[A-Za-z]{2,}"),
]


@pytest.mark.parametrize(("make", "shape"), SHAPES, ids=[make.__name__ for make, _ in SHAPES])
def test_every_value_has_the_exact_api_shape(make: Callable[[], str], shape: str) -> None:
    for _ in range(20):
        assert re.fullmatch(shape, make(), re.DOTALL)


@pytest.mark.parametrize("make", [generator.email, generator.username, generator.unique_country])
def test_values_that_must_be_unique_do_not_repeat(make: Callable[[], str]) -> None:
    assert len({make() for _ in range(200)}) == 200


@pytest.mark.parametrize("length", [0, 1, 37])
def test_random_strings_have_the_requested_length_and_alphabet(length: int) -> None:
    assert re.fullmatch(rf"[a-z0-9]{{{length}}}", generator.alphanumeric(length))
    assert re.fullmatch(rf"[a-z ]{{{length}}}", generator.text(length))
    assert re.fullmatch(rf"[xy]{{{length}}}", generator.random_from("xy", length))


def test_random_from_draws_from_the_whole_alphabet() -> None:
    assert set(generator.random_from("xyz", 300)) == {"x", "y", "z"}


class _Names:
    """Stands in for Faker: yields the given candidates in order."""

    def __init__(self, *candidates: str) -> None:
        self._candidates: Iterator[str] = iter(candidates)

    def first_name(self) -> str:
        return next(self._candidates)

    last_name = first_name


@pytest.mark.parametrize(
    ("candidates", "expected"),
    [
        (("Ann",), "Ann"),
        (("Al",), "Al"),  # 2 chars is enough
        (("A", "O'Brien", "Zoë", "Mary Jo", "Lee"), "Lee"),  # too short, apostrophe, non-ASCII, space: skipped
        (("A", "B", "C", "D", "Fifth"), "Fifth"),  # the fifth candidate is still tried
    ],
)
def test_names_skip_candidates_that_are_not_plain_letters(
    monkeypatch: pytest.MonkeyPatch, candidates: tuple[str, ...], expected: str
) -> None:
    monkeypatch.setattr(generator, "_faker", _Names(*candidates))
    assert generator.first_name() == expected


@pytest.mark.parametrize(("make", "prefix"), [(generator.first_name, "Test"), (generator.last_name, "User")])
def test_after_five_bad_candidates_a_plain_fallback_is_used(
    monkeypatch: pytest.MonkeyPatch, make: Callable[[], str], prefix: str
) -> None:
    monkeypatch.setattr(generator, "_faker", _Names("A", "B", "C", "D", "E", "Fine"))
    assert re.fullmatch(rf"{prefix}[a-z]{{6}}", make())
