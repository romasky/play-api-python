"""/bug-reports — auto-scored bug reports against the intentional bugs of /buggy/* (auth optional on POST)."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Headers, Params
from play_api.services import JsonBody, to_json


def submit(body: JsonBody, headers: Headers) -> httpx.Response:
    return client.post(paths.BUG_REPORTS, to_json(body), headers)


def list_mine(headers: Headers, params: Params | None = None) -> httpx.Response:
    return client.get(paths.BUG_REPORTS, params=params, headers=headers)


def get(report_id: str, headers: Headers) -> httpx.Response:
    return client.get(paths.bug_report(report_id), headers=headers)
