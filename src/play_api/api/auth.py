"""Authorization header builders — the heart of the negative coverage (see CLAUDE.md):

bearer(token) → "Bearer <token>"   wrong/revoked token → INVALID_TOKEN, another user's → FORBIDDEN
raw(value)    → verbatim value     malformed           → INVALID_TOKEN_FORMAT
none()        → no header          missing             → MISSING_TOKEN
"""

from __future__ import annotations

import base64

Headers = dict[str, str]


def bearer(token: str | None) -> Headers:
    if token is None:
        raise ValueError("auth.bearer: token is None")
    return {"Authorization": token if token.startswith("Bearer ") else f"Bearer {token}"}


def raw(value: str) -> Headers:
    return {"Authorization": value}


def none() -> Headers:
    return {}


def basic(user_pass: str) -> Headers:
    return {"Authorization": f"Basic {base64.b64encode(user_pass.encode()).decode()}"}
