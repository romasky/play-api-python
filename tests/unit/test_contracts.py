"""Response contracts — the registry `client.request()` consults and the declarative shapes themselves.

Every MINIMAL body below holds exactly the always-present fields of its contract: the table tests prove each
passes, that dropping any one key fails, that int/bool fields are strict and that unknown fields are allowed.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from play_api.api import paths
from play_api.models.responses import (
    admin,
    auth,
    bug_reports,
    buggy,
    challenges,
    chaos,
    contract_for,
    files,
    mail,
    system,
    users,
    webhooks,
)
from play_api.models.responses.base import Contract, Entry, ErrorDetails, ErrorEnvelope

# ─── minimal bodies (shared with test_contract_asserts.py) ─────────────────

ERROR = {"success": False, "error": {"code": "VALIDATION_ERROR"}}
USER = {"id": "u1", "email": "a@b.c", "username": "user_a", "profile": {}, "metadata": {}}
USERS_LIST = {"users": [], "page": 1, "per_page": 20, "total": 0, "total_pages": 0}
ROLE_COUNTS = {"admin": 1, "moderator": 0, "user": 2}
ADMIN_STATS = {"total": 3, "by_role": ROLE_COUNTS, "with_active_token": 1, "generated_at": "2026-10-28T00:00:00Z"}
LOGIN = {"success": True, "access_token": "t", "user_id": "u", "email": "e", "username": "n", "expires_at": "x"}
JWT_LOGIN = {
    "success": True,
    "token_type": "Bearer",
    "access_token": "a",
    "refresh_token": "r",
    "access_expires_in": 900,
    "refresh_expires_in": 86400,
    "user_id": "u",
    "email": "e",
}
JWT_DECODE = {
    "success": True,
    "header": {},
    "payload": {},
    "signature_valid": None,
    "expired": None,
    "expires_at": None,
    "issued_at": None,
}
STORE_BEHAVIOR = {"login_latency_ms": 0, "catalog_latency_ms": 0, "visual_bugs": False, "flaky_add_to_cart": False}
FEEDBACK_OK = {"criterion": "steps", "ok": True, "key": "k"}
SCORE = {"total": 100, "max": 100, "breakdown": {"steps": 20}, "feedback": [FEEDBACK_OK]}
BUG_REPORT_DETAIL = {
    "success": True,
    "report_id": "r",
    "bug_id": "b",
    "title": "t",
    "steps": ["s"],
    "expected": "e",
    "actual": "a",
    "severity": "low",
    "score": SCORE,
    "created_at": "c",
    "expires_at": "x",
}
BUG_ENTRY = {"bug_id": "b", "method": "GET", "path": "/buggy", "title": "t", "description": "d", "expected": "e"}
BUGGY_ITEM = {"id": 1, "sku": "S1", "name": "n", "price": 1.25}
BUGGY_ITEMS = {"success": True, "bug_id": "b", "page": 1, "per_page": 10, "total": 1, "items": [BUGGY_ITEM]}
CHALLENGE = {
    "id": "c",
    "title": "t",
    "description": "d",
    "category": "auth",
    "difficulty": "easy",
    "points": 10,
    "hint_count": 3,
    "params": [],
}
FLAKY_STEP = {"index": 0, "roll": 0.5, "status": 200, "failed": False}
FILE_ITEM = {
    "file_id": "f",
    "filename": "a.png",
    "size": 1,
    "content_type": "image/png",
    "declared_type": "image/png",
    "description": "",
    "download_url": "/d",
    "created_at": "c",
    "expires_at": "x",
}
MAILBOX = {"id": "m", "token": "t", "email_address": "a@b.c", "domain": "b.c", "expires_at": "x", "created_at": "c"}
MESSAGE = {"id": "m", "from": "a@b.c", "subject": "s", "body_preview": "p", "body": "b", "received_at": "r"}
WEBHOOK_INBOX = {
    "id": "w",
    "token": "t",
    "ingest_token": "i",
    "ingest_url": "/in/i",
    "event_count": 0,
    "total_received": 0,
    "dropped_count": 0,
    "created_at": "c",
    "expires_at": "x",
}
EVENT_SUMMARY = {
    "id": "e",
    "method": "POST",
    "content_type": "application/json",
    "body_size": 0,
    "body_encoding": "utf8",
    "signature_valid": None,
    "received_at": "r",
}

MINIMAL: list[tuple[type[Contract], dict[str, Any]]] = [
    (ErrorDetails, {"code": "X"}),
    (ErrorEnvelope, ERROR),
    (users.UserResponse, USER),
    (users.UsersListResponse, USERS_LIST),
    (users.LogoutResponse, {"success": True, "message": "m"}),
    (admin.RoleCounts, ROLE_COUNTS),
    (admin.AdminStatsResponse, ADMIN_STATS),
    (admin.AdminUsersListResponse, USERS_LIST),
    (auth.LoginResponse, LOGIN),
    (auth.BasicAuthResponse, {"success": True, "message": "m", "user": "admin"}),
    (auth.JwtLoginResponse, JWT_LOGIN),
    (
        auth.JwtRefreshResponse,
        {"success": True, "token_type": "Bearer", "access_token": "a", "access_expires_in": 900},
    ),
    (auth.JwtMeResponse, {"success": True, "sub": "u", "email": "e", "claims": {}}),
    (auth.JwtDecodeResponse, JWT_DECODE),
    (auth.StoreBehavior, STORE_BEHAVIOR),
    (
        auth.StoreLoginResponse,
        {"success": True, "persona": "p", "session": "s", "behavior": STORE_BEHAVIOR, "message": "m"},
    ),
    (bug_reports.ScoreFeedback, FEEDBACK_OK),
    (bug_reports.Score, SCORE),
    (
        bug_reports.BugReportSubmitted,
        {"success": True, "bug_id": "b", "owner": "anonymous", "saved": False, "created_at": "c", "score": SCORE},
    ),
    (bug_reports.BugReportsList, {"success": True, "user_id": "u", "total": 0, "returned": 0, "reports": []}),
    (bug_reports.BugReportDetail, BUG_REPORT_DETAIL),
    (buggy.BugEntry, BUG_ENTRY),
    (buggy.BuggyCatalogResponse, {"success": True, "total": 1, "bugs": [BUG_ENTRY]}),
    (buggy.BuggyItem, BUGGY_ITEM),
    (buggy.BuggyItemsResponse, BUGGY_ITEMS),
    (buggy.CartTotalResponse, {"success": True, "bug_id": "b", "items_count": 1, "currency": "USD", "total": 0.3}),
    (
        buggy.ScheduleResponse,
        {
            "success": True,
            "bug_id": "b",
            "requested_date": "d",
            "tz": "UTC",
            "event_local": "l",
            "event_start": "s",
            "event_start_utc": "u",
        },
    ),
    (challenges.Challenge, CHALLENGE),
    (challenges.ChallengesResponse, {"success": True, "total": 1, "challenges": [CHALLENGE]}),
    (
        challenges.ProgressResponse,
        {
            "success": True,
            "user_id": "u",
            "solved_count": 0,
            "total_challenges": 1,
            "total_points": 0,
            "solved": [],
            "hints": [],
        },
    ),
    (challenges.HintLevel, {"level": 1, "kind": "text"}),
    (
        challenges.HintsResponse,
        {"success": True, "challenge_id": "c", "hint_count": 1, "levels": [{"level": 1, "kind": "text"}]},
    ),
    (
        challenges.RevealResponse,
        {
            "success": True,
            "challenge_id": "c",
            "level": 1,
            "kind": "text",
            "hint": "h",
            "revealed_count": 1,
            "hint_count": 3,
            "has_more": True,
            "revealed": [],
        },
    ),
    (
        challenges.StartResponse,
        {"success": True, "challenge_id": "c", "already_solved": False, "attempt_id": "a", "status": "open"},
    ),
    (
        challenges.VerifyResponse,
        {
            "success": True,
            "challenge_id": "c",
            "solved": True,
            "already_solved": False,
            "points_awarded": 10,
            "attempt_id": "a",
        },
    ),
    (chaos.CacheResponse, {"etag": "e"}),
    (chaos.DelayResponse, {"delayed_seconds": 1.5, "clamped": False}),
    (
        chaos.EchoResponse,
        {
            "method": "GET",
            "path": "/p",
            "headers": {},
            "query": {},
            "body": None,
            "raw_body": None,
            "truncated": False,
            "client_ip": "1.2.3.4",
            "request_id": "r",
        },
    ),
    (chaos.FlakyResponse, {"ok": True, "failed": False, "deterministic": False, "seed": None, "roll": 0.5}),
    (chaos.FlakyStep, FLAKY_STEP),
    (
        chaos.FlakySequenceResponse,
        {
            "seed": "s",
            "count": 1,
            "fail_rate": 0.5,
            "fail_status": 503,
            "steps": [FLAKY_STEP],
            "first_success_index": 0,
            "fails_total": 0,
        },
    ),
    (chaos.FlakyStepResponse, {**FLAKY_STEP, "seed": "s"}),
    (chaos.GzipResponse, {"gzipped": True, "origin": "o", "method": "GET"}),
    (
        chaos.RedirectDoneResponse,
        {"redirected": True, "method": "GET", "body_length": 0, "body_sha256": "h", "message": "m"},
    ),
    (chaos.StatusResponse, {"status_code": 200, "message": "OK"}),
    (files.FileItem, FILE_ITEM),
    (files.FileUploadResponse, {**FILE_ITEM, "success": True, "owner": "anonymous"}),
    (files.FileMetadataResponse, {**FILE_ITEM, "success": True}),
    (files.FilesListResponse, {"success": True, "total": 1, "returned": 1, "files": [FILE_ITEM]}),
    (mail.MailboxResponse, MAILBOX),
    (mail.MessagesListResponse, {"messages": [], "count": 0}),
    (mail.MessageResponse, MESSAGE),
    (
        mail.SendToResponse,
        {"accepted": True, "to": "a@b.c", "smtp_code": "250", "category": "accepted", "message": "m"},
    ),
    (system.HealthResponse, {"status": "ok", "time": "t"}),
    (system.OpenApiDocument, {"swagger": "2.0", "basePath": "/api/v1", "info": {}, "paths": {}}),
    (system.PostmanCollection, {"info": {}, "item": [], "variable": []}),
    (system.PostmanEnvironment, {"name": "n", "values": []}),
    (system.RecaptchaVerifyResponse, {"success": False}),
    (webhooks.WebhookInbox, WEBHOOK_INBOX),
    (webhooks.WebhookInboxCreated, {**WEBHOOK_INBOX, "signing_secret": "s"}),
    (webhooks.IngestAccepted, {"received": True, "event_id": "e"}),
    (webhooks.EventSummary, EVENT_SUMMARY),
    (
        webhooks.EventsListResponse,
        {"events": [EVENT_SUMMARY], "total": 1, "returned": 1, "page": 1, "per_page": 20, "dropped_count": 0},
    ),
    (
        webhooks.WebhookEvent,
        {
            "id": "e",
            "method": "POST",
            "path": "/in/i",
            "headers": {"X": ["1"]},
            "content_type": "text/plain",
            "body_size": 0,
            "body_encoding": "utf8",
            "signature_valid": None,
            "received_at": "r",
        },
    ),
]


def _name(contract: type[Contract]) -> str:
    return contract.__name__


def test_every_contract_class_has_a_minimal_body() -> None:
    modules = (admin, auth, bug_reports, buggy, challenges, chaos, files, mail, system, users, webhooks)
    declared = {
        obj
        for module in modules
        for obj in vars(module).values()
        if isinstance(obj, type) and issubclass(obj, Contract) and obj.__module__ == module.__name__
    }
    assert declared - {c for c, _ in MINIMAL} == set()


@pytest.mark.parametrize(("contract", "body"), MINIMAL, ids=[_name(c) for c, _ in MINIMAL])
def test_minimal_body_passes_and_parses(contract: type[Contract], body: dict[str, Any]) -> None:
    parsed = contract.check(body)
    assert isinstance(parsed, contract)
    assert parsed.model_dump(by_alias=True, include=set(contract.model_fields), exclude_unset=True) == body


DROPS = [(c, body, key) for c, body in MINIMAL for key in body]


@pytest.mark.parametrize(("contract", "body", "key"), DROPS, ids=[f"{_name(c)}-{k}" for c, _, k in DROPS])
def test_every_always_present_field_is_required(contract: type[Contract], body: dict[str, Any], key: str) -> None:
    with pytest.raises(AssertionError, match=rf"{_name(contract)} contract violated:(.|\n)*{key}"):
        contract.check({k: v for k, v in body.items() if k != key})


def _stringified(value: Any) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


SCALARS = [(c, body, key) for c, body in MINIMAL for key, value in body.items() if isinstance(value, bool | int)]


@pytest.mark.parametrize(("contract", "body", "key"), SCALARS, ids=[f"{_name(c)}-{k}" for c, _, k in SCALARS])
def test_int_and_bool_fields_are_strict(contract: type[Contract], body: dict[str, Any], key: str) -> None:
    with pytest.raises(AssertionError, match=key):
        contract.check({**body, key: _stringified(body[key])})  # "900" is not an int, "true" not a bool


@pytest.mark.parametrize(("contract", "body"), MINIMAL, ids=[_name(c) for c, _ in MINIMAL])
def test_unknown_fields_are_allowed_and_kept(contract: type[Contract], body: dict[str, Any]) -> None:
    parsed = contract.check({**body, "added_later": [1]})
    assert parsed.model_extra == {"added_later": [1]}


@pytest.mark.parametrize(
    ("contract", "body"),
    [
        (chaos.DelayResponse, {"delayed_seconds": 2, "clamped": True}),  # an int satisfies a float field
        (auth.JwtDecodeResponse, {**JWT_DECODE, "signature_valid": True, "expired": False, "expires_at": "x"}),
        (bug_reports.ScoreFeedback, {**FEEDBACK_OK, "params": {"min": "2"}}),
        (system.RecaptchaVerifyResponse, {"success": False, "error_codes": ["invalid-input-response"]}),
        (webhooks.WebhookEvent, {**MINIMAL[-1][1], "query": {"a": ["1"]}, "body": "x"}),
        (mail.MessageResponse, {**MESSAGE, "html_body": None, "headers": {"To": "x"}}),
    ],
)
def test_optional_and_nullable_fields_accept_their_documented_values(
    contract: type[Contract], body: dict[str, Any]
) -> None:
    contract.check(body)


@pytest.mark.parametrize(
    ("contract", "body", "field"),
    [
        (auth.LoginResponse, {**LOGIN, "success": 1}, "success"),  # 1 is not a bool
        (users.UsersListResponse, {**USERS_LIST, "page": 1.0}, "page"),  # 1.0 is not an int
        (chaos.DelayResponse, {"delayed_seconds": "1.5", "clamped": False}, "delayed_seconds"),
        (mail.MessageResponse, {**MESSAGE, "from_": "a@b.c", "from": None}, "from"),
        (bug_reports.Score, {**SCORE, "feedback": [{"criterion": "c", "ok": "yes", "key": "k"}]}, "ok"),
    ],
)
def test_strictness_reaches_floats_aliases_and_nested_models(
    contract: type[Contract], body: dict[str, Any], field: str
) -> None:
    with pytest.raises(AssertionError, match=field):
        contract.check(body)


@pytest.mark.parametrize("body", [None, [], "<!DOCTYPE html>", 42])
def test_a_non_object_body_violates_the_contract_and_is_quoted(body: Any) -> None:
    with pytest.raises(
        AssertionError, match=rf"^HealthResponse contract violated:\n(.|\n)*\nBody: {re.escape(str(body))}$"
    ):
        system.HealthResponse.check(body)


# ─── registry: contract_for(method, path) as client.request() calls it ─────

ROUTED: list[tuple[str, str, type[Contract]]] = [
    ("GET", paths.HEALTH, system.HealthResponse),
    ("GET", paths.API_DOCUMENTS["OpenAPI JSON"], system.OpenApiDocument),
    ("GET", paths.API_DOCUMENTS["Postman collection"], system.PostmanCollection),
    ("GET", paths.API_DOCUMENTS["Postman environment"], system.PostmanEnvironment),
    ("POST", paths.VERIFY_RECAPTCHA, system.RecaptchaVerifyResponse),
    ("POST", paths.USERS_CREATE, users.UserResponse),
    ("GET", paths.USERS_LIST, users.UsersListResponse),
    ("GET", paths.users_get("u1"), users.UserResponse),
    ("PUT", paths.users_update("u1"), users.UserResponse),
    ("PATCH", paths.users_patch("u1"), users.UserResponse),
    ("POST", paths.users_logout("u1"), users.LogoutResponse),
    ("POST", paths.LOGIN, auth.LoginResponse),
    ("GET", paths.AUTH_BASIC, auth.BasicAuthResponse),
    ("POST", paths.JWT_LOGIN, auth.JwtLoginResponse),
    ("POST", paths.JWT_REFRESH, auth.JwtRefreshResponse),
    ("GET", paths.JWT_ME, auth.JwtMeResponse),
    ("POST", paths.JWT_DECODE, auth.JwtDecodeResponse),
    ("POST", paths.STORE_LOGIN, auth.StoreLoginResponse),
    ("POST", paths.USERS_CREATE_ADMIN, users.UserResponse),
    ("GET", paths.ADMIN_STATS, admin.AdminStatsResponse),
    ("GET", paths.ADMIN_USERS, admin.AdminUsersListResponse),
    ("PATCH", paths.admin_user_role("u1"), users.UserResponse),
    ("POST", paths.MAIL_CREATE, mail.MailboxResponse),
    ("GET", paths.mail_get("tok"), mail.MailboxResponse),
    ("GET", paths.mail_messages("tok"), mail.MessagesListResponse),
    ("GET", paths.mail_message("tok", "m1"), mail.MessageResponse),
    ("POST", paths.mail_send("tok"), mail.MessageResponse),
    ("POST", paths.mail_send_to("tok"), mail.SendToResponse),
    ("POST", paths.FILES_UPLOAD, files.FileUploadResponse),
    ("GET", paths.FILES, files.FilesListResponse),
    ("GET", paths.file("f1"), files.FileMetadataResponse),
    ("POST", paths.WEBHOOKS_INBOX, webhooks.WebhookInboxCreated),
    ("GET", paths.webhook("tok"), webhooks.WebhookInbox),
    ("GET", paths.webhook_events("tok"), webhooks.EventsListResponse),
    ("GET", paths.webhook_event("tok", "e1"), webhooks.WebhookEvent),
    *((m, paths.webhook_ingest("ing"), webhooks.IngestAccepted) for m in ("GET", "POST", "PUT", "PATCH", "DELETE")),
    ("POST", paths.BUG_REPORTS, bug_reports.BugReportSubmitted),
    ("GET", paths.BUG_REPORTS, bug_reports.BugReportsList),
    ("GET", paths.bug_report("r1"), bug_reports.BugReportDetail),
    ("GET", paths.BUGGY, buggy.BuggyCatalogResponse),
    ("GET", paths.BUGGY_ITEMS, buggy.BuggyItemsResponse),
    ("POST", paths.BUGGY_CART_TOTAL, buggy.CartTotalResponse),
    ("GET", paths.BUGGY_SCHEDULE, buggy.ScheduleResponse),
    ("GET", paths.CHALLENGES, challenges.ChallengesResponse),
    ("GET", paths.CHALLENGES_PROGRESS, challenges.ProgressResponse),
    ("GET", paths.challenge_hints("c1"), challenges.HintsResponse),
    ("POST", paths.challenge_reveal("c1"), challenges.RevealResponse),
    ("POST", paths.challenge_start("c1"), challenges.StartResponse),
    ("POST", paths.challenge_verify("c1"), challenges.VerifyResponse),
    ("GET", paths.CHAOS_CACHE, chaos.CacheResponse),
    ("GET", paths.chaos_delay("2"), chaos.DelayResponse),
    ("GET", paths.CHAOS_ECHO, chaos.EchoResponse),
    ("POST", paths.CHAOS_ECHO, chaos.EchoResponse),
    ("GET", paths.CHAOS_FLAKY, chaos.FlakyResponse),
    ("GET", paths.CHAOS_FLAKY_SEQUENCE, chaos.FlakySequenceResponse),
    ("GET", paths.chaos_flaky_step("3"), chaos.FlakyStepResponse),
    ("GET", paths.CHAOS_GZIP, chaos.GzipResponse),
    ("GET", paths.chaos_redirect("done"), chaos.RedirectDoneResponse),
    ("POST", paths.chaos_redirect("done"), chaos.RedirectDoneResponse),
    ("GET", paths.chaos_status("200"), chaos.StatusResponse),
]


@pytest.mark.parametrize(("method", "path", "contract"), ROUTED, ids=[f"{m} {p}" for m, p, _ in ROUTED])
def test_contract_for_picks_the_endpoint_contract(method: str, path: str, contract: type[Contract]) -> None:
    assert contract_for(method, path) is contract


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("DELETE", paths.users_delete("u1")),  # 204, no body
        ("HEAD", paths.users_exists("u1")),
        ("GET", paths.file_download("f1")),  # raw bytes
        ("GET", paths.API_DOCUMENTS["OpenAPI YAML"]),
        ("GET", paths.chaos_redirect("3")),
        ("POST", paths.HEALTH),  # right path, wrong method
        ("GET", "/health"),  # no /api/v1 prefix
        ("GET", f"{paths.HEALTH}/extra"),  # anchored at the end
        ("GET", "/api/v1/healthz"),
        ("GET", "/api/v1/openapi_json"),  # the dot is literal
        ("get", paths.HEALTH),  # methods are upper case, as client.request() passes them
    ],
)
def test_contract_for_returns_none_for_endpoints_without_a_json_contract(method: str, path: str) -> None:
    assert contract_for(method, path) is None


REGISTRY: list[Entry] = [
    row
    for module in (system, users, auth, admin, mail, files, webhooks, bug_reports, buggy, challenges, chaos)
    for row in module.CONTRACTS_2XX
]


def _sample_path(pattern: re.Pattern[str]) -> str:
    return pattern.pattern.removesuffix("$").replace("[^/]+", "x1").replace(r"\.", ".")


@pytest.mark.parametrize(("method", "pattern", "contract"), REGISTRY, ids=[f"{m} {p.pattern}" for m, p, _ in REGISTRY])
def test_no_registry_row_is_shadowed_by_a_broader_template(
    method: str, pattern: re.Pattern[str], contract: type[Contract]
) -> None:
    assert contract_for(method, _sample_path(pattern)) is contract
