"""/mail/* — temporary mailboxes, message injection and the SMTP response simulator."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.services import JsonBody


def create_mailbox(body: JsonBody = None) -> httpx.Response:
    return client.post(paths.MAIL_CREATE, body if body is not None else {})


def get_mailbox(token: str) -> httpx.Response:
    return client.get(paths.mail_get(token))


def delete_mailbox(token: str) -> httpx.Response:
    return client.delete(paths.mail_get(token))


def list_messages(token: str) -> httpx.Response:
    return client.get(paths.mail_messages(token))


def get_message(token: str, message_id: str) -> httpx.Response:
    return client.get(paths.mail_message(token, message_id))


def send(token: str, body: JsonBody) -> httpx.Response:
    return client.post(paths.mail_send(token), body)


def send_to(token: str, body: JsonBody) -> httpx.Response:
    """SMTP response simulator — always 200; `accepted` tells the delivery outcome."""
    return client.post(paths.mail_send_to(token), body)
