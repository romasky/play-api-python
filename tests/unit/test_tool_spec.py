"""tools/_spec.py — snapshot loading and operation iteration shared by spec_drift / spec_coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import _spec


def test_iter_operations_yields_upper_case_methods_and_skips_non_method_keys() -> None:
    get: dict[str, Any] = {"responses": {"200": {}}}
    post: dict[str, Any] = {"responses": {}}
    spec = {"paths": {"/a/{id}": {"get": get, "parameters": [{"name": "id"}], "post": post}, "/b": {"Head": {}}}}
    assert list(_spec.iter_operations(spec)) == [("GET", "/a/{id}", get), ("POST", "/a/{id}", post), ("HEAD", "/b", {})]


def test_a_spec_without_paths_has_no_operations() -> None:
    assert list(_spec.iter_operations({})) == []


def test_load_snapshot_reads_the_committed_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = tmp_path / "openapi.json"
    snapshot.write_text(json.dumps({"paths": {"/x": {"get": {}}}}))
    monkeypatch.setattr(_spec, "SNAPSHOT", snapshot)
    assert _spec.load_snapshot() == {"paths": {"/x": {"get": {}}}}


def test_the_real_snapshot_has_79_operations() -> None:
    assert _spec.SNAPSHOT == _spec.ROOT / "docs" / "openapi.json"
    assert len(list(_spec.iter_operations(_spec.load_snapshot()))) == 79
