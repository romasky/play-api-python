"""Mailbox / message steps — port of src/steps/mailSteps.js, on top of `play_api.services.mail`."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.models.requests import CreateMailboxReq, SendMessageReq, SendToReq
from play_api.models.responses.mail import assert_messages_have_no_full_body
from play_api.services import mail
from play_api.utils.gherkin import raw_json
from tests.steps.parsing import quoted

# ─── Create mailbox ────────────────────────────────────────────────────────


@when(parsers.parse('Create mailbox and save response as "{var}"'))
def create_mailbox(ctx, var):
    ctx.save(var, mail.create_mailbox())


@when(quoted('Create mailbox with domain "{domain}" and save response as "{var}"'))
def create_mailbox_domain(ctx, domain, var):
    ctx.save(var, mail.create_mailbox(CreateMailboxReq(domain=domain)))


@when(parsers.parse('Create mailbox with local_part "{local_part}" and save response as "{var}"'))
def create_mailbox_local_part(ctx, local_part, var):
    ctx.save(var, mail.create_mailbox(CreateMailboxReq(local_part=local_part)))


@when(parsers.parse('Create mailbox with context local_part "{key}" and save response as "{var}"'))
def create_mailbox_context_local_part(ctx, key, var):
    ctx.save(var, mail.create_mailbox(CreateMailboxReq(local_part=ctx.str(key))))


@when(quoted('Create mailbox with domain "{domain}" local_part "{local_part}" and save response as "{var}"'))
def create_mailbox_domain_local_part(ctx, domain, local_part, var):
    ctx.save(var, mail.create_mailbox(CreateMailboxReq(domain=domain, local_part=local_part)))


@when(parsers.parse('Create mailbox with raw body "{raw}" and save response as "{var}"'))
def create_mailbox_raw(ctx, raw, var):
    ctx.save(var, mail.create_mailbox(raw_json(raw)))


# ─── Get / delete mailbox ──────────────────────────────────────────────────


@when(parsers.parse('Get mailbox with token "{token_key}" and save response as "{var}"'))
def get_mailbox(ctx, token_key, var):
    ctx.save(var, mail.get_mailbox(ctx.str(token_key)))


@when(parsers.parse('Delete mailbox with token "{token_key}" and save response as "{var}"'))
def delete_mailbox(ctx, token_key, var):
    ctx.save(var, mail.delete_mailbox(ctx.str(token_key)))


# ─── Messages ──────────────────────────────────────────────────────────────


@when(parsers.parse('Get messages for token "{token_key}" and save response as "{var}"'))
def get_messages(ctx, token_key, var):
    ctx.save(var, mail.list_messages(ctx.str(token_key)))


@when(parsers.parse('Get message "{msg_id_key}" for token "{token_key}" and save response as "{var}"'))
def get_message(ctx, msg_id_key, token_key, var):
    ctx.save(var, mail.get_message(ctx.str(token_key), ctx.str(msg_id_key)))


@when(
    parsers.parse(
        'Send message to token "{token_key}" from "{from_key}" subject "{subject_key}" body "{body_key}" and save response as "{var}"'  # noqa: E501
    )
)
def send_message(ctx, token_key, from_key, subject_key, body_key, var):
    body = SendMessageReq(**{"from": ctx.str(from_key)}, subject=ctx.str(subject_key), body=ctx.str(body_key))
    ctx.save(var, mail.send(ctx.str(token_key), body))


@when(parsers.parse('Send message to token "{token_key}" with raw body "{raw}" and save response as "{var}"'))
def send_message_raw(ctx, token_key, raw, var):
    ctx.save(var, mail.send(ctx.str(token_key), raw_json(raw)))


# ─── SMTP response simulator (send-to) ─────────────────────────────────────


@when(quoted('Send to "{to_key}" from mailbox "{token_key}" and save response as "{var}"'))
def send_to(ctx, to_key, token_key, var):
    ctx.save(var, mail.send_to(ctx.str(token_key), SendToReq(to=ctx.str(to_key))))


@when(quoted('Send to "{to_key}" from mailbox "{token_key}" with subject "{subject}" and save response as "{var}"'))
def send_to_with_subject(ctx, to_key, token_key, subject, var):
    body = SendToReq(to=ctx.str(to_key), subject=subject, body="Sent through the SMTP response simulator")
    ctx.save(var, mail.send_to(ctx.str(token_key), body))


@when(parsers.parse('Send to from mailbox "{token_key}" with raw body "{raw}" and save response as "{var}"'))
def send_to_raw(ctx, token_key, raw, var):
    ctx.save(var, mail.send_to(ctx.str(token_key), raw_json(raw)))


# ─── Typed list-shape assertion ────────────────────────────────────────────


@then(parsers.parse('Assert messages list "{var}" items have no full body'))
def assert_messages_no_full_body(ctx, var):
    assert_messages_have_no_full_body(ctx.body(var))
