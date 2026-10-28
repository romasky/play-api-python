"""tools/spec_drift.py — live Swagger vs snapshot; the fetch is stubbed, never the network."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import httpx2 as httpx
import pytest

import _spec
import spec_drift
from play_api.config import settings

OLD: dict[str, Any] = {
    "paths": {
        "/users/get/{id}": {"get": {"responses": {"200": {}, "404": {}}}},
        "/users/delete/{id}": {"delete": {"responses": {"200": {}, "401": {}}}},
        "/gone": {"post": {"responses": {"201": {}}}},
    }
}
NEW: dict[str, Any] = {
    "paths": {
        "/users/get/{id}": {"get": {"responses": {"200": {}, "404": {}}}},
        "/users/delete/{id}": {"delete": {"responses": {"200": {}, "403": {}}}},
        "/fresh": {"get": {"responses": {"500": {}, "200": {}}}, "put": {}},
    }
}


def test_operations_maps_each_operation_to_its_response_codes() -> None:
    assert spec_drift.operations(NEW) == {
        "GET /users/get/{id}": {"200", "404"},
        "DELETE /users/delete/{id}": {"200", "403"},
        "GET /fresh": {"200", "500"},
        "PUT /fresh": set(),
    }


def test_diff_lists_new_removed_and_changed_operations_sorted() -> None:
    assert spec_drift.diff(spec_drift.operations(OLD), spec_drift.operations(NEW)) == [
        "+ GET /fresh  (new operation: 200, 500)",
        "+ PUT /fresh  (new operation: )",
        "- POST /gone  (operation removed)",
        "~ DELETE /users/delete/{id}  responses +403 -401",
    ]


@pytest.mark.parametrize(
    ("old", "new", "line"),
    [
        ({"GET /a": {"200"}}, {"GET /a": {"200", "401"}}, "~ GET /a  responses +401"),
        ({"GET /a": {"200", "401"}}, {"GET /a": {"200"}}, "~ GET /a  responses -401"),
    ],
)
def test_diff_reports_a_one_sided_response_change(
    old: dict[str, set[str]], new: dict[str, set[str]], line: str
) -> None:
    assert spec_drift.diff(old, new) == [line]


def test_identical_specs_have_no_diff() -> None:
    assert spec_drift.diff(spec_drift.operations(OLD), spec_drift.operations(OLD)) == []


class _Swagger:
    """Stands in for `httpx.get` on the live Swagger URL."""

    def __init__(self, spec: Any, status: int = 200) -> None:
        self.spec = spec
        self.status = status
        self.calls: list[tuple[str, float]] = []

    def __call__(self, url: str, timeout: float) -> httpx.Response:
        self.calls.append((url, timeout))
        return httpx.Response(self.status, json=self.spec, request=httpx.Request("GET", url))


@pytest.fixture
def snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "docs" / "openapi.json"
    path.parent.mkdir()
    path.write_text(json.dumps(OLD))
    monkeypatch.setattr(_spec, "SNAPSHOT", path)
    monkeypatch.setattr(spec_drift, "SNAPSHOT", path)
    monkeypatch.setattr(spec_drift, "ROOT", tmp_path)
    return path


def _run(monkeypatch: pytest.MonkeyPatch, swagger: _Swagger, *args: str) -> int:
    monkeypatch.setattr(httpx, "get", swagger)
    monkeypatch.setattr(sys, "argv", ["spec_drift.py", *args])
    return spec_drift.main()


def test_main_fetches_the_live_swagger_next_to_the_api(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    swagger = _Swagger(OLD)
    assert _run(monkeypatch, swagger) == 0
    assert swagger.calls == [(settings.base_url.rstrip("/") + "/swagger/doc.json", settings.request_timeout)]
    assert capsys.readouterr().out == "OK — live spec matches snapshot\n"


def test_main_prints_every_drift_line_and_fails(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(monkeypatch, _Swagger(NEW)) == 1
    assert capsys.readouterr().out.splitlines() == [
        *spec_drift.diff(spec_drift.operations(OLD), spec_drift.operations(NEW)),
        "4 change(s) vs docs/openapi.json",
    ]
    assert json.loads(snapshot.read_text()) == OLD


def test_update_accepts_the_live_spec_as_the_snapshot(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    live = {"paths": {"/ü": {"get": {}}, **NEW["paths"]}}
    assert _run(monkeypatch, _Swagger(live), "--update") == 0
    assert snapshot.read_text() == json.dumps(live, indent=2, ensure_ascii=False) + "\n"
    assert capsys.readouterr().out == "snapshot updated: docs/openapi.json (5 operations)\n"


def test_an_unreachable_swagger_raises_instead_of_reporting_no_drift(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(httpx.HTTPStatusError):
        _run(monkeypatch, _Swagger({"error": "down"}, status=503))
