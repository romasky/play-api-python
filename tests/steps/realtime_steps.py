"""Streaming steps — Server-Sent Events and the WebSocket echo (all transport in `services.realtime`)."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.assertions import assert_sse_done, assert_sse_progress
from play_api.services import realtime
from play_api.utils.gherkin import query_pairs
from tests.steps.support import quoted

# ─── Server-Sent Events ────────────────────────────────────────────────────


@when(quoted('Stream SSE progress with query "{query}" and save the events as "{key}"'))
def stream_sse(ctx, query, key):
    ctx.save(key, realtime.sse_progress(query_pairs(ctx.render(query))))


@when(quoted('Request SSE progress with query "{query}" and save response as "{var}"'))
def request_sse(ctx, query, var):
    ctx.save(var, realtime.sse_progress_response(query_pairs(ctx.render(query))))


@then(parsers.parse('Assert SSE "{key}" has {count:d} progress events counting up to 100 percent'))
def assert_progress(ctx, key, count):
    assert_sse_progress(ctx.require(key), count)


@then(parsers.parse('Assert SSE "{key}" ends with a done event with status "{status}" and total {total:d}'))
def assert_done(ctx, key, status, total):
    assert_sse_done(ctx.require(key), status, total)


# ─── WebSocket ─────────────────────────────────────────────────────────────


@when(parsers.parse('Open the WebSocket echo and save the welcome as "{key}"'))
def open_websocket(ctx, key):
    session = realtime.ws_connect()
    ctx.defer(session.close)
    ctx.save("websocket", session)
    ctx.save(key, session.receive_json())


@when(quoted('Send the text "{text}" over the WebSocket and save the reply as "{key}"'))
def websocket_text(ctx, text, key):
    ctx.save(key, ctx.require("websocket").echo(text))


@when(quoted('Send the bytes "{hex_bytes}" over the WebSocket and save the reply as "{key}"'))
def websocket_bytes(ctx, hex_bytes, key):
    reply = ctx.require("websocket").echo(bytes.fromhex(hex_bytes))
    assert isinstance(reply, bytes), f"binary frame expected, got text {reply!r}"
    ctx.save(key, reply.hex())


@then(quoted('Assert WebSocket welcome "{key}" field "{field}" equals "{expected}"'))
def assert_welcome_field(ctx, key, field, expected):
    actual = str(ctx.require(key).get(field)).lower()
    assert actual == expected, f"welcome '{field}' = {actual!r}, expected {expected!r}"


@then(quoted('Assert WebSocket welcome "{key}" field "{field}" starts with "{prefix}"'))
def assert_welcome_prefix(ctx, key, field, prefix):
    actual = str(ctx.require(key).get(field))
    assert actual.startswith(prefix), f"welcome '{field}' = {actual!r}, expected prefix {prefix!r}"


@when(parsers.parse('Send a plain GET to the WebSocket echo and save response as "{var}"'))
def websocket_plain_get(ctx, var):
    ctx.save(var, realtime.ws_plain_get())
