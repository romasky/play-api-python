"""`X-PlayQA-Signature: t=<unix>,v1=<hex hmac_sha256(secret, "<t>.<raw body>")>` — Stripe-style.

The server accepts a timestamp within ±300 s (undocumented; verified live: ±240 s valid, ±310 s invalid).
"""

from __future__ import annotations

import hashlib
import hmac
import time

from play_api.utils.lookup import choose

# the payload the signature scenarios send (signed over these exact bytes)
SIGNED_BODY = '{"event":"signed"}'
_FOREIGN_SECRET = "whsec_" + "0" * 32  # well-formed, but not the inbox's secret
_SKEW = 600  # seconds — twice the server's ±300 s tolerance


def signature(secret: str, body: str, timestamp: int) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def header_for(kind: str, secret: str, body: str) -> dict[str, str]:
    """valid | wrong hmac | stale timestamp | future timestamp | garbage | empty | none"""
    now = int(time.time())
    stale, future = now - _SKEW, now + _SKEW
    values = {
        "valid": signature(secret, body, now),
        "wrong hmac": signature(_FOREIGN_SECRET, body, now),
        "stale timestamp": signature(secret, body, stale),
        "future timestamp": signature(secret, body, future),
        "garbage": "garbage",
        "empty": "",
    }
    if kind == "none":
        return {}
    return {"X-PlayQA-Signature": choose(values, kind, "signature kind (or none)")}
