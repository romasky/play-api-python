"""pytest-bdd wiring: step modules, scenario context fixtures (with teardown), tag → Allure label hook,
and `--epic` selection for the CI matrix. Rate-limit pacing is per endpoint, in `play_api.pacing`."""

from __future__ import annotations

import warnings
from collections.abc import Iterator
from typing import Any

import pytest

from play_api.context import ScenarioContext

# Every step module is a pytest plugin so its @given/@when/@then are visible to all features.
pytest_plugins = [
    "tests.steps.common_steps",
    "tests.steps.accounts_steps",
    "tests.steps.mail_steps",
    "tests.steps.health_steps",
    "tests.steps.basic_auth_steps",
    "tests.steps.options_steps",
    "tests.steps.admin_steps",
]


# ─── Scenario context ──────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def global_ctx() -> dict[str, Any]:
    """`_g` store — survives across scenarios for the whole run."""
    return {}


@pytest.fixture
def ctx(global_ctx: dict[str, Any]) -> Iterator[ScenarioContext]:
    """Per-scenario context (local store) layered over the global one; runs `ctx.defer` actions after."""
    context = ScenarioContext(global_ctx)
    yield context
    for error in context.run_cleanups():
        warnings.warn(f"scenario cleanup failed: {error!r}", stacklevel=1)


# ─── Gherkin tags → pytest markers / Allure labels ─────────────────────────
#
# pytest-bdd turns every tag into `pytest.mark.<tag>`; allure-pytest-bdd only reads
# `allure_label` markers and reports the rest as plain Allure tags. The JS/Java projects
# use Cucumber-style label tags, so translate them here:
#   @allure.label.epic:User_Lifecycle   → allure_label("User_Lifecycle", label_type="epic")
#   @allure.label.severity:critical     → allure_label("critical", label_type="severity")

ALLURE_LABEL_PREFIX = "allure.label."


def pytest_bdd_apply_tag(tag: str, function):
    if tag.startswith(ALLURE_LABEL_PREFIX):
        name, _, value = tag.removeprefix(ALLURE_LABEL_PREFIX).partition(":")
        return pytest.mark.allure_label(value, label_type=name)(function)
    return None  # default: pytest.mark.<tag>


def _labels(node: pytest.Item, label_type: str) -> set[str]:
    return {m.args[0] for m in node.iter_markers("allure_label") if m.kwargs.get("label_type") == label_type and m.args}


# ─── --epic: run one Allure epic (CI matrix: one runner = one IP = its own rate-limit buckets) ───


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--epic", action="append", default=[], help="only scenarios whose Allure epic is one of these (repeatable)"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    epics = set(config.getoption("--epic"))
    if not epics:
        return
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        (selected if _labels(item, "epic") & epics else deselected).append(item)
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected
