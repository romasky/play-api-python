"""tools/check_steps.py — the offline step ↔ definition check, against the real features and a synthetic tree."""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, step, then, when

import check_steps

# ─── synthetic step definitions (this module stands in for the step plugins) ──────────


@given("a known step")
def _known() -> None: ...


@then("twice matched")
def _twice_exact() -> None: ...


@step(parsers.re("twice.*"))  # any keyword — collides with the @then above
def _twice_any() -> None: ...


@when("never used")
def _never() -> None: ...


NO_EPIC = """Feature: Synthetic without an epic
  Scenario Outline: outline
    Given a known step
    When nobody defines <n>
    Then twice matched

    Examples:
      | n   |
      | one |
      | two |
"""

WITH_EPIC = """@allure.label.epic:Synthetic
Feature: Synthetic with an epic
  Scenario: keyword typing
    When a known step
    And twice over
"""

# `@given("a known step")` must NOT match `When a known step`; `@step` matches any keyword
EXPECTED = """4 step definitions, 3 scenarios, 8 steps
MISSING   features/a.feature:4 [when] nobody defines one
MISSING   features/a.feature:4 [when] nobody defines two
MISSING   features/nested/b.feature:4 [when] a known step
AMBIGUOUS twice matched -> ['{m}.pytestbdd_stepdef_*_twice.*', '{m}.pytestbdd_stepdef_then_twice matched']
NO EPIC   features/a.feature (CI selects by epic — this feature would never run there)
UNUSED    {m}.pytestbdd_stepdef_when_never used
3 missing, 1 ambiguous, 1 without an epic (1 unused)
"""


@pytest.fixture
def synthetic_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(check_steps, "pytest_plugins", [__name__])
    (tmp_path / "features" / "nested").mkdir(parents=True)
    (tmp_path / "features" / "a.feature").write_text(NO_EPIC)
    (tmp_path / "features" / "nested" / "b.feature").write_text(WITH_EPIC)
    return tmp_path


def test_missing_ambiguous_epicless_and_unused_are_all_reported(
    synthetic_root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check_steps.main(synthetic_root) == 1
    assert capsys.readouterr().out == EXPECTED.format(m=__name__)


def test_unused_definitions_alone_are_not_fatal(synthetic_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (synthetic_root / "features" / "a.feature").unlink()
    (synthetic_root / "features" / "nested" / "b.feature").write_text(
        "@allure.label.epic:Synthetic\nFeature: F\n  Scenario: S\n    Given a known step\n"
    )
    assert check_steps.main(synthetic_root) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "4 step definitions, 1 scenarios, 1 steps"
    assert out[-1] == "OK (3 unused)"


@pytest.mark.parametrize(
    ("feature", "problems"),
    [
        ("@allure.label.epic:X\nFeature: F\n  Scenario: S\n    Given undefined\n", "1 missing, 0 ambiguous, 0 without"),
        ("@allure.label.epic:X\nFeature: F\n  Scenario: S\n    Then twice matched\n", "0 missing, 1 ambiguous, 0 with"),
        ("Feature: F\n  Scenario: S\n    Given a known step\n", "0 missing, 0 ambiguous, 1 without"),
    ],
)
def test_each_problem_kind_alone_fails_the_check(
    synthetic_root: Path, capsys: pytest.CaptureFixture[str], feature: str, problems: str
) -> None:
    (synthetic_root / "features" / "a.feature").unlink()
    (synthetic_root / "features" / "nested" / "b.feature").write_text(feature)
    assert check_steps.main(synthetic_root) == 1
    assert capsys.readouterr().out.splitlines()[-1].startswith(problems)
