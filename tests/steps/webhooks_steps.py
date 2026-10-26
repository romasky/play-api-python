"""/webhooks/* steps. Every created inbox is deleted after the scenario (`save_created`): the server allows
only 20 ACTIVE inboxes per IP, so a leak would break the 21st scenario for two hours."""

from __future__ import annotations

import base64

from pytest_bdd import parsers, then, when

from play_api.services import webhooks
from play_api.utils.gherkin import query_pairs, unescape_quotes
from play_api.utils.lookup import choose
from play_api.utils.samples import BINARY, WEBHOOK_BODY_LIMIT
from play_api.utils.webhook_sign import SIGNED_BODY, header_for
from tests.steps.support import quoted, save_created

_JSON = {"Content-Type": "application/json"}
_SIZES = {"64 KiB": WEBHOOK_BODY_LIMIT, "64 KiB + 1": WEBHOOK_BODY_LIMIT + 1}


@when(parsers.parse('Create webhook inbox and save response as "{var}"'))
def create_inbox(ctx, var):
    save_created(ctx, var, webhooks.create_inbox, lambda body: webhooks.delete_inbox(body["token"]))


@when(quoted('Get webhook inbox "{token_key}" and save response as "{var}"'))
def get_inbox(ctx, token_key, var):
    ctx.save(var, webhooks.get_inbox(ctx.str(token_key)))


@when(quoted('Delete webhook inbox "{token_key}" and save response as "{var}"'))
def delete_inbox(ctx, token_key, var):
    ctx.save(var, webhooks.delete_inbox(ctx.str(token_key)))


# ─── Capture (/webhooks/in/{ingest_token}) — bodies go as raw bytes, compared byte-for-byte later ───


@when(quoted('Send "{method}" to webhook ingest "{ingest_key}" and save response as "{var}"'))
def ingest_empty(ctx, method, ingest_key, var):
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), method))


@when(parsers.parse('Send POST to webhook ingest "{ingest_key}" with JSON body "{raw}" and save response as "{var}"'))
def ingest_json(ctx, ingest_key, raw, var):
    body = unescape_quotes(raw)
    ctx.save("sentBody", body)
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), content=body, headers=_JSON))


@when(
    quoted(
        'Send POST to webhook ingest "{ingest_key}" with header "{name}" values "{first}" and "{second}" and query "{query}" and save response as "{var}"'  # noqa: E501
    )
)
def ingest_repeated(ctx, ingest_key, name, first, second, query, var):
    headers = [(name, first), (name, second)]
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), headers=headers, params=query_pairs(query)))


@when(
    quoted(
        'Send POST to webhook ingest "{ingest_key}" with header "{name}" value "{value}" and save response as "{var}"'
    )
)
def ingest_header(ctx, ingest_key, name, value, var):
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), headers={name: value}))


@when(quoted('Send POST to webhook ingest "{ingest_key}" with a binary body and save response as "{var}"'))
def ingest_binary(ctx, ingest_key, var):
    headers = {"Content-Type": "application/octet-stream"}
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), content=BINARY, headers=headers))


@when(quoted('Send POST to webhook ingest "{ingest_key}" with a body of size "{size}" and save response as "{var}"'))
def ingest_sized(ctx, ingest_key, size, var):
    body = "a" * choose(_SIZES, size, "body size")
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), content=body, headers={"Content-Type": "text/plain"}))


@when(
    quoted(
        'Send POST to webhook ingest "{ingest_key}" signed with "{secret_key}" as "{kind}" and save response as "{var}"'
    )
)
def ingest_signed(ctx, ingest_key, secret_key, kind, var):
    headers = {**_JSON, **header_for(kind, ctx.str(secret_key), SIGNED_BODY)}
    ctx.save(var, webhooks.ingest(ctx.str(ingest_key), content=SIGNED_BODY, headers=headers))


# ─── Events ────────────────────────────────────────────────────────────────


@when(quoted('List webhook events of "{token_key}" and save response as "{var}"'))
def list_events(ctx, token_key, var):
    ctx.save(var, webhooks.list_events(ctx.str(token_key)))


@when(quoted('List webhook events of "{token_key}" with query "{query}" and save response as "{var}"'))
def list_events_query(ctx, token_key, query, var):
    ctx.save(var, webhooks.list_events(ctx.str(token_key), query_pairs(ctx.render(query))))


@when(quoted('Get webhook event "{event_key}" of "{token_key}" and save response as "{var}"'))
def get_event(ctx, event_key, token_key, var):
    ctx.save(var, webhooks.get_event(ctx.str(token_key), ctx.str(event_key)))


@then(quoted('Assert field "{field}" is the base64 of the binary body in response "{var}"'))
def assert_base64_binary(ctx, field, var):
    actual = ctx.body(var).get(field)
    assert actual is not None and base64.b64decode(actual) == BINARY, f"'{field}' = {actual!r} is not base64(BINARY)"
