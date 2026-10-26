"""API descriptions (OpenAPI / Postman downloads), Server-Sent Events, WebSocket echo and reCAPTCHA."""

from __future__ import annotations

import json

from pytest_bdd import parsers, then, when

from play_api.services import docs, realtime
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.parsing import quoted

# ─── API documents ─────────────────────────────────────────────────────────


@when(quoted('Download the API document "{name}" and save response as "{var}"'))
def download_document(ctx, name, var):
    ctx.save(var, docs.document(name))


@when(quoted('Download the API document "{name}" with query "{query}" and save response as "{var}"'))
def download_document_query(ctx, name, query, var):
    ctx.save(var, docs.document(name, query_pairs(query)))


@then(quoted('Assert Postman variable "{key}" is defined in response "{var}"'))
def assert_postman_variable(ctx, key, var):
    keys = [v.get("key") for v in ctx.body(var).get("variable", [])]
    assert key in keys, f"collection variable '{key}' missing; defined: {keys}"


# ─── Server-Sent Events ────────────────────────────────────────────────────


@when(quoted('Stream SSE progress with query "{query}" and save the events as "{key}"'))
def stream_sse(ctx, query, key):
    ctx.save(key, realtime.sse_progress(query_pairs(query)))


@when(quoted('Request SSE progress with query "{query}" and save response as "{var}"'))
def request_sse(ctx, query, var):
    ctx.save(var, realtime.sse_progress_response(query_pairs(query)))


@then(parsers.parse('Assert SSE "{key}" has {count:d} progress events counting up to 100 percent'))
def assert_sse_progress(ctx, key, count):
    progress = [e.data for e in ctx.get(key, fail_if_missing=True) if e.event == "progress"]
    assert [p["step"] for p in progress] == list(range(1, count + 1)), f"progress steps: {progress}"
    assert all(p["total"] == count for p in progress), f"progress totals: {progress}"
    assert progress[-1]["percent"] == 100, f"last progress event: {progress[-1]}"


@then(parsers.parse('Assert SSE "{key}" ends with a done event with status "{status}" and total {total:d}'))
def assert_sse_done(ctx, key, status, total):
    last = ctx.get(key, fail_if_missing=True)[-1]
    assert last.event == "done" and last.data == {"status": status, "total": total}, f"last event: {last}"


# ─── WebSocket ─────────────────────────────────────────────────────────────


@when(parsers.parse('Open the WebSocket echo and save the welcome as "{key}"'))
def open_websocket(ctx, key):
    connection = realtime.ws_connect()
    ctx.defer(connection.close)
    ctx.save("websocket", connection)
    ctx.save(key, json.loads(connection.recv(timeout=10)))


@when(quoted('Send the text "{text}" over the WebSocket and save the reply as "{key}"'))
def websocket_text(ctx, text, key):
    connection = ctx.get("websocket", fail_if_missing=True)
    connection.send(text)
    ctx.save(key, connection.recv(timeout=10))


@when(quoted('Send the bytes "{hex_bytes}" over the WebSocket and save the reply as "{key}"'))
def websocket_bytes(ctx, hex_bytes, key):
    connection = ctx.get("websocket", fail_if_missing=True)
    connection.send(bytes.fromhex(hex_bytes))
    reply = connection.recv(timeout=10)
    assert isinstance(reply, bytes), f"binary frame expected, got text {reply!r}"
    ctx.save(key, reply.hex())


@then(quoted('Assert WebSocket welcome "{key}" field "{field}" equals "{expected}"'))
def assert_welcome_field(ctx, key, field, expected):
    actual = str(ctx.get(key, fail_if_missing=True).get(field)).lower()
    assert actual == expected, f"welcome '{field}' = {actual!r}, expected {expected!r}"


@then(quoted('Assert WebSocket welcome "{key}" field "{field}" starts with "{prefix}"'))
def assert_welcome_prefix(ctx, key, field, prefix):
    actual = str(ctx.get(key, fail_if_missing=True).get(field))
    assert actual.startswith(prefix), f"welcome '{field}' = {actual!r}, expected prefix {prefix!r}"


@when(parsers.parse('Send a plain GET to the WebSocket echo and save response as "{var}"'))
def websocket_plain_get(ctx, var):
    ctx.save(var, realtime.ws_plain_get())


# ─── reCAPTCHA (non-standard envelope {success, error: <string>}) ───────────


@when(parsers.parse('Verify reCAPTCHA with raw body "{raw}" and save response as "{var}"'))
def verify_recaptcha(ctx, raw, var):
    ctx.save(var, docs.verify_recaptcha(raw_json(raw)))
