"""Mailbox / message steps — port of src/steps/mailSteps.js."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.api import client, paths
from play_api.models.requests import CreateMailboxReq, SendMessageReq
from play_api.models.responses import assert_messages_have_no_full_body
from play_api.utils.gherkin import raw_json

# ─── Create mailbox ────────────────────────────────────────────────────────


@when(parsers.parse('Create mailbox and save response as "{var}"'))
def create_mailbox(ctx, var):
    ctx.save(var, client.post(paths.MAIL_CREATE, {}))


@when(parsers.parse('Create mailbox with domain "{domain}" and save response as "{var}"'))
def create_mailbox_domain(ctx, domain, var):
    ctx.save(var, client.post(paths.MAIL_CREATE, CreateMailboxReq(domain=domain).to_body()))


@when(parsers.parse('Create mailbox with local_part "{local_part}" and save response as "{var}"'))
def create_mailbox_local_part(ctx, local_part, var):
    ctx.save(var, client.post(paths.MAIL_CREATE, CreateMailboxReq(local_part=local_part).to_body()))


@when(parsers.parse('Create mailbox with context local_part "{key}" and save response as "{var}"'))
def create_mailbox_context_local_part(ctx, key, var):
    ctx.save(var, client.post(paths.MAIL_CREATE, CreateMailboxReq(local_part=ctx.str(key)).to_body()))


@when(parsers.parse('Create mailbox with domain "{domain}" local_part "{local_part}" and save response as "{var}"'))
def create_mailbox_domain_local_part(ctx, domain, local_part, var):
    ctx.save(var, client.post(paths.MAIL_CREATE, CreateMailboxReq(domain=domain, local_part=local_part).to_body()))


@when(parsers.parse('Create mailbox with raw body "{raw}" and save response as "{var}"'))
def create_mailbox_raw(ctx, raw, var):
    ctx.save(var, client.post(paths.MAIL_CREATE, raw_json(raw)))


# ─── Get / delete mailbox ──────────────────────────────────────────────────


@when(parsers.parse('Get mailbox with token "{token_key}" and save response as "{var}"'))
def get_mailbox(ctx, token_key, var):
    ctx.save(var, client.get(paths.mail_get(ctx.str(token_key))))


@when(parsers.parse('Delete mailbox with token "{token_key}" and save response as "{var}"'))
def delete_mailbox(ctx, token_key, var):
    ctx.save(var, client.delete(paths.mail_delete(ctx.str(token_key))))


# ─── Messages ──────────────────────────────────────────────────────────────


@when(parsers.parse('Get messages for token "{token_key}" and save response as "{var}"'))
def get_messages(ctx, token_key, var):
    ctx.save(var, client.get(paths.mail_messages(ctx.str(token_key))))


@when(parsers.parse('Get message "{msg_id_key}" for token "{token_key}" and save response as "{var}"'))
def get_message(ctx, msg_id_key, token_key, var):
    ctx.save(var, client.get(paths.mail_message(ctx.str(token_key), ctx.str(msg_id_key))))


@when(
    parsers.parse(
        'Send message to token "{token_key}" from "{from_key}" subject "{subject_key}" body "{body_key}" and save response as "{var}"'  # noqa: E501
    )
)
def send_message(ctx, token_key, from_key, subject_key, body_key, var):
    body = SendMessageReq(**{"from": ctx.str(from_key)}, subject=ctx.str(subject_key), body=ctx.str(body_key))
    ctx.save(var, client.post(paths.mail_send(ctx.str(token_key)), body.to_body()))


@when(parsers.parse('Send message to token "{token_key}" with raw body "{raw}" and save response as "{var}"'))
def send_message_raw(ctx, token_key, raw, var):
    ctx.save(var, client.post(paths.mail_send(ctx.str(token_key)), raw_json(raw)))


# ─── Typed list-shape assertion ────────────────────────────────────────────


@then(parsers.parse('Assert messages list "{var}" items have no full body'))
def assert_messages_no_full_body(ctx, var):
    assert_messages_have_no_full_body(ctx.body(var))
