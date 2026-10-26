"""Rate-limit pacing — the server runs a per-IP token bucket per endpoint; we PACE, never retry.

None of the API's 429 responses carries `Retry-After` / `X-RateLimit-*`, so the intervals below come
from the server's limiter configuration (refill period of each bucket, + a small margin). `client.request()`
calls `throttle()` before every request: if the previous call to the same bucket was less than one refill
period ago, it sleeps the remainder. Consuming no faster than the refill rate can never drain a bucket,
whatever state an earlier run left it in — and scenarios that never touch a limited endpoint never wait.
"""

from __future__ import annotations

import re
import time

# (method, path regex under /api/v1, bucket name, minimum seconds between two calls)
_BUCKETS: tuple[tuple[str, re.Pattern[str], str, float], ...] = tuple(
    (method, re.compile(rf"/api/v1{rx}$"), name, interval)
    for method, rx, name, interval in (
        ("POST", r"/users/create(-admin)?", "create-user", 0.7),  # 1 per 600 ms, burst 100 (shared)
        ("POST", r"/challenges/[^/]+/start", "create-user", 0.7),  # creates a sandbox user → same bucket
        ("POST", r"/login", "login", 12.5),  # 1 per 12 s, burst 5
        ("POST", r"/jwt/login", "jwt-login", 12.5),  # separate bucket from /login; 400s count too
        ("POST", r"/jwt/decode", "jwt-decode", 2.1),  # 1 per 2 s, burst 10
        ("POST", r"/files/upload", "file-upload", 6.1),  # 10 per minute, burst 5
        ("POST", r"/webhooks/inbox", "webhook-inbox", 6.1),  # 10 per minute, burst 5
        ("POST", r"/store/login", "store-login", 2.1),  # 30 per minute, burst 10
        ("POST", r"/bug-reports", "bug-report", 2.1),  # 30 per minute, burst 10; 400s count too
    )
)

_last_call: dict[str, float] = {}


def throttle(method: str, path: str) -> None:
    for bucket_method, rx, name, interval in _BUCKETS:
        if bucket_method == method and rx.search(path):
            wait = _last_call.get(name, float("-inf")) + interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            _last_call[name] = time.monotonic()
            return
