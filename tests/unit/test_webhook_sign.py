from __future__ import annotations

import hashlib
import hmac
import time

import pytest

from play_api.utils.webhook_sign import SIGNED_BODY, header_for, signature

NOW = 1_800_000_000
SECRET = "whsec_test"


def _v1(secret: str, body: str, timestamp: int) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()


@pytest.fixture(autouse=True)
def _frozen_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(time, "time", lambda: NOW + 0.7)


def test_signature_is_stripe_style_hmac_sha256_over_timestamp_dot_body() -> None:
    assert signature(SECRET, SIGNED_BODY, NOW) == f"t={NOW},v1={_v1(SECRET, SIGNED_BODY, NOW)}"


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("valid", f"t={NOW},v1={_v1(SECRET, SIGNED_BODY, NOW)}"),
        ("wrong hmac", f"t={NOW},v1={_v1('whsec_' + '0' * 32, SIGNED_BODY, NOW)}"),
        ("stale timestamp", f"t={NOW - 600},v1={_v1(SECRET, SIGNED_BODY, NOW - 600)}"),
        ("future timestamp", f"t={NOW + 600},v1={_v1(SECRET, SIGNED_BODY, NOW + 600)}"),
        ("garbage", "garbage"),
        ("empty", ""),
    ],
)
def test_header_for_each_kind(kind: str, value: str) -> None:
    assert header_for(kind, SECRET, SIGNED_BODY) == {"X-PlayQA-Signature": value}


def test_none_sends_no_header_at_all() -> None:
    assert header_for("none", SECRET, SIGNED_BODY) == {}


def test_an_unknown_kind_is_rejected() -> None:
    with pytest.raises(AssertionError, match=r"^unknown signature kind \(or none\) 'bogus', expected one of "):
        header_for("bogus", SECRET, SIGNED_BODY)
