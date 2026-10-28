"""Every service function against a fake wire: the method, path, query, caller headers and body it sends.

Paths are written out literally (not taken from `play_api.api.paths`) so a wrong path builder fails here too.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import httpx2 as httpx
import pytest

from play_api.api.client import Params
from play_api.config import settings
from play_api.models.requests import ProfileReq
from play_api.services import (
    admin,
    bug_reports,
    buggy,
    challenges,
    chaos,
    docs,
    files,
    jwt,
    login,
    mail,
    realtime,
    system,
    users,
    webhooks,
)
from tests.unit.wire import Part, Wire, caller_headers, install, json_body, multipart, query

V1 = "/api/v1"
H = {"Authorization": "Bearer tok"}
SENT_H = [("authorization", "Bearer tok")]
P: Params = [("page", 2), ("filter", "a:1"), ("filter", "b:2")]
SENT_P = [("page", "2"), ("filter", "a:1"), ("filter", "b:2")]
BODY = {"k": "v"}
NO_BODY = object()  # nothing on the wire


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Wire:
    return install(monkeypatch)


def case(
    call: Callable[[], object],
    method: str,
    path: str,
    *,
    params: list[tuple[str, str]] | None = None,
    headers: list[tuple[str, str]] | None = None,
    body: Any = NO_BODY,
    id: str,
) -> Any:
    return pytest.param(call, method, V1 + path, params or [], headers or [], body, id=id)


CASES = [
    # admin
    case(lambda: admin.stats(H), "GET", "/admin/stats", headers=SENT_H, id="admin.stats"),
    case(lambda: admin.list_users(H, P), "GET", "/admin/users", params=SENT_P, headers=SENT_H, id="admin.list_users"),
    case(lambda: admin.list_users(H), "GET", "/admin/users", headers=SENT_H, id="admin.list_users-no-params"),
    case(
        lambda: admin.set_role("u1", {"role": "admin"}, H),
        "PATCH",
        "/admin/users/u1/role",
        headers=SENT_H,
        body={"role": "admin"},
        id="admin.set_role",
    ),
    case(lambda: admin.delete_user("u1", H), "DELETE", "/admin/users/u1", headers=SENT_H, id="admin.delete_user"),
    # bug reports
    case(lambda: bug_reports.submit(BODY, H), "POST", "/bug-reports", headers=SENT_H, body=BODY, id="bugs.submit"),
    case(
        lambda: bug_reports.list_mine(H, P), "GET", "/bug-reports", params=SENT_P, headers=SENT_H, id="bugs.list_mine"
    ),
    case(lambda: bug_reports.get("r1", H), "GET", "/bug-reports/r1", headers=SENT_H, id="bugs.get"),
    # buggy
    case(buggy.catalog, "GET", "/buggy", id="buggy.catalog"),
    case(lambda: buggy.items(P), "GET", "/buggy/items", params=SENT_P, id="buggy.items"),
    case(lambda: buggy.cart_total([BODY]), "POST", "/buggy/cart/total", body=[BODY], id="buggy.cart_total"),
    case(lambda: buggy.schedule(P), "GET", "/buggy/schedule", params=SENT_P, id="buggy.schedule"),
    # challenges
    case(lambda: challenges.catalog(P), "GET", "/challenges", params=SENT_P, id="challenges.catalog"),
    case(lambda: challenges.progress(H), "GET", "/challenges/progress", headers=SENT_H, id="challenges.progress"),
    case(lambda: challenges.hints("c1"), "GET", "/challenges/c1/hints", id="challenges.hints"),
    case(
        lambda: challenges.reveal("c1", {"level": 1}, H),
        "POST",
        "/challenges/c1/hints/reveal",
        headers=SENT_H,
        body={"level": 1},
        id="challenges.reveal",
    ),
    case(
        lambda: challenges.start("c1", H, P),
        "POST",
        "/challenges/c1/start",
        params=SENT_P,
        headers=SENT_H,
        id="challenges.start",
    ),
    case(lambda: challenges.verify("c1", H), "POST", "/challenges/c1/verify", headers=SENT_H, id="challenges.verify"),
    case(
        lambda: challenges.verify("c1", H, BODY),
        "POST",
        "/challenges/c1/verify",
        headers=SENT_H,
        body=BODY,
        id="challenges.verify-body",
    ),
    # chaos
    case(chaos.cache, "GET", "/chaos/cache", id="chaos.cache"),
    case(
        lambda: chaos.cache({"If-None-Match": '"abc"'}, "HEAD"),
        "HEAD",
        "/chaos/cache",
        headers=[("if-none-match", '"abc"')],
        id="chaos.cache-conditional",
    ),
    case(lambda: chaos.delay("3"), "GET", "/chaos/delay/3", id="chaos.delay"),
    case(lambda: chaos.timeout(P), "GET", "/chaos/timeout", params=SENT_P, id="chaos.timeout"),
    case(
        lambda: chaos.echo("PUT", params=P, headers={"Content-Type": "text/plain"}, content="hi"),
        "PUT",
        "/chaos/echo",
        params=SENT_P,
        headers=[("content-type", "text/plain")],
        body=b"hi",
        id="chaos.echo",
    ),
    case(lambda: chaos.flaky(P), "GET", "/chaos/flaky", params=SENT_P, id="chaos.flaky"),
    case(lambda: chaos.flaky_sequence(P), "GET", "/chaos/flaky/sequence", params=SENT_P, id="chaos.flaky_sequence"),
    case(lambda: chaos.flaky_step("2", P), "GET", "/chaos/flaky/step/2", params=SENT_P, id="chaos.flaky_step"),
    case(
        lambda: chaos.gzip({"Accept-Encoding": "identity", "X-A": "1"}),
        "GET",
        "/chaos/gzip",
        headers=[("accept-encoding", "identity"), ("x-a", "1")],
        id="chaos.gzip",
    ),
    case(
        lambda: chaos.redirect("POST", "3", params=P, content="x"),
        "POST",
        "/chaos/redirect/3",
        params=SENT_P,
        body=b"x",
        id="chaos.redirect",
    ),
    case(lambda: chaos.redirect_done("GET"), "GET", "/chaos/redirect/done", id="chaos.redirect_done"),
    case(lambda: chaos.redirect_done("POST", "aaa"), "POST", "/chaos/redirect/done", body=b"aaa", id="chaos.done-body"),
    case(lambda: chaos.status("418"), "GET", "/chaos/status/418", id="chaos.status"),
    # docs
    case(lambda: docs.document("OpenAPI JSON"), "GET", "/openapi.json", id="docs.openapi-json"),
    case(lambda: docs.document("OpenAPI YAML", P), "GET", "/openapi.yaml", params=SENT_P, id="docs.openapi-yaml"),
    case(lambda: docs.document("Postman collection"), "GET", "/postman/collection.json", id="docs.postman-collection"),
    case(lambda: docs.document("Postman environment"), "GET", "/postman/environment.json", id="docs.postman-env"),
    case(lambda: docs.verify_recaptcha(BODY), "POST", "/verify-recaptcha", body=BODY, id="docs.verify_recaptcha"),
    # files (multipart upload: see the dedicated tests below)
    case(
        lambda: files.upload_json(BODY, H), "POST", "/files/upload", headers=SENT_H, body=BODY, id="files.upload_json"
    ),
    case(lambda: files.list_mine(H, P), "GET", "/files", params=SENT_P, headers=SENT_H, id="files.list_mine"),
    case(lambda: files.metadata("f1", H), "GET", "/files/f1", headers=SENT_H, id="files.metadata"),
    case(lambda: files.metadata("f1"), "GET", "/files/f1", id="files.metadata-anonymous"),
    case(lambda: files.download("f1", P), "GET", "/files/f1/download", params=SENT_P, id="files.download"),
    case(lambda: files.delete("f1", H), "DELETE", "/files/f1", headers=SENT_H, id="files.delete"),
    # jwt
    case(lambda: jwt.login(BODY), "POST", "/jwt/login", body=BODY, id="jwt.login"),
    case(lambda: jwt.me(H), "GET", "/jwt/me", headers=SENT_H, id="jwt.me"),
    case(lambda: jwt.refresh(BODY, H), "POST", "/jwt/refresh", headers=SENT_H, body=BODY, id="jwt.refresh"),
    case(lambda: jwt.refresh(BODY), "POST", "/jwt/refresh", body=BODY, id="jwt.refresh-no-header"),
    case(lambda: jwt.decode(BODY), "POST", "/jwt/decode", body=BODY, id="jwt.decode"),
    # login
    case(lambda: login.login(BODY), "POST", "/login", body=BODY, id="login.login"),
    case(lambda: login.basic_auth(H), "GET", "/auth/basic", headers=SENT_H, id="login.basic_auth"),
    case(login.basic_auth, "GET", "/auth/basic", id="login.basic_auth-no-header"),
    case(lambda: login.store_login(BODY), "POST", "/store/login", body=BODY, id="login.store_login"),
    # mail
    case(mail.create_mailbox, "POST", "/mail/create", body={}, id="mail.create_mailbox-empty"),
    case(lambda: mail.create_mailbox(BODY), "POST", "/mail/create", body=BODY, id="mail.create_mailbox"),
    case(lambda: mail.get_mailbox("m1"), "GET", "/mail/m1", id="mail.get_mailbox"),
    case(lambda: mail.delete_mailbox("m1"), "DELETE", "/mail/m1", id="mail.delete_mailbox"),
    case(lambda: mail.list_messages("m1"), "GET", "/mail/m1/messages", id="mail.list_messages"),
    case(lambda: mail.get_message("m1", "x1"), "GET", "/mail/m1/messages/x1", id="mail.get_message"),
    case(lambda: mail.send("m1", BODY), "POST", "/mail/m1/send", body=BODY, id="mail.send"),
    case(lambda: mail.send_to("m1", BODY), "POST", "/mail/m1/send-to", body=BODY, id="mail.send_to"),
    # realtime (plain HTTP calls)
    case(lambda: realtime.sse_progress_response(P), "GET", "/sse/progress", params=SENT_P, id="realtime.sse_response"),
    case(realtime.ws_plain_get, "GET", "/ws/echo", id="realtime.ws_plain_get"),
    # system
    case(lambda: system.health(H), "GET", "/health", headers=SENT_H, id="system.health"),
    case(system.health, "GET", "/health", id="system.health-no-header"),
    # users
    case(lambda: users.create(BODY), "POST", "/users/create", body=BODY, id="users.create"),
    case(lambda: users.create_admin(BODY), "POST", "/users/create-admin", body=BODY, id="users.create_admin"),
    case(lambda: users.get("u1", H), "GET", "/users/get/u1", headers=SENT_H, id="users.get"),
    case(lambda: users.get("u1"), "GET", "/users/get/u1", id="users.get-anonymous"),
    case(lambda: users.list_users(P, H), "GET", "/users/list", params=SENT_P, headers=SENT_H, id="users.list_users"),
    case(users.list_users, "GET", "/users/list", id="users.list_users-bare"),
    case(lambda: users.exists("u1", "HEAD"), "HEAD", "/users/exists/u1", id="users.exists-head"),
    case(lambda: users.exists("u1", "GET"), "GET", "/users/exists/u1", id="users.exists-get"),
    case(lambda: users.update("u1", BODY, H), "PUT", "/users/update/u1", headers=SENT_H, body=BODY, id="users.update"),
    case(
        lambda: users.patch("u1", ProfileReq(last_name="L"), H),
        "PATCH",
        "/users/patch/u1",
        headers=SENT_H,
        body={"last_name": "L"},
        id="users.patch",
    ),
    case(lambda: users.delete("u1", H), "DELETE", "/users/delete/u1", headers=SENT_H, id="users.delete"),
    case(lambda: users.logout("u1", H), "POST", "/users/logout/u1", headers=SENT_H, id="users.logout"),
    case(users.options, "OPTIONS", "/users/options", id="users.options"),
    # webhooks
    case(webhooks.create_inbox, "POST", "/webhooks/inbox", id="webhooks.create_inbox"),
    case(lambda: webhooks.get_inbox("w1"), "GET", "/webhooks/w1", id="webhooks.get_inbox"),
    case(lambda: webhooks.delete_inbox("w1"), "DELETE", "/webhooks/w1", id="webhooks.delete_inbox"),
    case(lambda: webhooks.ingest("i1"), "POST", "/webhooks/in/i1", id="webhooks.ingest-default"),
    case(
        lambda: webhooks.ingest("i1", "PUT", content=b"\x00\x01", headers=[("X-A", "1"), ("X-A", "2")], params=P),
        "PUT",
        "/webhooks/in/i1",
        params=SENT_P,
        headers=[("x-a", "1"), ("x-a", "2")],
        body=b"\x00\x01",
        id="webhooks.ingest",
    ),
    case(lambda: webhooks.list_events("w1", P), "GET", "/webhooks/w1/events", params=SENT_P, id="webhooks.list_events"),
    case(lambda: webhooks.get_event("w1", "e1"), "GET", "/webhooks/w1/events/e1", id="webhooks.get_event"),
]


@pytest.mark.parametrize(("call", "method", "path", "params", "headers", "body"), CASES)
def test_service_puts_the_request_on_the_wire(
    wire: Wire,
    call: Callable[[], object],
    method: str,
    path: str,
    params: list[tuple[str, str]],
    headers: list[tuple[str, str]],
    body: Any,
) -> None:
    answer = httpx.Response(418)
    wire.reply(answer)

    assert call() is answer
    sent = wire.last
    assert (sent.method, sent.url.path, query(sent), caller_headers(sent)) == (method, path, params, headers)
    if body is NO_BODY:
        assert sent.content == b""
    elif isinstance(body, bytes):
        assert sent.content == body
    else:
        assert json_body(sent) == body


def test_an_unknown_api_document_lists_the_known_ones(wire: Wire) -> None:
    with pytest.raises(AssertionError, match=r"unknown API document 'Swagger', expected one of \['OpenAPI JSON'"):
        docs.document("Swagger")

    assert wire.requests == []


# ─── files.upload (multipart) ───────────────────────────────────────────────

PNG = ("a.png", b"\x89PNG", "image/png")


@pytest.mark.parametrize(
    ("kwargs", "parts"),
    [
        ({"file": PNG}, [Part("file", "a.png", b"\x89PNG", "image/png")]),
        (
            {"file": PNG, "description": "my file"},
            [Part("file", "a.png", b"\x89PNG", "image/png"), Part("description", None, b"my file", None)],
        ),
        (
            {"file": PNG, "description": ""},
            [Part("file", "a.png", b"\x89PNG", "image/png"), Part("description", None, b"", None)],
        ),
        ({"file": PNG, "field": "upload"}, [Part("upload", "a.png", b"\x89PNG", "image/png")]),
        ({"file": None}, [Part("description", None, b"", None)]),  # still multipart → NO_FILE
        ({"file": None, "description": "d"}, [Part("description", None, b"d", None)]),
    ],
)
def test_upload_sends_multipart_parts(wire: Wire, kwargs: dict[str, Any], parts: list[Part]) -> None:
    files.upload(H, **kwargs)

    assert (wire.last.method, wire.last.url.path) == ("POST", f"{V1}/files/upload")
    assert caller_headers(wire.last) == SENT_H
    assert multipart(wire.last) == parts


# ─── chaos: timeouts, redirects, raw gzip bytes ─────────────────────────────


@pytest.mark.parametrize(
    ("call", "read_timeout"),
    [
        (lambda: chaos.delay("3", 1.5), 1.5),
        (lambda: chaos.timeout(None, 2.0), 2.0),
        (lambda: chaos.delay("3"), settings.request_timeout),
        (chaos.timeout, settings.request_timeout),
    ],
)
def test_timeout_calls_pass_the_read_timeout(wire: Wire, call: Callable[[], object], read_timeout: float) -> None:
    call()

    assert wire.last.extensions["timeout"]["read"] == read_timeout


@pytest.mark.parametrize(("follow", "statuses"), [(True, [302, 200]), (False, [302])])
def test_redirect_follows_only_when_asked(wire: Wire, follow: bool, statuses: list[int]) -> None:
    wire.reply(httpx.Response(302, headers={"location": f"{V1}/chaos/redirect/done"}), httpx.Response(200))

    response = chaos.redirect("GET", "1", follow=follow)

    assert [r.status_code for r in [*response.history, response]] == statuses
    assert len(wire.requests) == len(statuses)


def test_redirect_is_not_followed_by_default(wire: Wire) -> None:
    wire.reply(httpx.Response(302, headers={"location": f"{V1}/chaos/redirect/done"}), httpx.Response(200))

    response = chaos.redirect("GET", "1")

    assert (response.status_code, response.history, len(wire.requests)) == (302, [], 1)


def _gzip_chunks() -> Iterator[bytes]:
    yield b"\x1f"
    yield b"\x8b"
    raise AssertionError("read past the two magic bytes")


def test_gzip_magic_reads_only_the_first_two_raw_bytes(wire: Wire) -> None:
    wire.reply(httpx.Response(200, content=_gzip_chunks(), headers={"content-encoding": "gzip"}))

    assert chaos.gzip_magic({"Accept-Encoding": "gzip", "X-A": "1"}) == b"\x1f\x8b"
    assert (wire.last.method, wire.last.url.path, caller_headers(wire.last)) == (
        "GET",
        f"{V1}/chaos/gzip",
        [("accept-encoding", "gzip"), ("x-a", "1")],
    )


def test_gzip_magic_trims_a_larger_first_chunk(wire: Wire) -> None:
    wire.reply(httpx.Response(200, content=iter([b"\x1f\x8b\x08\x00"])))

    assert chaos.gzip_magic({}) == b"\x1f\x8b"


def test_gzip_magic_refuses_a_non_200(wire: Wire) -> None:
    wire.reply(httpx.Response(503, content=b"down"))

    with pytest.raises(AssertionError, match="GET /chaos/gzip answered 503"):
        chaos.gzip_magic({})


def test_gzip_magic_returns_what_there_is_of_a_shorter_body(wire: Wire) -> None:
    wire.reply(httpx.Response(200, content=iter([b"\x1f"])))

    assert chaos.gzip_magic({}) == b"\x1f"
