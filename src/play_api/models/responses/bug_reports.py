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
