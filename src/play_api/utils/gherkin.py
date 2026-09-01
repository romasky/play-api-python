"""Helpers for step *arguments* that Cucumber pre-processed but pytest-bdd hands over verbatim."""

from __future__ import annotations

import json
from typing import Any


def raw_json(text: str) -> Any:
    """Parse the payload of a `… with raw body "{…}"` step.

    Cucumber's `{string}` type unescapes `\\"` inside the quotes; pytest-bdd passes the Gherkin
    text as written (`{\\"email\\":\\"x\\"}`), so undo that escaping before `json.loads`.
    """
    return json.loads(text.replace('\\"', '"'))
