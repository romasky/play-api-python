"""/challenges/* contracts."""

from __future__ import annotations

from typing import Any

from play_api.models.responses.base import Contract, entry


class Challenge(Contract):
    id: str
    title: str
    description: str
    category: str
    difficulty: str
    points: int
    hint_count: int
    params: list[Any]


class ChallengesResponse(Contract):
    success: bool
    total: int
    challenges: list[Challenge]


class ProgressResponse(Contract):
    success: bool
    user_id: str
    solved_count: int
    total_challenges: int
    total_points: int
    solved: list[dict[str, Any]]
    hints: list[dict[str, Any]]


class HintLevel(Contract):
    level: int
    kind: str


class HintsResponse(Contract):
    success: bool
    challenge_id: str
    hint_count: int
    levels: list[HintLevel]


class RevealResponse(Contract):
    success: bool
    challenge_id: str
    level: int
    kind: str
    hint: str
    revealed_count: int
    hint_count: int
    has_more: bool
    revealed: list[dict[str, Any]]


class StartResponse(Contract):
    """201 fresh attempt carries target incl. access_token; a repeat start (200) omits the token,
    a missing sandbox (200) has target_missing instead of target, a solved challenge has solved_at."""

    success: bool
    challenge_id: str
    already_solved: bool
    attempt_id: str
    status: str


class VerifyResponse(Contract):
    success: bool
    challenge_id: str
    solved: bool
    already_solved: bool
    points_awarded: int
    attempt_id: str


CONTRACTS_2XX = (
    entry("GET", r"/challenges", ChallengesResponse),
    entry("GET", r"/challenges/progress", ProgressResponse),
    entry("GET", r"/challenges/[^/]+/hints", HintsResponse),
    entry("POST", r"/challenges/[^/]+/hints/reveal", RevealResponse),
    entry("POST", r"/challenges/[^/]+/start", StartResponse),
    entry("POST", r"/challenges/[^/]+/verify", VerifyResponse),
)
