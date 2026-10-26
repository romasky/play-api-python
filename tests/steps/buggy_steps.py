"""/buggy/* steps. The bugs are permanent and deterministic, so the scenarios pin the WRONG values —
a fix on the server side would (rightly) turn them red."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.assertions import id_range
from play_api.models import factories
from play_api.models.responses.buggy import assert_cart_total, assert_item_ids, assert_prices_follow_ids
from play_api.services import buggy
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.support import quoted


@when(parsers.parse('Get buggy catalog and save response as "{var}"'))
def get_catalog(ctx, var):
    ctx.save(var, buggy.catalog())


@when(quoted('Get buggy items with query "{query}" and save response as "{var}"'))
def get_items(ctx, query, var):
    ctx.save(var, buggy.items(query_pairs(ctx.render(query))))


@then(quoted('Assert item ids are "{ids}" in response "{var}"'))
def assert_ids(ctx, ids, var):
    assert_item_ids(ctx.body(var), id_range(ids))


@then(parsers.parse('Assert every buggy item costs its id times 1.25 in response "{var}"'))
def assert_prices(ctx, var):
    assert_prices_follow_ids(ctx.body(var))


@when(quoted('Post buggy cart with items "{spec}" and save response as "{var}"'))
def post_cart(ctx, spec, var):
    ctx.save(var, buggy.cart_total(factories.cart(spec)))


@when(parsers.parse('Post buggy cart with {count:d} items and save response as "{var}"'))
def post_cart_many(ctx, count, var):
    ctx.save(var, buggy.cart_total(factories.cart_of(count)))


@when(parsers.parse('Post buggy cart with raw body "{raw}" and save response as "{var}"'))
def post_cart_raw(ctx, raw, var):
    ctx.save(var, buggy.cart_total(raw_json(ctx.render(raw))))


@then(quoted('Assert cart total is "{amount}" in response "{var}"'))
def assert_total(ctx, amount, var):
    assert_cart_total(ctx.response(var).text, amount)


@when(quoted('Get buggy schedule with query "{query}" and save response as "{var}"'))
def get_schedule(ctx, query, var):
    ctx.save(var, buggy.schedule(query_pairs(ctx.render(query))))
