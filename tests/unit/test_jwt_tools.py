from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import pytest

from play_api.utils.jwt_tools import craft, parts

NOW = 1_800_000_000
HEADER = {"alg": "HS256", "typ": "JWT"}
PAYLOAD = {"sub": "usr_1", "email": "ann@play-qa.com", "iat": NOW - 60, "exp": NOW + 840}


def _seg(obj: Any) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode()).rstrip(b"=").decode()


def _raw(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


GENUINE = f"{_seg(HEADER)}.{_seg(PAYLOAD)}.{_seg('server-signature')}"
HEAD, BODY, SIG = GENUINE.split(".")


def _signed_with_wrong_secret(token: str, digest: Any) -> bool:
    head, body, sig = token.split(".")
    expected = hmac.new(b"not-the-server-secret", f"{head}.{body}".encode(), digest).digest()
    return _raw(sig) == expected and "=" not in sig


@pytest.fixture(autouse=True)
def _frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: NOW + 0.9)


def test_parts_decodes_header_and_payload_without_verifying() -> None:
    assert parts(GENUINE) == (HEADER, PAYLOAD)


def test_wrong_secret_keeps_the_claims_and_signs_with_a_foreign_hs256_key() -> None:
    token = craft("wrong secret", GENUINE)
    assert parts(token) == (HEADER, PAYLOAD)
    assert _signed_with_wrong_secret(token, hashlib.sha256)


def test_tampered_payload_swaps_only_the_email_and_keeps_the_genuine_signature() -> None:
    head, body, sig = craft("tampered payload", GENUINE).split(".")
    assert (head, sig) == (HEAD, SIG)
    assert json.loads(_raw(body)) == {**PAYLOAD, "email": "attacker@play-qa.com"}


def test_alg_none_has_an_empty_signature() -> None:
    token = craft("alg none", GENUINE)
    assert parts(token) == ({**HEADER, "alg": "none"}, PAYLOAD)
    assert token.endswith(".")
    assert token.count(".") == 2


def test_alg_hs512_is_signed_with_sha512() -> None:
    token = craft("alg HS512", GENUINE)
    assert parts(token) == ({**HEADER, "alg": "HS512"}, PAYLOAD)
    assert _signed_with_wrong_secret(token, hashlib.sha512)


def test_forged_expired_expired_an_hour_ago() -> None:
    token = craft("forged expired", GENUINE)
    assert parts(token) == (HEADER, {**PAYLOAD, "iat": NOW - 7200, "exp": NOW - 3600})
    assert _signed_with_wrong_secret(token, hashlib.sha256)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("one segment", HEAD),
        ("two segments", f"{HEAD}.{BODY}"),
        ("four segments", f"{GENUINE}.{SIG}"),
        ("garbage", "not-a-jwt-at-all"),
        ("padded", f"{GENUINE}=="),
        ("bad base64", f"!!!.{BODY}.{SIG}"),
        ("non-JSON payload", f"{HEAD}.{base64.urlsafe_b64encode(b'not json').rstrip(b'=').decode()}.{SIG}"),
        ("opaque", "usr_1700000000_0123456789abcdef0123456789abcdef"),
        ("empty object", "e30.e30.e30"),
    ],
)
def test_malformed_kinds(kind: str, expected: str) -> None:
    assert craft(kind, GENUINE) == expected


def test_empty_object_decodes_to_empty_header_and_payload() -> None:
    assert parts(craft("empty object", GENUINE)) == ({}, {})


def test_oversized_carries_a_payload_over_8_kib_but_stays_under_the_cloudflare_limit() -> None:
    head, body, sig = craft("oversized", GENUINE).split(".")
    assert (head, sig) == (HEAD, SIG)
    assert _raw(body) == b"x" * 6300
    assert 8 * 1024 < len(f"{head}.{body}.{sig}") < 12 * 1024


def test_no_exp_drops_exp_and_null_claims_but_keeps_the_rest() -> None:
    genuine = f"{HEAD}.{_seg({**PAYLOAD, 'nickname': None})}.{SIG}"
    token = craft("no exp", genuine)
    assert parts(token) == (HEADER, {k: v for k, v in PAYLOAD.items() if k != "exp"})
    assert _signed_with_wrong_secret(token, hashlib.sha256)


def test_exp_string_replaces_exp_with_text() -> None:
    assert parts(craft("exp string", GENUINE))[1] == {**PAYLOAD, "exp": "tomorrow"}


def test_an_unknown_kind_is_rejected_with_the_valid_names() -> None:
    with pytest.raises(AssertionError, match=r"^unknown JWT kind 'nope', expected one of \['alg HS512', "):
        craft("nope", GENUINE)
