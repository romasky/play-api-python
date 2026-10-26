"""Service layer: one module per API domain. Steps call services; services call `api.client` with
`api.paths` and request models. A service takes plain values (never `ctx`) and returns the
`httpx.Response` untouched — assertions stay in the steps / contracts.

Bodies are `JsonBody`: a request model (the client serialises it with `to_body()`) or any raw JSON value
for the `… with raw body "{…}"` steps that send deliberately broken payloads.
"""

from __future__ import annotations

from typing import Any

from play_api.models.requests import Body

JsonBody = Body | dict[str, Any] | list[Any] | str | int | float | bool | None
