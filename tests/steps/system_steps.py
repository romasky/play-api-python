"""System endpoints: GET /health, OPTIONS /users/options, the API descriptions (OpenAPI / Postman downloads)
and POST /verify-recaptcha (non-standard envelope {success, error: <string>})."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.services import docs, system, users
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.support import quoted

# ─── Health / OPTIONS (live API answers OPTIONS with 204 via Cloudflare) ───


@when(parsers.parse('Send GET health request and save as "{var}"'))
def get_health(ctx, var):
    ctx.save(var, system.health())


@when(parsers.parse('Send GET health request with X-Request-ID "{request_id_key}" and save as "{var}"'))
def get_health_with_request_id(ctx, request_id_key, var):
    ctx.save(var, system.health({"X-Request-ID": ctx.str(request_id_key)}))


@when(parsers.parse('Send OPTIONS users request and save response as "{var}"'))
def options_users(ctx, var):
    ctx.save(var, users.options())


# ─── API documents ─────────────────────────────────────────────────────────


@when(quoted('Download the API document "{name}" and save response as "{var}"'))
def download_document(ctx, name, var):
    ctx.save(var, docs.document(name))


@when(quoted('Download the API document "{name}" with query "{query}" and save response as "{var}"'))
def download_document_query(ctx, name, query, var):
    ctx.save(var, docs.document(name, query_pairs(ctx.render(query))))


@then(quoted('Assert Postman variable "{key}" is defined in response "{var}"'))
def assert_postman_variable(ctx, key, var):
    keys = [v.get("key") for v in ctx.body(var).get("variable", [])]
    assert key in keys, f"collection variable '{key}' missing; defined: {keys}"


# ─── reCAPTCHA ─────────────────────────────────────────────────────────────


@when(parsers.parse('Verify reCAPTCHA with raw body "{raw}" and save response as "{var}"'))
def verify_recaptcha(ctx, raw, var):
    ctx.save(var, docs.verify_recaptcha(raw_json(ctx.render(raw))))
