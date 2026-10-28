"""Domain `assert_*` helpers of `play_api.models.responses` — each passes on the right body and fails loudly
(AssertionError naming what is wrong) on the wrong one, the way the `Then` steps call them with `ctx.body(var)`."""

from __future__ import annotations

import json
from typing import Any

import pytest

from play_api.models.responses.admin import assert_admin_stats_consistent
from play_api.models.responses.auth import assert_login_successful
from play_api.models.responses.base import assert_error_code, assert_has_request_id
from play_api.models.responses.bug_reports import assert_criterion, assert_every_criterion
from play_api.models.responses.buggy import assert_cart_total, assert_item_ids, assert_prices_follow_ids
from play_api.models.responses.mail import assert_messages_have_no_full_body
from tests.unit.test_contracts import ADMIN_STATS, BUGGY_ITEMS, ERROR, LOGIN, SCORE

# ─── base: error envelope ────────────────────────────────────────────────


def test_assert_error_code_passes_on_the_expected_code() -> None:
    assert_error_code(ERROR, "VALIDATION_ERROR")


def test_assert_error_code_names_both_codes_on_a_mismatch() -> None:
    with pytest.raises(AssertionError, match="Expected error code 'FORBIDDEN' but got 'VALIDATION_ERROR'"):
        assert_error_code(ERROR, "FORBIDDEN")


@pytest.mark.parametrize("body", ["404 page not found", {"success": False}, {"success": False, "error": "boom"}])
def test_assert_error_code_rejects_a_body_without_the_envelope(body: Any) -> None:
    with pytest.raises(AssertionError, match="ErrorEnvelope contract violated"):
        assert_error_code(body, "NOT_FOUND")


def test_assert_has_request_id_passes_on_a_non_blank_id() -> None:
    assert_has_request_id({**ERROR, "request_id": "req-1"})


@pytest.mark.parametrize("extra", [{}, {"request_id": None}, {"request_id": ""}, {"request_id": "  "}])
def test_assert_has_request_id_fails_when_missing_or_blank(extra: dict[str, Any]) -> None:
    with pytest.raises(AssertionError, match="Expected non-empty 'request_id'"):
        assert_has_request_id({**ERROR, **extra})


# ─── auth ────────────────────────────────────────────────────────────────


def test_assert_login_successful_passes_on_success_true() -> None:
    assert_login_successful(LOGIN)


def test_assert_login_successful_fails_on_success_false() -> None:
    with pytest.raises(AssertionError, match="Expected success=true"):
        assert_login_successful({**LOGIN, "success": False})


def test_assert_login_successful_fails_when_the_token_is_missing() -> None:
    with pytest.raises(AssertionError, match=r"LoginResponse contract violated(.|\n)*access_token"):
        assert_login_successful({k: v for k, v in LOGIN.items() if k != "access_token"})


# ─── admin ───────────────────────────────────────────────────────────────


def _stats(admin: int = 1, moderator: int = 0, user: int = 2, *, total: int = 3, active: int = 1) -> dict[str, Any]:
    roles = {"admin": admin, "moderator": moderator, "user": user}
    return {**ADMIN_STATS, "total": total, "by_role": roles, "with_active_token": active}


@pytest.mark.parametrize(
    "body",
    [ADMIN_STATS, _stats(active=0), _stats(active=3), _stats(1, 1, 1, total=3), _stats(1, 0, 0, total=1, active=1)],
)
def test_assert_admin_stats_consistent_passes_when_the_parts_add_up(body: dict[str, Any]) -> None:
    assert_admin_stats_consistent(body)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (_stats(total=4), "by_role does not sum to total"),
        (_stats(total=2), "by_role does not sum to total"),
        (_stats(active=-1), "with_active_token out of range"),
        (_stats(active=4), "with_active_token out of range"),
        (_stats(0, 1, 2), "expected by_role.admin >= 1"),
        ({**ADMIN_STATS, "total": "3"}, "AdminStatsResponse contract violated"),
    ],
)
def test_assert_admin_stats_consistent_fails_on_inconsistent_parts(body: dict[str, Any], message: str) -> None:
    with pytest.raises(AssertionError, match=message):
        assert_admin_stats_consistent(body)


# ─── bug reports ─────────────────────────────────────────────────────────

CRITERIA = ("steps", "endpoint", "expected_actual", "severity", "title")


def _report(*feedback: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "score": {**SCORE, "feedback": list(feedback)}}


def _passed(criterion: str) -> dict[str, Any]:
    return {"criterion": criterion, "ok": True, "key": f"{criterion}.ok"}


def _failed(criterion: str) -> dict[str, Any]:
    return {"criterion": criterion, "ok": False, "key": f"{criterion}.fail", "params": {"min": "2"}}


ALL_PASSED = _report(*map(_passed, CRITERIA))
ALL_FAILED = _report(*map(_failed, CRITERIA))
MIXED = _report(_passed("steps"), _failed("title"))


@pytest.mark.parametrize(("criterion", "ok"), [("steps", True), ("title", False)])
def test_assert_criterion_passes_when_the_verdict_matches(criterion: str, ok: bool) -> None:
    assert_criterion(MIXED, criterion, ok)


@pytest.mark.parametrize(("criterion", "ok"), [("steps", False), ("title", True)])
def test_assert_criterion_fails_on_the_opposite_verdict(criterion: str, ok: bool) -> None:
    with pytest.raises(AssertionError, match=f"criterion '{criterion}' ok={not ok}, expected {ok}"):
        assert_criterion(MIXED, criterion, ok)


def test_assert_criterion_fails_when_the_criterion_is_absent() -> None:
    with pytest.raises(AssertionError, match="no feedback for criterion 'severity'"):
        assert_criterion(MIXED, "severity", True)


@pytest.mark.parametrize("body", ["<!DOCTYPE html>", {"success": True}, {"score": {"total": 1}}])
def test_assert_criterion_fails_without_a_score(body: Any) -> None:
    with pytest.raises(AssertionError, match="Score contract violated"):
        assert_criterion(body, "steps", True)


@pytest.mark.parametrize(("body", "ok"), [(ALL_PASSED, True), (ALL_FAILED, False)])
def test_assert_every_criterion_passes_when_all_five_share_the_verdict(body: dict[str, Any], ok: bool) -> None:
    assert_every_criterion(body, ok)


@pytest.mark.parametrize(
    ("body", "ok", "message"),
    [
        (_report(*map(_passed, CRITERIA[:4])), True, "expected 5 feedback items, got 4"),
        (_report(*map(_passed, (*CRITERIA, "extra"))), True, "expected 5 feedback items, got 6"),
        (ALL_PASSED, False, r"criteria not ok=False: \['steps', 'endpoint', 'expected_actual', 'severity', 'title'\]"),
        (_report(*map(_passed, CRITERIA[:4]), _failed("title")), True, r"criteria not ok=True: \['title'\]"),
        (
            _report(*map(_passed, CRITERIA[:4]), {**_passed("title"), "params": {}}),
            True,
            r"unexpected params presence: \['title'\]",
        ),
        (
            _report(*map(_failed, CRITERIA[1:]), {"criterion": "steps", "ok": False, "key": "k"}),
            False,
            r"unexpected params presence: \['steps'\]",
        ),
    ],
)
def test_assert_every_criterion_fails_on_a_count_verdict_or_params_mismatch(
    body: dict[str, Any], ok: bool, message: str
) -> None:
    with pytest.raises(AssertionError, match=message):
        assert_every_criterion(body, ok)


# ─── buggy ───────────────────────────────────────────────────────────────


def _items(*priced: tuple[int, float]) -> dict[str, Any]:
    rows = [{"id": i, "sku": f"S{i}", "name": "n", "price": price} for i, price in priced]
    return {**BUGGY_ITEMS, "items": rows}


def test_assert_item_ids_passes_on_the_exact_ids_in_order() -> None:
    assert_item_ids(_items((1, 1.25), (2, 2.5)), [1, 2])
    assert_item_ids(_items(), [])


@pytest.mark.parametrize(
    ("body", "expected", "message"),
    [
        (_items((1, 1.25), (2, 2.5)), [2, 1], r"item ids \[1, 2\], expected \[2, 1\]"),
        (_items((1, 1.25)), [1, 2], r"item ids \[1\], expected \[1, 2\]"),
        (_items((1, 1.25)), [], r"item ids \[1\], expected \(none\)"),
    ],
)
def test_assert_item_ids_fails_on_other_ids(body: dict[str, Any], expected: list[int], message: str) -> None:
    with pytest.raises(AssertionError, match=message):
        assert_item_ids(body, expected)


@pytest.mark.parametrize(
    "body",
    [_items((1, 1.25), (2, 2.5), (3, 3.75), (7, 8.75)), _items((4, 5)), _items((0, 0.0)), _items()],
)
def test_assert_prices_follow_ids_passes_on_id_times_one_and_a_quarter(body: dict[str, Any]) -> None:
    assert_prices_follow_ids(body)


@pytest.mark.parametrize("body", [_items((1, 1.25), (3, 3.76)), _items((2, 2.0)), _items((5, 6.24))])
def test_assert_prices_follow_ids_names_the_wrong_items(body: dict[str, Any]) -> None:
    with pytest.raises(AssertionError, match=r"items with an unexpected price: .*id=") as caught:
        assert_prices_follow_ids(body)
    assert "id=1," not in str(caught.value)  # only the offenders are listed


@pytest.mark.parametrize(
    ("raw", "expected"), [('{"total": 0.30}', "0.3"), ('{"total": 0.3}', "0.30"), ('{"total": 15}', "15.00")]
)
def test_assert_cart_total_compares_exact_decimals(raw: str, expected: str) -> None:
    assert_cart_total(raw, expected)


@pytest.mark.parametrize(("total", "expected"), [(0.30000000000000004, "0.3"), (0.31, "0.3"), (14.99, "15")])
def test_assert_cart_total_fails_on_any_other_amount(total: float, expected: str) -> None:
    with pytest.raises(AssertionError, match=f"cart total .*, expected {expected}"):
        assert_cart_total(json.dumps({"total": total}), expected)


# ─── mail ────────────────────────────────────────────────────────────────

PREVIEW = {"id": "m", "body_preview": "hi"}


def test_assert_messages_have_no_full_body_passes_on_preview_only_items() -> None:
    assert_messages_have_no_full_body({"messages": [PREVIEW, {**PREVIEW, "id": "n"}], "count": 2})


@pytest.mark.parametrize(
    ("item", "message"),
    [
        ({"id": "m"}, "lacks 'body_preview'"),
        ({**PREVIEW, "body": "full"}, "exposes 'body'"),
        ({**PREVIEW, "html_body": None}, "exposes 'html_body'"),
        ({**PREVIEW, "headers": {}}, "exposes 'headers'"),
    ],
)
def test_assert_messages_have_no_full_body_fails_on_a_leaky_item(item: dict[str, Any], message: str) -> None:
    with pytest.raises(AssertionError, match=message):
        assert_messages_have_no_full_body({"messages": [PREVIEW, item], "count": 2})


def test_assert_messages_have_no_full_body_fails_on_an_empty_list() -> None:
    with pytest.raises(AssertionError, match="'messages' is empty"):
        assert_messages_have_no_full_body({"messages": [], "count": 0})
