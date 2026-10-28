from __future__ import annotations

import time

import pytest

from play_api import pacing
from play_api.api import paths


class FakeClock:
    """monotonic() + sleep() that advance a virtual time; records every sleep."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> FakeClock:
    fake = FakeClock()
    monkeypatch.setattr(pacing, "_last_call", {})
    monkeypatch.setattr(time, "monotonic", fake.monotonic)
    monkeypatch.setattr(time, "sleep", fake.sleep)
    return fake


def test_first_call_of_a_bucket_never_waits(clock: FakeClock) -> None:
    pacing.throttle("POST", paths.LOGIN)
    assert clock.sleeps == []


def test_second_call_within_the_interval_sleeps_the_remainder(clock: FakeClock) -> None:
    pacing.throttle("POST", paths.LOGIN)
    clock.now += 2.5
    pacing.throttle("POST", paths.LOGIN)
    assert clock.sleeps == [pytest.approx(10.0)]  # 12.5 s interval


def test_call_exactly_at_the_interval_does_not_wait(clock: FakeClock) -> None:
    pacing.throttle("POST", paths.JWT_DECODE)
    clock.now += 2.1
    pacing.throttle("POST", paths.JWT_DECODE)
    assert clock.sleeps == []


def test_call_just_before_the_interval_waits_the_tiny_rest(clock: FakeClock) -> None:
    pacing.throttle("POST", paths.JWT_DECODE)
    clock.now += 2.0
    pacing.throttle("POST", paths.JWT_DECODE)
    assert clock.sleeps == [pytest.approx(0.1)]


def test_last_call_is_stamped_after_the_sleep(clock: FakeClock) -> None:
    pacing.throttle("POST", paths.STORE_LOGIN)
    pacing.throttle("POST", paths.STORE_LOGIN)  # sleeps 2.1 → stamped at 1002.1
    clock.now += 2.0
    pacing.throttle("POST", paths.STORE_LOGIN)
    assert clock.sleeps == [pytest.approx(2.1), pytest.approx(0.1)]


def test_shared_bucket_paces_across_endpoints(clock: FakeClock) -> None:
    pacing.throttle("POST", "/api/v1/users/create")
    pacing.throttle("POST", "/api/v1/challenges/abc/start")
    pacing.throttle("POST", "/api/v1/users/create-admin")
    assert clock.sleeps == [pytest.approx(0.7), pytest.approx(0.7)]


def test_buckets_are_independent(clock: FakeClock) -> None:
    pacing.throttle("POST", paths.LOGIN)
    pacing.throttle("POST", paths.JWT_LOGIN)
    pacing.throttle("POST", "/api/v1/files/upload")
    assert clock.sleeps == []


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", paths.LOGIN),  # wrong method
        ("POST", "/api/v1/users/list"),  # unlimited endpoint
        ("POST", "/api/v1/login/extra"),  # anchored at the end
        ("POST", "/login"),  # needs the /api/v1 prefix
        ("POST", "/api/v1/challenges/a/b/start"),  # one id segment only
    ],
)
def test_unlimited_requests_never_wait_or_stamp(clock: FakeClock, method: str, path: str) -> None:
    pacing.throttle(method, path)
    pacing.throttle(method, path)
    pacing.throttle("POST", paths.LOGIN)  # and they leave the limited buckets untouched
    assert clock.sleeps == []


def test_full_url_ending_in_a_limited_path_is_paced(clock: FakeClock) -> None:
    pacing.throttle("POST", "https://www.play-qa.com/api/v1/bug-reports")
    pacing.throttle("POST", paths.BUG_REPORTS)
    assert clock.sleeps == [pytest.approx(2.1)]
