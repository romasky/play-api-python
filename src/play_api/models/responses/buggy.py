"""/buggy/* contracts — the shapes are correct; the VALUES are deliberately wrong (pinned by the helpers below)."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from play_api.models.responses.base import Contract, entry


class BugEntry(Contract):
    bug_id: str
    method: str
    path: str
    title: str
    description: str
    expected: str


class BuggyCatalogResponse(Contract):
    success: bool
    total: int
    bugs: list[BugEntry]


class BuggyItem(Contract):
    id: int
    sku: str
    name: str
    price: float


class BuggyItemsResponse(Contract):
    success: bool
    bug_id: str
    page: int
    per_page: int
    total: int
    items: list[BuggyItem]


class CartTotalResponse(Contract):
    success: bool
    bug_id: str
    items_count: int
    currency: str
    total: float


class ScheduleResponse(Contract):
    success: bool
    bug_id: str
    requested_date: str
    tz: str
    event_local: str
    event_start: str
    event_start_utc: str


CONTRACTS_2XX = (
    entry("GET", r"/buggy", BuggyCatalogResponse),
    entry("GET", r"/buggy/items", BuggyItemsResponse),
    entry("POST", r"/buggy/cart/total", CartTotalResponse),
    entry("GET", r"/buggy/schedule", ScheduleResponse),
)


def assert_item_ids(body: Any, expected: list[int]) -> None:
    actual = [item.id for item in BuggyItemsResponse.check(body).items]
    assert actual == expected, f"item ids {actual}, expected {expected or '(none)'}"


def assert_prices_follow_ids(body: Any) -> None:
    """Every catalogue item costs id × 1.25 (compared as Decimal, never as binary floats)."""
    items = BuggyItemsResponse.check(body).items
    wrong = [i for i in items if Decimal(str(i.price)) != Decimal(i.id) * Decimal("1.25")]
    assert not wrong, f"items with an unexpected price: {wrong}"


def assert_cart_total(raw_body: str, expected: str) -> None:
    """Parse the RAW text with Decimal so "0.30" is compared as exact cents."""
    total = json.loads(raw_body, parse_float=Decimal)["total"]
    assert Decimal(total) == Decimal(expected), f"cart total {total}, expected {expected}"
