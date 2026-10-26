"""`X-PlayQA-Signature: t=<unix>,v1=<hex hmac_sha256(secret, "<t>.<raw body>")>` — Stripe-style.

The server accepts a timestamp within ±300 s (undocumented; verified live: ±240 s valid, ±310 s invalid).
"""

from __future__ import annotations

import hashlib
import hmac
import time


def signature(secret: str, body: str, timestamp: int | None = None) -> str:
    t = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), f"{t}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={t},v1={digest}"


def header_for(kind: str, secret: str, body: str) -> dict[str, str]:
    """valid | wrong hmac | stale timestamp | future timestamp | garbage | empty | none"""
    now = int(time.time())
    values = {
        "valid": signature(secret, body, now),
        "wrong hmac": signature("whsec_" + "0" * 32, body, now),
        "stale timestamp": signature(secret, body, now - 600),
        "future timestamp": signature(secret, body, now + 600),
        "garbage": "garbage",
        "empty": "",
    }
    if kind == "none":
        return {}
    assert kind in values, f"unknown signature kind '{kind}', expected none or one of {sorted(values)}"
    return {"X-PlayQA-Signature": values[kind]}
