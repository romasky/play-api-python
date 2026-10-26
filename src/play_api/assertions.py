"""Generic typed assertions over response bodies and headers (lists, ordering, Link header).

Steps stay one-liners; the logic and the failure messages live here. All paths are dotted
(`get_path`), never substring matches on the serialised body.
"""

from __future__ import annotations

import math
from typing import Any

import httpx2 as httpx

from play_api.utils.json_path import get_path, has_path


def items(body: Any, list_path: str) -> list[Any]:
    value = get_path(body, list_path)
    assert isinstance(value, list), f"'{list_path}' is not a list. Body: {body}"
    return value


def assert_sorted(body: Any, list_path: str, key: str, direction: str) -> None:
    """Byte-order check (Python str ordering == the API's binary string order for UTF-8)."""
    assert direction in ("asc", "desc"), f"direction must be asc|desc, got {direction!r}"
    values = [get_path(item, key) for item in items(body, list_path)]
    assert None not in values, f"some '{list_path}' items have no '{key}': {values}"
    expected = sorted(values, reverse=direction == "desc")
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
    wrong = [get_path(row, field) for row in rows if render(get_path(row, field)) != expected]
    assert not wrong, f"{len(wrong)} item(s) of '{list_path}' have '{field}' != '{expected}': {wrong[:5]}"


def assert_total_pages(body: Any) -> None:
    total, per_page, pages = get_path(body, "total"), get_path(body, "per_page"), get_path(body, "total_pages")
    assert isinstance(total, int) and isinstance(per_page, int) and per_page > 0, f"bad pagination fields: {body}"
    assert pages == math.ceil(total / per_page), f"total_pages {pages} != ceil({total} / {per_page})"


def link(response: httpx.Response, rel: str) -> str | None:
    """URL of one RFC 8288 `Link` relation, or None (httpx parses the header into `response.links`)."""
    entry = response.links.get(rel)
    return entry.get("url") if entry else None


def render(value: Any) -> str:
    """JS parity for `String(actual)`: booleans render lowercase, everything else via str()."""
    return str(value).lower() if isinstance(value, bool) else str(value)
