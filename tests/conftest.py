"""pytest-bdd wiring: step modules, scenario context fixtures, tag → Allure label hook,
and rate-limit pacing (port of the Before hooks in src/steps/accountsSteps.js)."""

from __future__ import annotations

import time

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
]


# ─── Scenario context ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def global_ctx() -> dict:
    """`_g` store — survives across scenarios for the whole run."""
    return {}


@pytest.fixture
def ctx(global_ctx) -> ScenarioContext:
    """Per-scenario context (local store) layered over the global one."""
    return ScenarioContext(global_ctx)


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


# ─── Rate-limit pacing (server enforces per-IP limits; pace, never retry) ───
#
# JS: Before({tags:'@allure.label.suite:User_Management'}) → sleep 2 s
#     Before({tags:'@allure.label.subSuite:Login'})        → sleep 13 s  (5 login/min)

def _labels(request, label_type: str) -> set[str]:
    return {
        m.args[0]
        for m in request.node.iter_markers("allure_label")
        if m.kwargs.get("label_type") == label_type and m.args
    }


@pytest.fixture(autouse=True)
def _rate_limit_pacing(request):
    if "Login" in _labels(request, "subSuite"):
        time.sleep(13)
    elif "User_Management" in _labels(request, "suite"):
        time.sleep(2)
    yield
