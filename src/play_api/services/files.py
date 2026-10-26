"""/files/* — multipart upload (auth optional), my-files list, public metadata + download, delete."""

from __future__ import annotations

import httpx2 as httpx

from play_api.api import client, paths
from play_api.api.client import Files, Headers, Params


def upload(
    headers: Headers,
    file: tuple[str, bytes, str] | None,
    *,
    field: str = "file",
    description: str | None = None,
) -> httpx.Response:
    """`file` = (filename, bytes, declared content type); `field` other than "file", or no file → NO_FILE.

    The description goes in as a multipart FIELD (filename None), so the body stays multipart/form-data
    even without a file part — `data=` alone would make httpx send x-www-form-urlencoded instead.
    """
    parts: Files = []
    if file is not None:
        parts.append((field, file))
    if description is not None or file is None:
        parts.append(("description", (None, (description or "").encode(), None)))
    return client.request("POST", paths.FILES_UPLOAD, files=parts, headers=headers)


def upload_json(body: dict[str, str], headers: Headers) -> httpx.Response:
    """Not multipart at all → INVALID_MULTIPART."""
    return client.post(paths.FILES_UPLOAD, body, headers)


def list_mine(headers: Headers, params: Params | None = None) -> httpx.Response:
    return client.get(paths.FILES, params=params, headers=headers)


def metadata(file_id: str, headers: Headers | None = None) -> httpx.Response:
    return client.get(paths.file(file_id), headers=headers)


def download(file_id: str, params: Params | None = None) -> httpx.Response:
    return client.get(paths.file_download(file_id), params=params)


def delete(file_id: str, headers: Headers) -> httpx.Response:
    return client.delete(paths.file(file_id), headers)
