"""/buggy/* steps. The bugs are permanent and deterministic, so the scenarios pin the WRONG values —
a fix on the server side would (rightly) turn them red."""

from __future__ import annotations

import json
from decimal import Decimal

from pytest_bdd import parsers, then, when

from play_api.services import buggy
from play_api.utils.gherkin import query_pairs, raw_json
from play_api.utils.json_path import get_path
from tests.steps.parsing import quoted


def _cart(spec: str) -> dict[str, list[dict[str, object]]]:
    """`10x2, 5.50x3` → {"items": [{"price": 10, "qty": 2}, {"price": 5.5, "qty": 3}]}"""
    items = []
    for position in spec.split(","):
        price, qty = position.strip().split("x")
        items.append({"price": json.loads(price), "qty": int(qty)})
    return {"items": items}


def _ids(spec: str) -> list[int]:
    """`1..9` → [1..9], `25` → [25], `` → []"""
    if not spec:
        return []
    if ".." in spec:
        first, last = spec.split("..")
        return list(range(int(first), int(last) + 1))
    return [int(spec)]


@when(parsers.parse('Get buggy catalog and save response as "{var}"'))
def get_catalog(ctx, var):
    ctx.save(var, buggy.catalog())


@when(quoted('Get buggy items with query "{query}" and save response as "{var}"'))
def get_items(ctx, query, var):
    ctx.save(var, buggy.items(query_pairs(query)))


@then(quoted('Assert item ids are "{ids}" in response "{var}"'))
def assert_item_ids(ctx, ids, var):
    actual = [item["id"] for item in get_path(ctx.body(var), "items")]
    assert actual == _ids(ids), f"item ids {actual}, expected {ids or '(none)'}"


@then(parsers.parse('Assert every buggy item costs its id times 1.25 in response "{var}"'))
def assert_item_prices(ctx, var):
    wrong = [
        i for i in get_path(ctx.body(var), "items") if Decimal(str(i["price"])) != Decimal(i["id"]) * Decimal("1.25")
    ]
    assert not wrong, f"items with an unexpected price: {wrong}"


@when(quoted('Post buggy cart with items "{spec}" and save response as "{var}"'))
def post_cart(ctx, spec, var):
    ctx.save(var, buggy.cart_total(_cart(spec)))


@when(parsers.parse('Post buggy cart with {count:d} items and save response as "{var}"'))
def post_cart_many(ctx, count, var):
    ctx.save(var, buggy.cart_total({"items": [{"price": 1, "qty": 1}] * count}))


@when(parsers.parse('Post buggy cart with raw body "{raw}" and save response as "{var}"'))
def post_cart_raw(ctx, raw, var):
    ctx.save(var, buggy.cart_total(raw_json(raw)))


@then(quoted('Assert cart total is "{amount}" in response "{var}"'))
def assert_cart_total(ctx, amount, var):
    # parse the raw text with Decimal: compare exact cents, never binary floats
    total = json.loads(ctx.response(var).text, parse_float=Decimal)["total"]
    assert Decimal(total) == Decimal(amount), f"cart total {total}, expected {amount}"


@when(quoted('Get buggy schedule with query "{query}" and save response as "{var}"'))
def get_schedule(ctx, query, var):
    ctx.save(var, buggy.schedule(query_pairs(query)))
