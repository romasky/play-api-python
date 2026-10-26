"""Run-wide shared credentials, kept in the `_g` (global) store so rate-limited logins happen once.

`/jwt/login` allows 5 calls per minute and every call counts, so scenarios that only NEED a token pair
(me / refresh / decode) share one. Safe because the refresh token is reusable and access tokens live
15 minutes; the session is rebuilt after 10 minutes. It also carries an access token minted with a
1-second TTL — expired forever after the first 2 seconds, so all TOKEN_EXPIRED cases share it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from play_api.models import factories
from play_api.models.requests import JwtLoginReq
from play_api.services import jwt, users

_MAX_AGE = 600  # seconds — well inside the 900 s access-token lifetime
_KEY = "jwt_session"


@dataclass(frozen=True)
class JwtSession:
    user_id: str
    email: str
    opaque_token: str
    access: str
    refresh: str
    expired_access: str
    created: float


def _ok(response: Any, what: str) -> dict[str, Any]:
    assert response.status_code in (200, 201), (
        f"shared JWT session: {what} failed {response.status_code}: {response.text}"
    )
    body: dict[str, Any] = response.json()
    return body


def shared_jwt_session(global_store: dict[str, Any]) -> JwtSession:
    session: JwtSession | None = global_store.get(_KEY)
    if session is None or time.monotonic() - session.created > _MAX_AGE:
        body = factories.minimal_user()
        assert body.email is not None and body.password is not None
        created = _ok(users.create(body), "create user")
        pair = _ok(jwt.login(JwtLoginReq(email=body.email, password=body.password)), "JWT login")
        short = _ok(jwt.login(JwtLoginReq(email=body.email, password=body.password, access_ttl_seconds=1)), "ttl login")
        time.sleep(2)  # let the 1-second token expire
        session = JwtSession(
            user_id=created["id"],
            email=body.email,
            opaque_token=created["access_token"],
            access=pair["access_token"],
            refresh=pair["refresh_token"],
            expired_access=short["access_token"],
            created=time.monotonic(),
        )
        global_store[_KEY] = session
    return session
