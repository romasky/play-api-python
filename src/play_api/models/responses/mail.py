"""/mail/* contracts."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from play_api.models.responses.base import Contract, entry
from play_api.utils.json_path import has_path


class MailboxResponse(Contract):
    id: str
    token: str
    email_address: str
    domain: str
    expires_at: str
    created_at: str


class MessagesListResponse(Contract):
    messages: list[dict[str, Any]]
    count: int


class MessageResponse(Contract):
    """Single message (GET /mail/:token/messages/:id and POST /mail/:token/send 201)."""

    id: str
    from_: str = Field(alias="from")
    subject: str
    body_preview: str
    body: str
    html_body: str | None = None
    headers: dict[str, Any] | None = None
    received_at: str


class SendToResponse(Contract):
    """No `success` field. Magic recipients add `enhanced_status`; accepted ones add `message_id`."""

    accepted: bool
    to: str
    smtp_code: str
    category: str
    message: str


CONTRACTS_2XX = (
    entry("POST", r"/mail/create", MailboxResponse),
    entry("GET", r"/mail/[^/]+", MailboxResponse),
    entry("GET", r"/mail/[^/]+/messages", MessagesListResponse),
    entry("GET", r"/mail/[^/]+/messages/[^/]+", MessageResponse),
    entry("POST", r"/mail/[^/]+/send", MessageResponse),
    entry("POST", r"/mail/[^/]+/send-to", SendToResponse),
)


def assert_messages_have_no_full_body(body: Any) -> None:
    messages = MessagesListResponse.check(body).messages
    assert messages, "Expected at least one message in the list to check its shape"
    for i, m in enumerate(messages):
        assert has_path(m, "body_preview"), f"messages[{i}] has no 'body_preview': {m}"
        leaked = [f for f in ("body", "html_body", "headers") if has_path(m, f)]
        assert not leaked, f"messages[{i}] exposes full-body fields {leaked}: {m}"
