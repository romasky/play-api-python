from __future__ import annotations

import base64
import json
import re
from typing import Any

import httpx2 as httpx
import pytest

from play_api import assertions as a
from play_api.services.realtime import SseEvent

REQUEST = httpx.Request("GET", "https://x/api/v1/users/list")


def response(status: int = 200, *, text: str = "", headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, text=text, headers=headers or {}, request=REQUEST)


def token(payload: dict[str, Any]) -> str:
    def seg(obj: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).rstrip(b"=").decode()

    return f"{seg({'alg': 'HS256', 'typ': 'JWT'})}.{seg(payload)}.sig"


# ─── as_text / items ───


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, "true"), (False, "false"), (None, "None"), (1, "1"), ("Abc", "Abc"), (1.5, "1.5")],
)
def test_as_text_lowercases_only_booleans(value: object, expected: str) -> None:
    assert a.as_text(value) == expected


def test_items_returns_the_list_or_fails() -> None:
    assert a.items({"data": [1, 2]}, "data") == [1, 2]
    assert a.items({"data": []}, "data") == []
    with pytest.raises(AssertionError, match="'data' is not a list"):
        a.items({"data": {"x": 1}}, "data")
    with pytest.raises(AssertionError, match="'missing' is not a list"):
        a.items({}, "missing")


# ─── assert_sorted ───

SORTED_BODY = {"data": [{"u": {"n": "a"}}, {"u": {"n": "b"}}, {"u": {"n": "b"}}, {"u": {"n": "c"}}]}


def test_assert_sorted_accepts_the_right_direction_with_ties() -> None:
    a.assert_sorted(SORTED_BODY, "data", "u.n", "asc")
    a.assert_sorted({"data": list(reversed(SORTED_BODY["data"]))}, "data", "u.n", "desc")
    a.assert_sorted({"data": []}, "data", "u.n", "desc")


def test_assert_sorted_rejects_the_wrong_direction() -> None:
    with pytest.raises(AssertionError, match=r"'data' not sorted by u.n desc: \['a', 'b', 'b', 'c'\]"):
        a.assert_sorted(SORTED_BODY, "data", "u.n", "desc")
    with pytest.raises(AssertionError, match=r"not sorted by u\.n asc"):
        a.assert_sorted({"data": list(reversed(SORTED_BODY["data"]))}, "data", "u.n", "asc")


def test_assert_sorted_uses_byte_order() -> None:
    a.assert_sorted({"data": [{"n": "Z"}, {"n": "a"}]}, "data", "n", "asc")  # uppercase sorts first
    with pytest.raises(AssertionError):
        a.assert_sorted({"data": [{"n": "a"}, {"n": "Z"}]}, "data", "n", "asc")


def test_assert_sorted_rejects_missing_keys_and_bad_direction() -> None:
    with pytest.raises(AssertionError, match="some 'data' items have no 'n'"):
        a.assert_sorted({"data": [{"n": "a"}, {}]}, "data", "n", "asc")
    with pytest.raises(AssertionError, match=re.escape("direction must be asc|desc, got 'up'")):
        a.assert_sorted(SORTED_BODY, "data", "u.n", "up")


# ─── assert_every_item / assert_every_item_equals ───


def test_assert_every_item_present() -> None:
    a.assert_every_item({"d": [{"id": 1}, {"id": None}]}, "d", "id")
    with pytest.raises(AssertionError, match="1 item\\(s\\) of 'd' lacks 'id', first index 1"):
        a.assert_every_item({"d": [{"id": 1}, {}]}, "d", "id")


def test_assert_every_item_counts_offenders_and_reports_the_first() -> None:
    with pytest.raises(AssertionError, match="2 item\\(s\\) of 'd' lacks 'id', first index 0"):
        a.assert_every_item({"d": [{}, {"id": 1}, {}]}, "d", "id")


def test_assert_every_item_absent() -> None:
    a.assert_every_item({"d": [{"x": 1}, {}]}, "d", "metadata.last_login_ip", present=False)
    with pytest.raises(AssertionError, match="1 item\\(s\\) of 'd' exposes 'secret', first index 1"):
        a.assert_every_item({"d": [{}, {"secret": None}]}, "d", "secret", present=False)


def test_assert_every_item_rejects_an_empty_list() -> None:
    with pytest.raises(AssertionError, match="'d' is empty"):
        a.assert_every_item({"d": []}, "d", "id")


def test_assert_every_item_equals_compares_as_text() -> None:
    a.assert_every_item_equals({"d": [{"active": True}, {"active": True}]}, "d", "active", "true")
    a.assert_every_item_equals({"d": [{"n": 3}]}, "d", "n", "3")
    with pytest.raises(AssertionError, match=r"1 item\(s\) of 'd' have 'active' != 'true': \[False\]"):
        a.assert_every_item_equals({"d": [{"active": True}, {"active": False}]}, "d", "active", "true")
    with pytest.raises(AssertionError, match="'d' is empty"):
        a.assert_every_item_equals({"d": []}, "d", "active", "true")


def test_assert_every_item_equals_shows_at_most_five_offenders() -> None:
    body = {"d": [{"n": i} for i in range(7)]}
    with pytest.raises(AssertionError, match=r"7 item\(s\) of 'd' have 'n' != 'x': \[0, 1, 2, 3, 4\]$"):
        a.assert_every_item_equals(body, "d", "n", "x")


# ─── assert_total_pages ───


@pytest.mark.parametrize(
    ("total", "per_page", "pages"),
    [(0, 10, 0), (10, 10, 1), (11, 10, 2), (1, 100, 1), (401, 20, 21), (5, 1, 5)],  # limit=1 is a valid page size
)
def test_assert_total_pages_accepts_the_ceiling(total: int, per_page: int, pages: int) -> None:
    a.assert_total_pages({"total": total, "per_page": per_page, "total_pages": pages})


@pytest.mark.parametrize(("total", "per_page", "pages"), [(11, 10, 1), (10, 10, 2), (0, 10, 1)])
def test_assert_total_pages_rejects_a_wrong_count(total: int, per_page: int, pages: int) -> None:
    with pytest.raises(AssertionError, match=f"total_pages {pages} != ceil\\({total} / {per_page}\\)"):
        a.assert_total_pages({"total": total, "per_page": per_page, "total_pages": pages})


@pytest.mark.parametrize(
    "body",
    [
        {"total": "10", "per_page": 10, "total_pages": 1},
        {"total": 10, "per_page": "10", "total_pages": 1},
        {"total": 10, "per_page": 0, "total_pages": 1},
        {"total": 10, "per_page": -5, "total_pages": -2},
        {"per_page": 10, "total_pages": 0},
    ],
)
def test_assert_total_pages_rejects_bad_fields(body: dict[str, Any]) -> None:
    with pytest.raises(AssertionError, match="bad pagination fields"):
        a.assert_total_pages(body)


# ─── id_range / link ───


@pytest.mark.parametrize(
    ("spec", "expected"),
    [("1..3", [1, 2, 3]), ("25", [25]), ("", []), ("7..7", [7]), ("10..12", [10, 11, 12])],
)
def test_id_range(spec: str, expected: list[int]) -> None:
    assert a.id_range(spec) == expected


def test_link_returns_the_relation_url_or_none() -> None:
    res = response(headers={"link": '</api/v1/users/list?page=2&limit=3>; rel="next", </x?page=1>; rel="first"'})
    assert a.link(res, "next") == "/api/v1/users/list?page=2&limit=3"
    assert a.link(res, "first") == "/x?page=1"
    assert a.link(res, "prev") is None
    assert a.link(response(), "next") is None


# ─── assert_plain_text / assert_cloudflare_page ───


def test_assert_plain_text() -> None:
    a.assert_plain_text(
        response(404, text="404 page not found\n", headers={"content-type": "text/plain"}), "404 page not found"
    )
    with pytest.raises(AssertionError, match="expected a text body, got Content-Type 'application/json'"):
        a.assert_plain_text(response(text="ok", headers={"content-type": "application/json"}), "ok")
    with pytest.raises(AssertionError, match="expected a text body, got Content-Type ''"):
        a.assert_plain_text(httpx.Response(200, content=b"ok", request=REQUEST), "ok")
    with pytest.raises(AssertionError, match="body 'other', expected 'ok'"):
        a.assert_plain_text(response(text="other", headers={"content-type": "text/plain"}), "ok")


def test_assert_cloudflare_page_accepts_text_and_html_naming_the_status() -> None:
    a.assert_cloudflare_page(response(502, text="error code: 502", headers={"content-type": "text/plain"}), 502)
    html = "<!DOCTYPE html><title>Gateway time-out | 504</title>"
    a.assert_cloudflare_page(response(504, text=html, headers={"content-type": "text/html; charset=UTF-8"}), 504)


def test_assert_cloudflare_page_rejects_json_content_type() -> None:
    with pytest.raises(AssertionError, match="expected a Cloudflare text/HTML page, got 'application/json'"):
        a.assert_cloudflare_page(response(502, text='{"code": 502}', headers={"content-type": "application/json"}), 502)


def test_assert_cloudflare_page_needs_the_status_as_a_whole_word() -> None:
    with pytest.raises(AssertionError, match="page does not name status 502"):
        a.assert_cloudflare_page(response(502, text="error code: 5021", headers={"content-type": "text/plain"}), 502)
    with pytest.raises(AssertionError, match="page does not name status 504"):
        a.assert_cloudflare_page(response(504, text="error code: 502", headers={"content-type": "text/plain"}), 504)


def test_assert_cloudflare_page_rejects_origin_json_in_a_text_body() -> None:
    with pytest.raises(AssertionError, match="got the origin JSON"):
        a.assert_cloudflare_page(response(502, text='{"status": 502}', headers={"content-type": "text/plain"}), 502)


# ─── assert_plan_replays ───


def plan_runner(statuses: dict[str, int]) -> tuple[list[str], Any]:
    calls: list[str] = []

    def attempt(index: str) -> httpx.Response:
        calls.append(index)
        return response(statuses[index])

    return calls, attempt


def test_assert_plan_replays_returns_attempts_until_the_first_200() -> None:
    plan = [
        {"index": 0, "status": 503},
        {"index": 1, "status": 500},
        {"index": 2, "status": 200},
        {"index": 3, "status": 200},
    ]
    calls, attempt = plan_runner({"0": 503, "1": 500, "2": 200, "3": 200})
    assert a.assert_plan_replays(plan, attempt) == 3
    assert calls == ["0", "1", "2"]


def test_assert_plan_replays_first_attempt_success() -> None:
    _, attempt = plan_runner({"0": 200})
    assert a.assert_plan_replays([{"index": 0, "status": 200}], attempt) == 1


def test_assert_plan_replays_rejects_an_off_plan_status() -> None:
    calls, attempt = plan_runner({"0": 503, "1": 200})
    with pytest.raises(AssertionError, match="step 1 answered 200, the plan says 500"):
        a.assert_plan_replays([{"index": 0, "status": 503}, {"index": 1, "status": 500}], attempt)
    assert calls == ["0", "1"]


def test_assert_plan_replays_rejects_a_plan_without_success() -> None:
    calls, attempt = plan_runner({"0": 503})
    with pytest.raises(AssertionError, match="no successful step in the plan"):
        a.assert_plan_replays([{"index": 0, "status": 503}], attempt)
    assert calls == ["0"]


# ─── SSE ───


def progress(step: int, total: int, percent: int) -> SseEvent:
    return SseEvent("progress", {"step": step, "total": total, "percent": percent})


GOOD_STREAM = [
    SseEvent("message", {"hello": True}),
    progress(1, 3, 33),
    progress(2, 3, 66),
    progress(3, 3, 100),
    SseEvent("done", {"status": "complete", "total": 3}),
]


def test_assert_sse_progress_accepts_a_complete_stream() -> None:
    a.assert_sse_progress(GOOD_STREAM, 3)


@pytest.mark.parametrize(
    ("events", "message"),
    [
        ([progress(1, 3, 33), progress(3, 3, 100)], "progress steps"),
        ([progress(1, 3, 33), progress(2, 3, 66)], "progress steps"),
        ([progress(1, 3, 33), progress(2, 2, 66), progress(3, 3, 100)], "progress totals"),
        ([progress(1, 3, 33), progress(2, 3, 66), progress(3, 3, 99)], "last progress event"),
    ],
)
def test_assert_sse_progress_rejects_a_broken_stream(events: list[SseEvent], message: str) -> None:
    with pytest.raises(AssertionError, match=message):
        a.assert_sse_progress(events, 3)


def test_a_short_last_progress_event_is_named_in_the_failure() -> None:
    stream = [progress(1, 3, 33), progress(2, 3, 66), progress(3, 3, 99)]
    with pytest.raises(AssertionError) as failure:
        a.assert_sse_progress(stream, 3)
    assert str(failure.value) == "last progress event: {'step': 3, 'total': 3, 'percent': 99}"


def test_assert_sse_done() -> None:
    a.assert_sse_done(GOOD_STREAM, "complete", 3)
    with pytest.raises(AssertionError, match="last event"):
        a.assert_sse_done(GOOD_STREAM, "complete", 4)
    with pytest.raises(AssertionError, match="last event"):
        a.assert_sse_done(GOOD_STREAM, "failed", 3)
    with pytest.raises(AssertionError, match="last event"):
        a.assert_sse_done([*GOOD_STREAM[:-1], SseEvent("message", {"status": "complete", "total": 3})], "complete", 3)


# ─── JWT ───


def test_assert_jwt_claim_compares_as_text() -> None:
    jwt = token({"sub": "u1", "admin": False, "iat": 100, "exp": 1000})
    a.assert_jwt_claim(jwt, "sub", "u1")
    a.assert_jwt_claim(jwt, "admin", "false")
    a.assert_jwt_claim(jwt, "exp", "1000")
    with pytest.raises(AssertionError, match="JWT claim 'sub': expected 'u2' but got 'u1'"):
        a.assert_jwt_claim(jwt, "sub", "u2")
    with pytest.raises(AssertionError, match="JWT claim 'role': expected 'admin' but got 'None'"):
        a.assert_jwt_claim(jwt, "role", "admin")


def test_assert_jwt_lifetime() -> None:
    jwt = token({"iat": 1_700_000_000, "exp": 1_700_000_900})
    a.assert_jwt_lifetime(jwt, 900)
    with pytest.raises(AssertionError, match="JWT exp - iat = 900, expected 1"):
        a.assert_jwt_lifetime(jwt, 1)
