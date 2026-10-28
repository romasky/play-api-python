"""Generic typed assertions over response bodies and headers (lists, ordering, Link header, pages,
streams, tokens). Steps stay one-liners; the logic and the failure messages live here. All paths are
dotted (`get_path`), never substring matches on a serialised body.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Any

import httpx2 as httpx

from play_api.utils import jwt_tools
from play_api.utils.json_path import get_path, has_path


def as_text(value: Any) -> str:
    """JS parity for `String(actual)`: booleans render lowercase, everything else via str()."""
    return str(value).lower() if isinstance(value, bool) else str(value)


def items(body: Any, list_path: str) -> list[Any]:
    value = get_path(body, list_path)
    assert isinstance(value, list), f"'{list_path}' is not a list. Body: {body}"
    return value


_RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})")


def _sort_key(values: list[Any]) -> Callable[[Any], Any] | None:
    """Timestamps compare by instant: Go's RFC3339Nano drops trailing fractional zeros ("…:44Z" is
    …:44.000), so their text order is wrong. Anything else keeps byte order (Python str ordering ==
    the API's binary string order for UTF-8)."""
    if values and all(isinstance(v, str) and _RFC3339.fullmatch(v) for v in values):
        return datetime.fromisoformat
    return None


def assert_sorted(body: Any, list_path: str, key: str, direction: str) -> None:
    assert direction in ("asc", "desc"), f"direction must be asc|desc, got {direction!r}"
    values = [get_path(item, key) for item in items(body, list_path)]
    assert None not in values, f"some '{list_path}' items have no '{key}': {values}"
    expected = sorted(values, key=_sort_key(values), reverse=direction == "desc")
    assert values == expected, f"'{list_path}' not sorted by {key} {direction}: {values}"


def assert_every_item(body: Any, list_path: str, field: str, *, present: bool = True) -> None:
    rows = items(body, list_path)
    assert rows, f"'{list_path}' is empty — nothing to check. Body: {body}"
    offenders = [i for i, row in enumerate(rows) if has_path(row, field) != present]
    verb = "lacks" if present else "exposes"
    assert not offenders, f"{len(offenders)} item(s) of '{list_path}' {verb} '{field}', first index {offenders[0]}"


def assert_every_item_equals(body: Any, list_path: str, field: str, expected: str) -> None:
    rows = items(body, list_path)
    assert rows, f"'{list_path}' is empty — nothing to check. Body: {body}"
    wrong = [get_path(row, field) for row in rows if as_text(get_path(row, field)) != expected]
    assert not wrong, f"{len(wrong)} item(s) of '{list_path}' have '{field}' != '{expected}': {wrong[:5]}"


def assert_total_pages(body: Any) -> None:
    total, per_page, pages = get_path(body, "total"), get_path(body, "per_page"), get_path(body, "total_pages")
    assert isinstance(total, int) and isinstance(per_page, int) and per_page > 0, f"bad pagination fields: {body}"
    assert pages == math.ceil(total / per_page), f"total_pages {pages} != ceil({total} / {per_page})"


def id_range(spec: str) -> list[int]:
    """`1..9` → [1, …, 9]; `25` → [25]; `` → []."""
    if not spec:
        return []
    first, _, last = spec.partition("..")
    return list(range(int(first), int(last or first) + 1))


def link(response: httpx.Response, rel: str) -> str | None:
    """URL of one RFC 8288 `Link` relation, or None (httpx parses the header into `response.links`)."""
    entry = response.links.get(rel)
    return entry.get("url") if entry else None


def assert_plain_text(response: httpx.Response, expected: str) -> None:
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("text/"), f"expected a text body, got Content-Type {content_type!r}"
    assert response.text.strip() == expected, f"body {response.text!r}, expected {expected!r}"


def assert_cloudflare_page(response: httpx.Response, status: int) -> None:
    """Cloudflare replaces the origin body of 502/504/52x — plain text, or an HTML page for a client that accepts
    gzip (httpx always does). Either way it names the status and is NOT the origin's JSON."""
    content_type = response.headers.get("content-type", "")
    assert content_type.startswith("text/"), f"expected a Cloudflare text/HTML page, got {content_type!r}"
    assert re.search(rf"\b{status}\b", response.text), f"page does not name status {status}: {response.text[:200]!r}"
    try:
        json.loads(response.text)
    except ValueError:
        return
    raise AssertionError(f"expected Cloudflare's page, got the origin JSON: {response.text[:200]!r}")


def assert_plan_replays(plan: Sequence[dict[str, Any]], attempt: Callable[[str], httpx.Response]) -> int:
    """The client-side retry loop a flaky sequence exists for: every attempt must answer its PLANNED status.
    Returns the number of attempts until the first 200."""
    for number, planned in enumerate(plan, start=1):
        response = attempt(str(planned["index"]))
        assert response.status_code == planned["status"], (
            f"step {planned['index']} answered {response.status_code}, the plan says {planned['status']}"
        )
        if response.status_code == 200:
            return number
    raise AssertionError(f"no successful step in the plan: {list(plan)}")


def assert_sse_progress(events: Sequence[Any], count: int) -> None:
    """`count` progress events, steps 1..count, each with total == count, the last at 100 %."""
    progress = [e.data for e in events if e.event == "progress"]
    assert [p["step"] for p in progress] == list(range(1, count + 1)), f"progress steps: {progress}"
    assert all(p["total"] == count for p in progress), f"progress totals: {progress}"
    assert progress[-1]["percent"] == 100, f"last progress event: {progress[-1]}"


def assert_sse_done(events: Sequence[Any], status: str, total: int) -> None:
    last = events[-1]
    assert last.event == "done" and last.data == {"status": status, "total": total}, f"last event: {last}"


def assert_jwt_claim(token: str, claim: str, expected: str) -> None:
    _, payload = jwt_tools.parts(token)
    actual = as_text(payload.get(claim))
    assert actual == expected, f"JWT claim '{claim}': expected '{expected}' but got '{actual}'. Payload: {payload}"


def assert_jwt_lifetime(token: str, seconds: int) -> None:
    _, payload = jwt_tools.parts(token)
    lifetime = payload["exp"] - payload["iat"]
    assert lifetime == seconds, f"JWT exp - iat = {lifetime}, expected {seconds}. Payload: {payload}"
