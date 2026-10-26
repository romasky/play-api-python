"""System contracts — GET /health."""

from __future__ import annotations

from play_api.models.responses.base import Contract, entry


class HealthResponse(Contract):
    status: str
    time: str


CONTRACTS_2XX = (entry("GET", r"/health", HealthResponse),)
