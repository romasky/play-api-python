"""Generic steps — port of src/steps/commonSteps.js (data generation, Extract, status /
header / typed body-field assertions). Phrasing must match features/ verbatim.

Pattern: `parsers.parse('… "{var}" …')` replaces Cucumber's `{string}`; `{n:d}` replaces `{int}`.
Every step receives the `ctx` fixture. Keep steps thin; put logic in play_api.*.

Decorator choice: pytest-bdd matches by keyword (Cucumber does not), and the features use
`Extract` / `Generate …` / `Save …` after Given, When *and* Then — so data-setup and extraction
steps use the keyword-agnostic `@step`; pure assertions stay `@then`.
"""

from __future__ import annotations

import re
from datetime import date

from pytest_bdd import parsers, step, then

from play_api.models.responses import assert_has_request_id
from play_api.utils import generator as gen
from play_api.utils.json_path import get_path, has_path

# ─── Data generation ───────────────────────────────────────────────────────


@step(parsers.parse('Save string "{value}" as "{key}"'))
def save_string(ctx, value, key):
    ctx.save(key, value)


@step(parsers.parse('Save context value "{src_key}" as "{dest_key}"'))
def save_context_value(ctx, src_key, dest_key):
    ctx.save(dest_key, ctx.get(src_key, fail_if_missing=True))


@step(parsers.parse('Generate email and save as "{key}"'))
def generate_email(ctx, key):
    ctx.save(key, gen.email())


@step(parsers.parse('Generate username and save as "{key}"'))
def generate_username(ctx, key):
    ctx.save(key, gen.username())


@step(parsers.parse('Generate password and save as "{key}"'))
def generate_password(ctx, key):
    ctx.save(key, gen.password())


@step(parsers.parse('Generate first name and save as "{key}"'))
def generate_first_name(ctx, key):
    ctx.save(key, gen.first_name())


@step(parsers.parse('Generate last name and save as "{key}"'))
def generate_last_name(ctx, key):
    ctx.save(key, gen.last_name())


@step(parsers.parse('Generate sender email and save as "{key}"'))
def generate_sender_email(ctx, key):
    ctx.save(key, gen.sender_email())


@step(parsers.parse('Generate message subject and save as "{key}"'))
def generate_message_subject(ctx, key):
    ctx.save(key, gen.message_subject())


@step(parsers.parse('Generate message body and save as "{key}"'))
def generate_message_body(ctx, key):
    ctx.save(key, gen.message_body())


@step(parsers.parse('Generate invalid email and save as "{key}"'))
def generate_invalid_email(ctx, key):
    ctx.save(key, gen.invalid_email())


@step(parsers.parse('Generate short password and save as "{key}"'))
def generate_short_password(ctx, key):
    ctx.save(key, gen.short_password())


@step(parsers.parse('Generate fake mongo id and save as "{key}"'))
def generate_fake_mongo_id(ctx, key):
    ctx.save(key, gen.fake_mongo_id())


@step(parsers.parse('Generate fake uuid and save as "{key}"'))
def generate_fake_uuid(ctx, key):
    ctx.save(key, gen.fake_uuid())


@step(parsers.parse('Generate phone number and save as "{key}"'))
def generate_phone_number(ctx, key):
    ctx.save(key, gen.phone_number())


@step(parsers.parse('Generate local part and save as "{key}"'))
def generate_local_part(ctx, key):
    ctx.save(key, gen.alphanumeric(10).lower())


@step(parsers.parse('Generate local part with underscore and hyphen and save as "{key}"'))
def generate_local_part_underscore_hyphen(ctx, key):
    ctx.save(key, f"my_{gen.alphanumeric(6)}-box")


@step(parsers.parse('Generate string of length {n:d} and save as "{key}"'))
def generate_string_of_length(ctx, n, key):
    ctx.save(key, gen.alphanumeric(n))


@step(parsers.parse('Get current date and save as "{key}"'))
def get_current_date(ctx, key):
    ctx.save(key, date.today().isoformat())


# ─── Extract ───────────────────────────────────────────────────────────────


@step(parsers.parse('Extract "{field}" from "{var}" and save as "{key}"'))
def extract_field(ctx, field, var, key):
    body = ctx.body(var)
    value = get_path(body, field)
    assert value is not None, f"Field '{field}' not found in response. Body: {body}"
    ctx.save(key, str(value))


# ─── Status code ───────────────────────────────────────────────────────────


@step(parsers.parse('Get and check status code {code:d} from "{var}"'))
def check_status_code(ctx, code, var):
    res = ctx.response(var)
    assert res.status_code == code, f"Expected status {code} but got {res.status_code}. Body: {res.text}"


@then(parsers.parse('Assert response is not a server error in "{var}"'))
def assert_not_server_error(ctx, var):
    res = ctx.response(var)
    assert res.status_code < 500, f"Expected non-5xx status but got {res.status_code}. Body: {res.text}"


@then(parsers.parse('Assert status code is one of "{codes}" in "{var}"'))
def assert_status_one_of(ctx, codes, var):
    allowed = {int(c.strip()) for c in codes.split(",")}
    res = ctx.response(var)
    assert res.status_code in allowed, f"Expected status in [{codes}] but got {res.status_code}. Body: {res.text}"


# ─── Header assertions (httpx headers are case-insensitive) ────────────────


@then(parsers.parse('Assert response header "{header}" equals "{expected}" in "{var}"'))
def assert_header_equals(ctx, header, expected, var):
    actual = ctx.response(var).headers.get(header)
    resolved = ctx.str(expected)
    assert actual == resolved, f"Header '{header}': expected '{resolved}' but got '{actual}'"


@then(parsers.parse('Assert response header "{header}" contains "{expected}" in "{var}"'))
def assert_header_contains(ctx, header, expected, var):
    actual = ctx.response(var).headers.get(header)
    assert actual is not None and expected in actual, f"Header '{header}' '{actual}' does not contain '{expected}'"


@then(parsers.parse('Assert response header "{header}" is present in "{var}"'))
def assert_header_present(ctx, header, var):
    assert ctx.response(var).headers.get(header), f"Header '{header}' is missing"


# ─── Typed body-field assertions ───────────────────────────────────────────


def _render(value) -> str:
    """JS parity for `String(actual)`: booleans render lowercase, everything else via str()."""
    return str(value).lower() if isinstance(value, bool) else str(value)


@then(parsers.parse('Assert field "{field}" equals "{expected}" in response "{var}"'))
def assert_field_equals(ctx, field, expected, var):
    actual = get_path(ctx.body(var), field)
    resolved = ctx.str(expected)
    assert _render(actual) == resolved, f"Field '{field}': expected '{resolved}' but got '{actual}'"


@then(parsers.parse('Assert field "{field}" is not null in response "{var}"'))
def assert_field_not_null(ctx, field, var):
    body = ctx.body(var)
    assert get_path(body, field) is not None, f"Field '{field}' is null/missing. Body: {body}"


@then(parsers.parse('Assert field "{field}" contains "{expected}" in response "{var}"'))
def assert_field_contains(ctx, field, expected, var):
    actual = get_path(ctx.body(var), field)
    resolved = ctx.str(expected)
    assert isinstance(actual, str) and resolved in actual, f"Field '{field}' = '{actual}' does not contain '{resolved}'"


@then(parsers.parse('Assert field "{field}" is present in response "{var}"'))
def assert_field_present(ctx, field, var):
    body = ctx.body(var)
    assert has_path(body, field), f"Field '{field}' is missing. Body: {body}"


@then(parsers.parse('Assert field "{field}" is absent in response "{var}"'))
def assert_field_absent(ctx, field, var):
    body = ctx.body(var)
    assert not has_path(body, field), f"Field '{field}' should NOT be present. Body: {body}"


@then(parsers.parse('Assert response body is empty in "{var}"'))
def assert_body_empty(ctx, var):
    res = ctx.response(var)
    assert not res.content, f"Expected empty body but got: {res.text}"


@then(parsers.parse('Assert response has request_id in "{var}"'))
def assert_response_has_request_id(ctx, var):
    assert_has_request_id(ctx.body(var))


# ─── Context value assertions ──────────────────────────────────────────────


@then(parsers.parse('Assert "{key}" not null'))
def assert_ctx_not_null(ctx, key):
    assert ctx.get(key, fail_if_missing=True), f"{key} is null"


@then(parsers.parse('Assert "{key}" equals "{expected}"'))
def assert_ctx_equals(ctx, key, expected):
    actual, resolved = ctx.str(key), ctx.str(expected)
    assert actual == resolved, f"{key}: '{actual}' != '{resolved}'"


@then(parsers.parse('Assert "{key}" contains "{expected}"'))
def assert_ctx_contains(ctx, key, expected):
    value = ctx.str(key)
    assert expected in value, f"'{value}' does not contain '{expected}'"


@then(parsers.parse('Assert "{key}" matches regex "{regex}"'))
def assert_ctx_matches(ctx, key, regex):
    value = ctx.str(key)
    assert re.search(regex, value), f"'{value}' does not match regex '{regex}'"


# ─── Debug ─────────────────────────────────────────────────────────────────


@then(parsers.parse('Print response "{var}"'))
def print_response(ctx, var):
    value = ctx.get(var, fail_if_missing=True)
    if hasattr(value, "status_code"):
        print(f"\n[{var}] HTTP {value.status_code}\n{value.text}\n")
    else:
        print(f"\n[{var}] = {value}\n")
