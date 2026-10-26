"""/buggy/* contracts — the shapes are correct; the VALUES are deliberately wrong (asserted in steps)."""

from __future__ import annotations

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
