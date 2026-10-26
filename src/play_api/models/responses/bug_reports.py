"""/bug-reports contracts. Anonymous submissions answer 200 without report_id / expires_at."""

from __future__ import annotations

from typing import Any

from play_api.models.responses.base import Contract, entry


class ScoreFeedback(Contract):
    criterion: str
    ok: bool
    key: str
    params: dict[str, str] | None = None  # present only on failed criteria


class Score(Contract):
    total: int
    max: int
    breakdown: dict[str, int]
    feedback: list[ScoreFeedback]


class BugReportSubmitted(Contract):
    success: bool
    bug_id: str
    owner: str  # "user" | "anonymous"
    saved: bool
    created_at: str
    score: Score
    report_id: str | None = None  # authenticated only
    expires_at: str | None = None  # authenticated only


class BugReportsList(Contract):
    success: bool
    user_id: str
    total: int
    returned: int
    reports: list[dict[str, Any]]


class BugReportDetail(Contract):
    success: bool
    report_id: str
    bug_id: str
    title: str
    steps: list[str]
    expected: str
    actual: str
    severity: str
    score: Score
    created_at: str
    expires_at: str


CONTRACTS_2XX = (
    entry("POST", r"/bug-reports", BugReportSubmitted),
    entry("GET", r"/bug-reports", BugReportsList),
    entry("GET", r"/bug-reports/[^/]+", BugReportDetail),
)


def _feedback(body: Any) -> list[ScoreFeedback]:
    return Score.check(body.get("score") if isinstance(body, dict) else None).feedback


def assert_criterion(body: Any, criterion: str, ok: bool) -> None:
    item = next((f for f in _feedback(body) if f.criterion == criterion), None)
    assert item is not None, f"no feedback for criterion '{criterion}'. Body: {body}"
    assert item.ok is ok, f"criterion '{criterion}' ok={item.ok}, expected {ok}: {item}"


def assert_every_criterion(body: Any, ok: bool) -> None:
    """All five criteria share the verdict; a failed one explains itself with `params`, a passed one has none."""
    feedback = _feedback(body)
    assert len(feedback) == 5, f"expected 5 feedback items, got {len(feedback)}"
    wrong = [f.criterion for f in feedback if f.ok is not ok]
    assert not wrong, f"criteria not ok={ok}: {wrong}"
    leaky = [f.criterion for f in feedback if (f.params is not None) == ok]
    assert not leaky, f"criteria with unexpected params presence: {leaky}"
