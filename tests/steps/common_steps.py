"""Generic steps — port of src/steps/commonSteps.js (data generation, Extract, status /
header / typed body-field assertions). Phrasing must match features/ verbatim.

Pattern: `parsers.parse('… "{var}" …')` replaces Cucumber's `{string}`; `{n:d}` replaces `{int}`.
Every step receives the `ctx` fixture. Keep steps thin; put logic in play_api.*.

TODO (port the rest of commonSteps.js — see the JS file for the full list):
  Save context value / Generate * (12 generators) / Generate string of length / local part variants /
  Get current date / Assert response is not a server error / Assert status code is one of /
  Assert response header {equals,contains,is present} / Assert field {contains,is present,is absent} /
  Assert response body is empty / Assert response has request_id / Assert {string} {not null,equals,contains,matches regex} /
  Print response
"""

from __future__ import annotations

from pytest_bdd import given, then, when, parsers

from play_api.utils import generator as gen
from play_api.utils.json_path import get_path, has_path


# ─── Data generation ───────────────────────────────────────────────────────

@given(parsers.parse('Save string "{value}" as "{key}"'))
def save_string(ctx, value, key):
    ctx.save(key, value)


@given(parsers.parse('Generate email and save as "{key}"'))
def generate_email(ctx, key):
    ctx.save(key, gen.email())


# ─── Extract ───────────────────────────────────────────────────────────────

@then(parsers.parse('Extract "{field}" from "{var}" and save as "{key}"'))
def extract_field(ctx, field, var, key):
    body = ctx.body(var)
    value = get_path(body, field)
    assert value is not None, f"Field '{field}' not found in response. Body: {body}"
    ctx.save(key, str(value))


# ─── Status code ───────────────────────────────────────────────────────────

@when(parsers.parse('Get and check status code {code:d} from "{var}"'))
@then(parsers.parse('Get and check status code {code:d} from "{var}"'))
def check_status_code(ctx, code, var):
    res = ctx.response(var)
    assert res.status_code == code, f"Expected status {code} but got {res.status_code}. Body: {res.text}"


# ─── Typed body-field assertions ───────────────────────────────────────────

@then(parsers.parse('Assert field "{field}" equals "{expected}" in response "{var}"'))
def assert_field_equals(ctx, field, expected, var):
    actual = get_path(ctx.body(var), field)
    resolved = ctx.str(expected)
    # JS parity: String(true) === "true", String(0) === "0"
    rendered = str(actual).lower() if isinstance(actual, bool) else str(actual)
    assert rendered == resolved, f"Field '{field}': expected '{resolved}' but got '{actual}'"


@then(parsers.parse('Assert field "{field}" is not null in response "{var}"'))
def assert_field_not_null(ctx, field, var):
    body = ctx.body(var)
    assert get_path(body, field) is not None, f"Field '{field}' is null/missing. Body: {body}"


@then(parsers.parse('Assert field "{field}" is absent in response "{var}"'))
def assert_field_absent(ctx, field, var):
    body = ctx.body(var)
    assert not has_path(body, field), f"Field '{field}' should NOT be present. Body: {body}"
