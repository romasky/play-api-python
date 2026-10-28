from __future__ import annotations

import time
from typing import Any

import httpx2 as httpx
import pytest

from play_api import jwt_session
from play_api.models.requests import CreateUserReq, JwtLoginReq
from play_api.services import jwt, users

REQUEST = httpx.Request("POST", "https://x/api/v1")


class FakeApi:
    """Stands in for services.users.create / services.jwt.login and the clock; records the calls."""

    def __init__(self) -> None:
        self.now = 5000.0
        self.sleeps: list[float] = []
        self.created: list[CreateUserReq] = []
        self.logins: list[JwtLoginReq] = []
        self.create_status = 201
        self.login_status = 200

    def create(self, body: CreateUserReq) -> httpx.Response:
        self.created.append(body)
        n = len(self.created)
        return httpx.Response(self.create_status, json={"id": f"u{n}", "access_token": f"opaque{n}"}, request=REQUEST)

    def login(self, body: JwtLoginReq) -> httpx.Response:
        self.logins.append(body)
        n = len(self.logins)
        if self.login_status != 200:
            return httpx.Response(self.login_status, json={"error": {"code": "INVALID_CREDENTIALS"}}, request=REQUEST)
        return httpx.Response(200, json={"access_token": f"access{n}", "refresh_token": f"refresh{n}"}, request=REQUEST)

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> FakeApi:
    fake = FakeApi()
    monkeypatch.setattr(users, "create", fake.create)
    monkeypatch.setattr(jwt, "login", fake.login)
    monkeypatch.setattr(time, "monotonic", fake.monotonic)
    monkeypatch.setattr(time, "sleep", fake.sleep)
    return fake


def test_first_call_creates_a_user_and_two_logins(api: FakeApi) -> None:
    store: dict[str, Any] = {}
    session = jwt_session.shared_jwt_session(store)

    user = api.created[0]
    assert session == jwt_session.JwtSession(
        user_id="u1",
        email=str(user.email),
        opaque_token="opaque1",
        access="access1",
        refresh="refresh1",
        expired_access="access2",
        created=5002.0,  # stamped after the 2 s wait
    )
    assert [(lg.email, lg.password, lg.access_ttl_seconds) for lg in api.logins] == [
        (user.email, user.password, None),
        (user.email, user.password, 1),
    ]
    assert api.sleeps == [2]
    assert store == {"jwt_session": session}


def test_session_is_reused_while_young_enough(api: FakeApi) -> None:
    store: dict[str, Any] = {}
    first = jwt_session.shared_jwt_session(store)
    api.now = first.created + 600  # exactly the max age: still fresh
    assert jwt_session.shared_jwt_session(store) is first
    assert len(api.created) == 1
    assert len(api.logins) == 2


def test_session_is_rebuilt_after_the_max_age(api: FakeApi) -> None:
    store: dict[str, Any] = {}
    first = jwt_session.shared_jwt_session(store)
    api.now = first.created + 600.5
    second = jwt_session.shared_jwt_session(store)
    assert second is not first
    assert second.user_id == "u2"
    assert store["jwt_session"] is second


def test_failed_create_names_the_step_and_the_status(api: FakeApi) -> None:
    api.create_status = 400
    with pytest.raises(AssertionError, match="shared JWT session: create user failed 400"):
        jwt_session.shared_jwt_session({})
    assert api.logins == []


def test_failed_login_names_the_step_and_the_body(api: FakeApi) -> None:
    api.login_status = 401
    store: dict[str, Any] = {}
    with pytest.raises(AssertionError, match=r"JWT login failed 401: .*INVALID_CREDENTIALS"):
        jwt_session.shared_jwt_session(store)
    assert store == {}
