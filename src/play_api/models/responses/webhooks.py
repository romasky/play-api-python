"""/webhooks/* contracts — NO `success` field on any webhook 2xx body."""

from __future__ import annotations

from pydantic import Field

from play_api.models.responses.base import Contract, entry


class WebhookInbox(Contract):
    id: str
    token: str
    ingest_token: str
    ingest_url: str
    event_count: int
    total_received: int
    dropped_count: int
    created_at: str
    expires_at: str


class WebhookInboxCreated(WebhookInbox):
    signing_secret: str  # only in the 201 — GET never returns it


class IngestAccepted(Contract):
    received: bool
    event_id: str


class EventSummary(Contract):
    id: str
    method: str
    content_type: str
    body_preview: str | None = None
    body_size: int
    body_encoding: str
    signature_valid: bool | None = Field(...)
    received_at: str


class EventsListResponse(Contract):
    events: list[EventSummary]
    total: int
    returned: int
    page: int
    per_page: int
    dropped_count: int


class WebhookEvent(Contract):
    id: str
    method: str
    path: str
    headers: dict[str, list[str]]
    query: dict[str, list[str]] | None = None  # omitted when the request had no query string
    content_type: str
    body: str | None = None  # omitted for an empty body (HEAD included)
    body_size: int
    body_encoding: str  # "utf8" | "base64"
    signature_valid: bool | None = Field(...)
    received_at: str


CONTRACTS_2XX = (
    entry("POST", r"/webhooks/inbox", WebhookInboxCreated),
    entry("GET", r"/webhooks/[^/]+", WebhookInbox),
    entry("GET", r"/webhooks/[^/]+/events", EventsListResponse),
    entry("GET", r"/webhooks/[^/]+/events/[^/]+", WebhookEvent),
    *(entry(m, r"/webhooks/in/[^/]+", IngestAccepted) for m in ("GET", "POST", "PUT", "PATCH", "DELETE")),
)
