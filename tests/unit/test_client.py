from __future__ import annotations

import json
from collections.abc import Iterator

import allure
import httpx2 as httpx
import pytest

from play_api.api import client
from play_api.api.client import ContractViolation, RawJson
from play_api.config import settings
from play_api.models.requests import ProfileReq
from tests.unit.wire import Part, Wire, caller_headers, install, json_body, multipart, query

HEALTH = "/api/v1/health"
SECRET = "whsec_0123456789abcdef0123456789abcdef"
JSON_KIND = allure.attachment_type.JSON
TEXT_KIND = allure.attachment_type.TEXT


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Wire:
    return install(monkeypatch)


def _dropped() -> httpx.RemoteProtocolError:
    return httpx.RemoteProtocolError("Server disconnected without sending a response")


# ─── what goes on the wire ──────────────────────────────────────────────────


def test_request_sends_method_path_and_returns_the_response(wire: Wire) -> None:
    wire.reply(httpx.Response(404, text="404 page not found", headers={"content-type": "text/plain"}))

    response = client.request("HEAD", HEALTH)

    assert (wire.last.method, wire.last.url.path, str(wire.last.url.host)) == ("HEAD", HEALTH, "www.play-qa.com")
    assert response.status_code == 404
    assert response.text == "404 page not found"
    assert wire.steps == [f"HEAD {HEALTH}"]


def test_a_request_model_goes_out_as_its_body_without_unset_fields(wire: Wire) -> None:
    client.post("/api/v1/users/patch/u1", ProfileReq(first_name="Ann", bio=""))

    assert json_body(wire.last) == {"first_name": "Ann", "bio": ""}
    assert json.loads(wire.attached("Request Body")[0]) == {"first_name": "Ann", "bio": ""}


def test_a_plain_json_value_goes_out_as_json(wire: Wire) -> None:
    client.put("/api/v1/users/update/u1", {"name": "Ä", "tags": [1, None]})

    assert wire.last.method == "PUT"
    assert json_body(wire.last) == {"name": "Ä", "tags": [1, None]}
    assert wire.attached("Request Body") == ['{\n  "name": "Ä",\n  "tags": [\n    1,\n    null\n  ]\n}']


def test_raw_json_is_sent_verbatim_as_application_json_next_to_the_caller_headers(wire: Wire) -> None:
    client.patch("/api/v1/users/patch/u1", RawJson('{"email": "a@b.c",'), headers={"Authorization": " Bearer t "})

    assert wire.last.content == b'{"email": "a@b.c",'
    assert wire.last.headers["content-type"] == "application/json"
    assert caller_headers(wire.last) == [("authorization", "Bearer t")]
    assert wire.attached("Request Body") == ['{"email": "a@b.c",']


def test_header_values_are_trimmed_on_the_wire_but_attached_as_written(wire: Wire) -> None:
    client.delete("/api/v1/users/delete/u1", headers={"Authorization": "Bearer ", "X-Trace": "  a b  "})

    assert caller_headers(wire.last) == [("authorization", "Bearer"), ("x-trace", "a b")]
    assert json.loads(wire.attached("Request Headers")[0]) == {"Authorization": "Bearer ", "X-Trace": "  a b  "}


def test_a_repeated_header_goes_out_once_per_pair(wire: Wire) -> None:
    client.request("POST", "/api/v1/webhooks/in/i1", headers=[("X-Custom", "one"), ("X-Custom", "two")])

    assert caller_headers(wire.last) == [("x-custom", "one"), ("x-custom", "two")]
    assert json.loads(wire.attached("Request Headers")[0]) == [["X-Custom", "one"], ["X-Custom", "two"]]


@pytest.mark.parametrize(
    ("params", "sent", "attached"),
    [
        ({"page": 2, "search": "a b"}, [("page", "2"), ("search", "a b")], [["page", 2], ["search", "a b"]]),
        (
            [("filter", "a:1"), ("filter", "b:2"), ("sort", "")],
            [("filter", "a:1"), ("filter", "b:2"), ("sort", "")],
            [["filter", "a:1"], ["filter", "b:2"], ["sort", ""]],
        ),
    ],
)
def test_params_keep_repeats_and_empty_values(
    wire: Wire, params: client.Params, sent: list[tuple[str, str]], attached: list[list[object]]
) -> None:
    client.get("/api/v1/users/list", params=params)

    assert query(wire.last) == sent
    assert json.loads(wire.attached("Query Params")[0]) == attached


def test_nothing_optional_is_attached_for_a_bare_call(wire: Wire) -> None:
    client.options("/api/v1/users/options", headers={})

    assert wire.last.content == b""
    assert caller_headers(wire.last) == []
    assert [name for _, name, _ in wire.attachments] == ["Status", "Response Headers"]


def test_text_content_is_sent_as_is_and_attached_as_text(wire: Wire) -> None:
    client.request("POST", "/api/v1/chaos/echo", content="plain ✓", headers={"Content-Type": "text/plain"})

    assert wire.last.content == "plain ✓".encode()
    assert wire.attachments[1] == ("plain ✓", "Request Body", TEXT_KIND)


def test_binary_content_is_sent_as_is_and_only_its_size_is_attached(wire: Wire) -> None:
    client.request("POST", "/api/v1/chaos/echo", content=b"\x00\xff\x10")

    assert wire.last.content == b"\x00\xff\x10"
    assert wire.attached("Request Body") == ["<3 bytes>"]


def test_multipart_parts_go_out_and_are_summarised(wire: Wire) -> None:
    files: client.Files = [("file", ("a.png", b"\x89PNG", "image/png")), ("description", (None, b"hi", None))]

    client.request("POST", "/api/v1/files/upload", files=files)

    assert multipart(wire.last) == [
        Part("file", "a.png", b"\x89PNG", "image/png"),
        Part("description", None, b"hi", None),
    ]
    assert json.loads(wire.attached("Multipart Files")[0]) == [
        {"field": "file", "filename": "a.png", "bytes": 4, "content_type": "image/png"},
        {"field": "description", "filename": None, "bytes": 2, "content_type": None},
    ]


# ─── timeouts, redirects, pacing, retry ─────────────────────────────────────


def test_the_client_default_timeout_applies_unless_one_is_given(wire: Wire) -> None:
    client.get("/api/v1/chaos/delay/1")
    client.get("/api/v1/chaos/delay/1", timeout=1.5)

    assert [r.extensions["timeout"]["read"] for r in wire.requests] == [settings.request_timeout, 1.5]


def test_a_client_timeout_is_attached_and_re_raised(wire: Wire) -> None:
    wire.reply(httpx.ReadTimeout("timed out"))

    with pytest.raises(httpx.ReadTimeout):
        client.get("/api/v1/chaos/timeout", timeout=0.5)

    assert wire.attached("Timeout") == ["ReadTimeout after the 0.5 s client timeout"]


def test_a_default_timeout_attachment_names_the_effective_seconds(wire: Wire) -> None:
    wire.reply(httpx.ReadTimeout("timed out"))

    with pytest.raises(httpx.ReadTimeout):
        client.get("/api/v1/chaos/timeout")

    assert wire.attached("Timeout") == [f"ReadTimeout after the {settings.request_timeout} s client timeout"]
    assert wire.attached("Status") == []


def test_redirects_are_not_followed_by_default(wire: Wire) -> None:
    wire.reply(httpx.Response(302, headers={"location": "/api/v1/chaos/redirect/done"}))

    response = client.get("/api/v1/chaos/redirect/1")

    assert response.status_code == 302
    assert len(wire.requests) == 1
    assert wire.attached("Redirect") == []


def test_followed_redirect_hops_are_attached(wire: Wire) -> None:
    wire.reply(
        httpx.Response(307, headers={"location": "/api/v1/chaos/redirect/done"}),
        httpx.Response(200, json={"redirected": True}),
    )

    response = client.request("POST", "/api/v1/chaos/redirect/1", content="x", follow_redirects=True)

    assert response.json() == {"redirected": True}
    assert [(r.method, r.url.path) for r in wire.requests] == [
        ("POST", "/api/v1/chaos/redirect/1"),
        ("POST", "/api/v1/chaos/redirect/done"),
    ]
    assert wire.attached("Redirect") == ["307 → /api/v1/chaos/redirect/done"]


def test_every_request_is_paced_by_its_method_and_path(wire: Wire) -> None:
    client.post("/api/v1/login", {"email": "a"})

    assert wire.throttled == [("POST", "/api/v1/login")]


def test_a_dropped_connection_is_retried_once_and_re_paced(wire: Wire) -> None:
    wire.reply(_dropped(), httpx.Response(200, json={"status": "ok", "time": "now"}))

    response = client.get(HEALTH)

    assert response.json() == {"status": "ok", "time": "now"}
    assert len(wire.requests) == 2
    assert wire.throttled == [("GET", HEALTH), ("GET", HEALTH)]
    assert wire.attached("Retry") == [
        "Server disconnected without sending a response — retried once on a fresh connection"
    ]


def test_a_second_dropped_connection_is_raised(wire: Wire) -> None:
    wire.reply(_dropped(), _dropped(), httpx.Response(200))

    with pytest.raises(httpx.RemoteProtocolError):
        client.get(HEALTH)

    assert len(wire.requests) == 2


def test_other_transport_errors_are_not_retried(wire: Wire) -> None:
    wire.reply(httpx.ConnectError("refused"), httpx.Response(200))

    with pytest.raises(httpx.ConnectError):
        client.get(HEALTH)

    assert len(wire.requests) == 1
    assert wire.attached("Retry") == []


@pytest.mark.parametrize("status", [429, 503])
def test_error_statuses_are_returned_never_retried(wire: Wire, status: int) -> None:
    wire.reply(httpx.Response(status, json={"success": False, "error": {"code": "X"}}))

    assert client.get(HEALTH).status_code == status
    assert len(wire.requests) == 1


# ─── response attachments ───────────────────────────────────────────────────


def test_status_headers_and_json_body_are_attached(wire: Wire) -> None:
    wire.reply(httpx.Response(400, json={"error": {"code": "É"}}, headers={"x-request-id": "r1"}))

    client.get(HEALTH)

    assert wire.attached("Status") == ["400"]
    assert json.loads(wire.attached("Response Headers")[0])["x-request-id"] == "r1"
    assert wire.attachments[-1] == ('{\n  "error": {\n    "code": "É"\n  }\n}', "Response Body", JSON_KIND)


@pytest.mark.parametrize("content_type", ["text/plain; charset=utf-8", "application/x-yaml", "application/yaml"])
def test_a_non_json_text_body_is_attached_as_text(wire: Wire, content_type: str) -> None:
    wire.reply(httpx.Response(200, content=b"swagger: '2.0'\n{", headers={"content-type": content_type}))

    client.get("/api/v1/openapi.yaml")

    assert wire.attachments[-1] == ("swagger: '2.0'\n{", "Response Body", TEXT_KIND)


def test_a_binary_body_is_summarised(wire: Wire) -> None:
    wire.reply(httpx.Response(200, content=b"\x89PNG\x00", headers={"content-type": "image/png"}))

    response = client.get("/api/v1/files/f1/download")

    assert response.content == b"\x89PNG\x00"
    assert wire.attached("Response Body") == ["<5 bytes, image/png>"]


def test_an_empty_body_attaches_no_body(wire: Wire) -> None:
    wire.reply(httpx.Response(204))

    client.delete("/api/v1/users/delete/u1")

    assert wire.attached("Status") == ["204"]
    assert wire.attached("Response Body") == []


def test_secrets_are_scrubbed_from_every_attachment(wire: Wire) -> None:
    wire.reply(httpx.Response(400, json={"token": "t", "signing_secret": SECRET}))

    client.post("/api/v1/webhooks/in/i1", {"secret": SECRET})

    assert json.loads(wire.attached("Request Body")[0]) == {"secret": "whsec_***"}
    assert json.loads(wire.attached("Response Body")[0]) == {"token": "t", "signing_secret": "whsec_***"}
    assert json_body(wire.last) == {"secret": SECRET}  # only the report is scrubbed, never the wire


@pytest.mark.parametrize(
    ("size", "attached"),
    [
        (64 * 1024, "a" * 64 * 1024),
        (64 * 1024 + 1, "a" * 64 * 1024 + "\n… truncated (65537 chars in total)"),
    ],
)
def test_attach_caps_the_size(wire: Wire, size: int, attached: str) -> None:
    client.attach("a" * size, "Big")

    assert wire.attachments == [(attached, "Big", TEXT_KIND)]


# ─── 2xx contract ───────────────────────────────────────────────────────────


def test_a_valid_2xx_body_passes_its_contract(wire: Wire) -> None:
    wire.reply(httpx.Response(200, json={"status": "ok", "time": "t"}))

    assert client.get(HEALTH).json() == {"status": "ok", "time": "t"}
    assert wire.steps == [f"GET {HEALTH}", "Contract: HealthResponse"]


@pytest.mark.parametrize("status", [200, 201, 299])
def test_a_2xx_body_breaking_its_contract_raises_with_the_response(wire: Wire, status: int) -> None:
    wire.reply(httpx.Response(status, json={"status": SECRET}))

    with pytest.raises(ContractViolation) as caught:
        client.get(HEALTH)

    assert caught.value.response.status_code == status
    assert caught.value.response.json() == {"status": SECRET}
    message = str(caught.value)
    assert message.startswith("HealthResponse contract violated:")
    assert "time" in message
    assert SECRET not in message
    assert "whsec_***" in message


@pytest.mark.parametrize(
    ("method", "path", "status"),
    [
        ("GET", HEALTH, 300),  # not 2xx
        ("GET", HEALTH, 400),
        ("GET", HEALTH, 199),
        ("POST", HEALTH, 200),  # no contract for this method
        ("GET", "/api/v1/files/f1/download", 200),  # no contract for this path
    ],
)
def test_no_contract_is_checked_outside_documented_2xx(wire: Wire, method: str, path: str, status: int) -> None:
    wire.reply(httpx.Response(status, json={"unexpected": True}))

    assert client.request(method, path).json() == {"unexpected": True}
    assert not any(step.startswith("Contract") for step in wire.steps)


def test_a_2xx_non_json_body_is_not_contract_checked(wire: Wire) -> None:
    wire.reply(httpx.Response(200, text="ok", headers={"content-type": "text/plain"}))

    assert client.get(HEALTH).text == "ok"
    assert wire.steps == [f"GET {HEALTH}"]


# ─── stream ─────────────────────────────────────────────────────────────────


def _chunks() -> Iterator[bytes]:
    yield b"data: 1\n"
    yield b"data: 2\n"


def test_stream_is_paced_attached_and_yields_the_unread_response(wire: Wire) -> None:
    wire.reply(httpx.Response(200, content=_chunks()))

    with client.stream(
        "GET", "/api/v1/sse/progress", params=[("steps", "5")], headers={"Last-Event-ID": " 3 "}
    ) as response:
        lines = list(response.iter_lines())

    assert lines == ["data: 1", "data: 2"]
    assert (wire.last.method, wire.last.url.path, query(wire.last)) == ("GET", "/api/v1/sse/progress", [("steps", "5")])
    assert caller_headers(wire.last) == [("last-event-id", "3")]
    assert wire.throttled == [("GET", "/api/v1/sse/progress")]
    assert wire.steps == ["GET /api/v1/sse/progress (stream)"]
    assert [name for _, name, _ in wire.attachments] == ["Query Params", "Request Headers", "Status"]
    assert wire.attached("Status") == ["200"]
