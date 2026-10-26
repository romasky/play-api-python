"""Downloadable API descriptions (OpenAPI JSON/YAML, Postman collection/environment) and reCAPTCHA."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Params
from play_api.services import JsonBody, to_json


def document(name: str, params: Params | None = None) -> httpx.Response:
    assert name in paths.API_DOCUMENTS, f"unknown API document '{name}', expected one of {sorted(paths.API_DOCUMENTS)}"
    return client.get(paths.API_DOCUMENTS[name], params=params)


def verify_recaptcha(body: JsonBody) -> httpx.Response:
    return client.post(paths.VERIFY_RECAPTCHA, to_json(body))
