"""JWT crafting for negative tests — stdlib only (no PyJWT): the server's secret is unknown, so every
token built here either has a WRONG signature or is malformed on purpose.

`craft(kind, genuine)` derives a broken token from a genuine one (so claims such as `sub` stay real):

  wrong secret | tampered payload | alg none | alg HS512 | forged expired  → 401 INVALID_SIGNATURE
  one/two/four segments | garbage | padded | bad base64 | non-JSON payload
  | oversized (> 8 KiB) | opaque                                            → 401 INVALID_TOKEN_FORMAT
                                                                              (400 INVALID_JWT_FORMAT on /decode)
  no exp | exp string | empty object                                       → decode-only shapes
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from typing import Any

_WRONG_SECRET = b"not-the-server-secret"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_json(obj: Any) -> str:
    return b64url(json.dumps(obj, separators=(",", ":")).encode())


def _unb64url(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def parts(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """(header, payload) of a JWT, signature NOT verified."""
    header, payload, _ = token.split(".")
    return json.loads(_unb64url(header)), json.loads(_unb64url(payload))


def sign(header: dict[str, Any], payload: dict[str, Any], secret: bytes = _WRONG_SECRET) -> str:
    signing_input = f"{_b64url_json(header)}.{_b64url_json(payload)}"
    digest = hashlib.sha512 if header.get("alg") == "HS512" else hashlib.sha256
    signature = hmac.new(secret, signing_input.encode(), digest).digest()
    return f"{signing_input}.{b64url(signature)}"


def _with_payload(token: str, **changes: Any) -> str:
    """Keep the genuine header + signature, swap the payload → signature no longer matches."""
    _, payload = parts(token)
    head, _, signature = token.split(".")
    return f"{head}.{_b64url_json({**payload, **changes})}.{signature}"


def _alg_none(token: str) -> str:
    header, payload = parts(token)
    return f"{_b64url_json({**header, 'alg': 'none'})}.{_b64url_json(payload)}."


def _expired(token: str) -> str:
    header, payload = parts(token)
    now = int(time.time())
    return sign(header, {**payload, "iat": now - 7200, "exp": now - 3600})


def _claims_only(token: str, **changes: Any) -> str:
    header, payload = parts(token)
    payload = {k: v for k, v in {**payload, **changes}.items() if v is not None}
    return sign(header, payload)


_KINDS: dict[str, Callable[[str], str]] = {
    # wrong signature
    "wrong secret": lambda t: sign(*parts(t)),
    "tampered payload": lambda t: _with_payload(t, email="attacker@play-qa.com"),
    "alg none": _alg_none,
    "alg HS512": lambda t: sign({**parts(t)[0], "alg": "HS512"}, parts(t)[1]),
    "forged expired": _expired,
    # malformed
    "one segment": lambda t: t.split(".")[0],
    "two segments": lambda t: ".".join(t.split(".")[:2]),
    "four segments": lambda t: f"{t}.{t.split('.')[2]}",
    "garbage": lambda _t: "not-a-jwt-at-all",
    "padded": lambda t: f"{t}==",
    "bad base64": lambda t: "!!!." + t.split(".", 1)[1],
    "non-JSON payload": lambda t: f"{t.split('.')[0]}.{b64url(b'not json')}.{t.split('.')[2]}",
    "oversized": lambda t: f"{t.split('.')[0]}.{b64url(b'x' * 6300)}.{t.split('.')[2]}",  # ≈ 8.4 KiB < CF 520
    "opaque": lambda _t: "usr_1700000000_0123456789abcdef0123456789abcdef",
    # decode-only shapes
    "no exp": lambda t: _claims_only(t, exp=None),
    "exp string": lambda t: _claims_only(t, exp="tomorrow"),
    "empty object": lambda _t: "e30.e30.e30",
}


def craft(kind: str, genuine: str) -> str:
    assert kind in _KINDS, f"unknown JWT kind '{kind}', expected one of {list(_KINDS)}"
    return _KINDS[kind](genuine)
