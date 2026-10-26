"""Response contracts — typed pydantic shapes, one module per API domain.

Two uses:
* explicit step assertions (`assert_error_code`, `assert_login_successful`, …) — imported from the
  domain module (`play_api.models.responses.users`) or `_base` for the shared error envelope;
* `contract_for(method, path)` — `client.request()` validates **every 2xx JSON response** against the
  documented shape automatically, so a field disappearing from `POST /mail/create` fails the request
  step even in a scenario that only asserts the status code.

`extra="allow"` everywhere: the API may add fields; contracts assert presence of the documented ones.
New 2xx endpoint → add its contract to the domain module AND a row to that module's `CONTRACTS_2XX`.
Endpoints answering 2xx with an empty body (DELETE 204, HEAD, OPTIONS) or raw bytes (downloads) have no row.
"""

from __future__ import annotations

from play_api.models.responses import (
    admin,
    auth,
    bug_reports,
    buggy,
    challenges,
    chaos,
    files,
    mail,
    system,
    users,
    webhooks,
)
from play_api.models.responses.base import Contract, Entry

_CONTRACTS_2XX: tuple[Entry, ...] = (
    *system.CONTRACTS_2XX,
    *users.CONTRACTS_2XX,
    *auth.CONTRACTS_2XX,
    *admin.CONTRACTS_2XX,
    *mail.CONTRACTS_2XX,
    *files.CONTRACTS_2XX,
    *webhooks.CONTRACTS_2XX,
    *bug_reports.CONTRACTS_2XX,
    *buggy.CONTRACTS_2XX,
    *challenges.CONTRACTS_2XX,
    *chaos.CONTRACTS_2XX,
)


def contract_for(method: str, path: str) -> type[Contract] | None:
    """The documented 2xx contract for an endpoint, or None if it has none (empty-body responses)."""
    return next((c for m, rx, c in _CONTRACTS_2XX if m == method and rx.search(path)), None)
