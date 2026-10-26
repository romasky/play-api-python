"""Shared Swagger plumbing for tools/spec_drift.py and tools/spec_coverage.py."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "docs" / "openapi.json"
METHODS = ("GET", "PUT", "POST", "DELETE", "OPTIONS", "HEAD", "PATCH")


def load_snapshot() -> dict[str, Any]:
    spec: dict[str, Any] = json.loads(SNAPSHOT.read_text())
    return spec


def iter_operations(spec: dict[str, Any]) -> Iterator[tuple[str, str, dict[str, Any]]]:
    """(METHOD, path template, operation object) for every operation of the spec."""
    for path, item in spec.get("paths", {}).items():
        for method, operation in item.items():
            if method.upper() in METHODS:
                yield method.upper(), path, operation
