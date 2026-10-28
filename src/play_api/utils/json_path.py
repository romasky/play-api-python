"""Dotted-path helpers for typed response-body checks (port of src/utils/jsonPath.js).

get_path(body, "metadata.role")     → value or None, never raises; "messages.0.subject" works
has_path(body, "profile.bio")       → True only if every segment is a real key / index
"""

from __future__ import annotations

from typing import Any

_MISSING = object()  # distinguishes "absent" from a present null


def _step(current: Any, key: str) -> Any:
    if isinstance(current, dict):
        return current.get(key, _MISSING)
    if isinstance(current, list) and key.isdigit() and int(key) < len(current):
        return current[int(key)]
    return _MISSING


def _resolve(obj: Any, path: str) -> Any:
    current = obj
    for key in path.split("."):
        current = _step(current, key)
        if current is _MISSING:
            break
    return current


def get_path(obj: Any, path: str) -> Any:
    value = _resolve(obj, path)
    return None if value is _MISSING else value


def has_path(obj: Any, path: str) -> bool:
    return _resolve(obj, path) is not _MISSING
