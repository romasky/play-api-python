"""System contracts — GET /health, the downloadable API descriptions, POST /verify-recaptcha."""

from __future__ import annotations

from typing import Any

from play_api.models.responses.base import Contract, entry


class HealthResponse(Contract):
    status: str
    time: str


class OpenApiDocument(Contract):
    swagger: str
    basePath: str
    info: dict[str, Any]
    paths: dict[str, Any]


class PostmanCollection(Contract):
    info: dict[str, Any]
    item: list[Any]
    variable: list[dict[str, Any]]


class PostmanEnvironment(Contract):
    name: str
    values: list[dict[str, Any]]


class RecaptchaVerifyResponse(Contract):
    """200 means Google answered — `success` says whether the token passed (a bogus one: false + error_codes)."""

    success: bool
    error_codes: list[str] | None = None


CONTRACTS_2XX = (
    entry("GET", r"/health", HealthResponse),
    entry("GET", r"/openapi\.json", OpenApiDocument),
    entry("GET", r"/postman/collection\.json", PostmanCollection),
    entry("GET", r"/postman/environment\.json", PostmanEnvironment),
    entry("POST", r"/verify-recaptcha", RecaptchaVerifyResponse),
)
