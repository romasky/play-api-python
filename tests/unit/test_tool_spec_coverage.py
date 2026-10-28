"""tools/spec_coverage.py — which spec operations a run called, read from allure result files in tmp_path."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

import _spec
import spec_coverage

SPEC: dict[str, Any] = {
    "paths": {
        "/users/get/{id}": {"get": {}},
        "/chaos/redirect/{n}": {"get": {}},
        "/chaos/redirect/done": {"get": {}},
        "/ws/echo": {"get": {}},
        "/files/{a}/{b}": {"delete": {}},
    }
}
OPS = spec_coverage.operations(SPEC)


def test_operations_turn_path_templates_into_anchored_regexes() -> None:
    assert sorted(OPS) == [
        "DELETE /files/{a}/{b}",
        "GET /chaos/redirect/done",
        "GET /chaos/redirect/{n}",
        "GET /users/get/{id}",
        "GET /ws/echo",
    ]
    rx = OPS["GET /users/get/{id}"]
    assert rx.match("/api/v1/users/get/abc")
    assert not rx.match("/api/v1/users/get/a/b")  # a parameter is one segment
    assert not rx.match("/api/v1/users/get/abc/extra")
    assert not rx.match("/users/get/abc")
    assert OPS["GET /ws/echo"].pattern == r"^/api/v1/ws/echo$"


@pytest.mark.parametrize(
    ("method", "path", "op"),
    [
        ("GET", "/api/v1/chaos/redirect/done", "GET /chaos/redirect/done"),  # most specific template wins
        ("GET", "/api/v1/chaos/redirect/3", "GET /chaos/redirect/{n}"),
        ("DELETE", "/api/v1/files/x/y", "DELETE /files/{a}/{b}"),
        ("POST", "/api/v1/users/get/1", None),  # method must match too
        ("GET", "/api/v1/nowhere", None),
    ],
)
def test_owner_is_the_single_most_specific_operation(method: str, path: str, op: str | None) -> None:
    assert spec_coverage.owner(method, path, OPS) == op


def _result(results: Path, name: str, steps: list[Any]) -> None:
    (results / f"{name}-result.json").write_text(json.dumps({"name": name, "steps": steps}))


@pytest.fixture
def results(tmp_path: Path) -> Path:
    _result(
        tmp_path,
        "a",
        [
            {
                "name": "When I get the user",
                "steps": [
                    {"name": "GET /api/v1/users/get/42?fields=id"},
                    {"name": "GET /api/v1/chaos/redirect/done (stream)"},
                ],
            },
            {"name": "Then nothing", "steps": [{"steps": [{"name": "WebSocket connect /api/v1/ws/echo"}]}]},
        ],
    )
    _result(tmp_path, "b", [{"name": "PATCH /api/v2/elsewhere"}, {"name": "GET /api/v1/users/get/42 trailing"}])
    _result(tmp_path, "c", [])
    (tmp_path / "x-container.json").write_text(json.dumps({"steps": [{"name": "GET /api/v1/ignored"}]}))
    return tmp_path


def test_called_collects_http_and_websocket_calls_from_nested_steps(results: Path) -> None:
    assert spec_coverage.called(results) == {
        ("GET", "/api/v1/users/get/42"),
        ("GET", "/api/v1/chaos/redirect/done"),
        ("GET", "/api/v1/ws/echo"),
    }


def test_an_empty_results_dir_called_nothing(tmp_path: Path) -> None:
    assert spec_coverage.called(tmp_path) == set()


@pytest.fixture
def snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "openapi.json"
    path.write_text(json.dumps(SPEC))
    monkeypatch.setattr(_spec, "SNAPSHOT", path)


def _main(monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["spec_coverage.py", *args])
    return spec_coverage.main()


EXPECTED = """NOT CALLED DELETE /files/{a}/{b}
NOT CALLED GET /chaos/redirect/{n}
3/5 spec operations called (60.0 %)
"""


@pytest.mark.parametrize(("minimum", "code"), [(None, 0), ("60", 0), ("60.1", 1)])
def test_main_lists_uncalled_operations_and_fails_below_the_minimum(
    snapshot: None,
    results: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    minimum: str | None,
    code: int,
) -> None:
    args = ["--results", str(results), *(["--min", minimum] if minimum else [])]
    assert _main(monkeypatch, *args) == code
    assert capsys.readouterr().out == EXPECTED


def test_main_reads_allure_results_in_the_repo_by_default(
    snapshot: None, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "allure-results").mkdir()
    monkeypatch.setattr(spec_coverage, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["spec_coverage.py"])
    assert spec_coverage.main() == 0
    assert capsys.readouterr().out.splitlines()[-1] == "0/5 spec operations called (0.0 %)"
