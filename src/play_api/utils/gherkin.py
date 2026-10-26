"""Helpers for step *arguments* that Cucumber pre-processed but pytest-bdd hands over verbatim."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qsl

from play_api.api.client import RawJson

_ESCAPED_QUOTE = re.compile(r'\\+"')


def raw_json(text: str) -> Any:
    """Parse the payload of a `… with raw body "{…}"` step.

    Cucumber's `{string}` type unescapes `\\"` inside the quotes; pytest-bdd passes the Gherkin
    text as written (`{\\"email\\":\\"x\\"}`), so undo that escaping before `json.loads`. Inside an
    Examples table cell the same `\\"` arrives with a DOUBLED backslash, so any run of backslashes in
    front of a quote collapses (the payloads never need a literal `\\"` inside a JSON string).

    Text that is not valid JSON (a truncated body on purpose) comes back as `RawJson`, which the
    client sends byte-for-byte instead of re-serialising.
    """
    text = unescape_quotes(text)
    try:
        return json.loads(text)
    except ValueError:
        return RawJson(text)


def unescape_quotes(text: str) -> str:
    """`{\\"a\\":1}` (step text) or `{\\\\"a\\\\":1}` (Examples cell) → `{"a":1}` — see raw_json."""
    return _ESCAPED_QUOTE.sub('"', text)


def query_pairs(query: str) -> list[tuple[str, str | int | float | bool | None]]:
    """`limit=3&filter=a:1&filter=b:2&sort=` → ordered pairs; keeps repeated keys AND present-but-empty
    values (the API answers `sort=` with 400 but an absent `sort` with the default)."""
    return [(key, value) for key, value in parse_qsl(query, keep_blank_values=True)]
