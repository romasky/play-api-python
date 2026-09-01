"""Dotted-path helpers for typed response-body checks (port of src/utils/jsonPath.js).

get_path(body, "metadata.role")     → value or None, never raises; "messages.0.subject" works
has_path(body, "profile.bio")       → True only if every segment is a real key / index
"""

from __future__ import annotations

from typing import Any


def _step(current: Any, key: str) -> tuple[bool, Any]:
    if isinstance(current, dict):
        return (True, current[key]) if key in current else (False, None)
    if isinstance(current, list) and key.isdigit() and int(key) < len(current):
        return True, current[int(key)]
    return False, None


def get_path(obj: Any, path: str) -> Any:
    current = obj
    for key in path.split("."):
        found, current = _step(current, key)
        if not found:
            return None
    return current


def has_path(obj: Any, path: str) -> bool:
    current = obj
    for key in path.split("."):
        found, current = _step(current, key)
        if not found:
            return False
    return True
