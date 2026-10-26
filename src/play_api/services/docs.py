"""Downloadable API descriptions (OpenAPI JSON/YAML, Postman collection/environment) and reCAPTCHA."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Params
from play_api.services import JsonBody
from play_api.utils.lookup import choose


def document(name: str, params: Params | None = None) -> httpx.Response:
    return client.get(choose(paths.API_DOCUMENTS, name, "API document"), params=params)


def verify_recaptcha(body: JsonBody) -> httpx.Response:
    return client.post(paths.VERIFY_RECAPTCHA, body)
