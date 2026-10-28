"""tools/ub_gates.py — gate dispatch; `subprocess.run` is stubbed, crapper / dryer / mutator never launch."""

from __future__ import annotations

import io
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import ub_gates

PY = [sys.executable, "-m"]
# Spelled out, not built from ub_gates.UNIT: a copy of the implementation would pin its bugs too.
PYTEST = ["pytest", "tests/unit", "-o", "addopts=", "--confcutdir=tests/unit", "-p", "no:cacheprovider", "-q"]
UNIT = [*PY, *PYTEST]
COV_RUN = [*PY, "coverage", "run", "--source=src,tools", "-m", *PYTEST]
COV_LCOV = [*PY, "coverage", "lcov", "-q", "-o", "target/coverage/python/lcov.info"]
CRAPPER = [*PY, "crapper", "--use-existing-coverage", "--threshold", "9.99", "src", "tools"]
DRYER = [*PY, "dryer", "--threshold", "0.8", "src", "tools"]
FAST = [UNIT, COV_RUN, COV_LCOV, CRAPPER, DRYER]
# --no-coverage: every site runs, so a site no test reaches survives (fails) instead of being skipped as uncovered
MUTATOR = [*PY, "mutator", "--no-coverage", "--test-command", shlex.join(UNIT)]


class _Runner:
    """Records every command; a command fails when its module (+ first arg) is in `failing`."""

    def __init__(self, *failing: str) -> None:
        self.failing = set(failing)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert (cwd, check) == (ub_gates.ROOT, False)
        self.commands.append(command)
        failed = command[2] in self.failing or " ".join(command[2:4]) in self.failing
        return subprocess.CompletedProcess(command, 1 if failed else 0)


@pytest.fixture
def dry_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "dry.edn"
    path.write_text("{:candidates []}")
    monkeypatch.setattr(ub_gates, "DRY_SNAPSHOT", path)
    return path


def _with(monkeypatch: pytest.MonkeyPatch, *failing: str) -> _Runner:
    runner = _Runner(*failing)
    monkeypatch.setattr(subprocess, "run", runner)
    return runner


def test_python_echoes_the_command_and_reports_its_exit_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _with(monkeypatch, "dryer")
    assert ub_gates.python("pytest", "-q") is True
    assert ub_gates.python("dryer") is False
    assert runner.commands == [[*PY, "pytest", "-q"], [*PY, "dryer"]]
    assert capsys.readouterr().out == f"$ {shlex.join([*PY, 'pytest', '-q'])}\n$ {shlex.join([*PY, 'dryer'])}\n"


def test_the_echo_is_on_stdout_before_the_child_writes_to_it(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="utf-8"))  # block-buffered, like a CI pipe
    seen_by_child: list[bytes] = []

    def run(command: list[str], cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        seen_by_child.append(raw.getvalue())
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    ub_gates.python("pytest", "-q")
    assert seen_by_child == [f"$ {shlex.join([*PY, 'pytest', '-q'])}\n".encode()]


def test_the_unit_gate_runs_tests_unit_without_the_live_suites_addopts(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main(["unit"]) == 0
    assert runner.commands == [UNIT]
    assert ub_gates.UNIT[:4] == ["pytest", "tests/unit", "-o", "addopts="]
    assert "--confcutdir=tests/unit" in ub_gates.UNIT


def test_fast_runs_unit_crap_and_dry_in_order(
    monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main(["fast"]) == 0
    assert runner.commands == FAST
    assert capsys.readouterr().out.splitlines()[-1] == "ub gates: OK"


def test_all_is_the_default_and_adds_mutator_on_the_changed_files(
    monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main([]) == 0
    assert runner.commands == [*FAST, [*MUTATOR, "--changed"]]
    assert capsys.readouterr().out.splitlines()[-1] == "ub gates: OK"
    runner = _with(monkeypatch)
    assert ub_gates.main(["all"]) == 0
    assert runner.commands == [*FAST, [*MUTATOR, "--changed"]]


def test_all_mutates_the_given_paths_instead(monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main(["all", "src/a.py", "tools"]) == 0
    assert runner.commands[-1] == [*MUTATOR, "src/a.py", "tools"]


def test_all_fails_when_a_mutant_survives(
    monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _with(monkeypatch, "mutator")  # mutator exits 3 on a survivor
    assert ub_gates.main(["all"]) == 1
    assert capsys.readouterr().out.splitlines()[-1] == "ub gates: FAILED mutate"


@pytest.mark.parametrize("command", ["fast", "unit", "crap", "dry"])
def test_only_all_and_mutate_take_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], command: str
) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main([command, "src/a.py"]) == 2
    assert runner.commands == []
    assert capsys.readouterr().err == f"{ub_gates.__doc__}\n"


@pytest.mark.parametrize(
    ("failing", "commands"),
    [
        ("coverage run", [COV_RUN]),  # no lcov, no crapper after a failed coverage run
        ("coverage lcov", [COV_RUN, COV_LCOV]),
        ("crapper", [COV_RUN, COV_LCOV, CRAPPER]),
    ],
)
def test_crap_stops_at_the_first_failing_step(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], failing: str, commands: list[list[str]]
) -> None:
    runner = _with(monkeypatch, failing)
    assert ub_gates.main(["crap"]) == 1
    assert runner.commands == commands
    assert capsys.readouterr().out.splitlines()[-1] == "ub gates: FAILED crap"


def test_one_failing_gate_is_named_and_the_others_still_run(
    monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _with(monkeypatch, "pytest")
    assert ub_gates.main(["fast"]) == 1
    assert runner.commands == FAST
    assert capsys.readouterr().out.splitlines()[-1] == "ub gates: FAILED unit"


@pytest.mark.parametrize(
    ("snapshot", "failing", "code"),
    [
        ("{:candidates []}", (), 0),
        ("{:candidates [{:score 0.91 :a x :b y}]}", (), 1),  # dryer exits 0 — a scored pair is the failure
        ("{:candidates []}", ("dryer",), 1),
    ],
)
def test_dry_fails_on_any_scored_pair_in_the_snapshot(
    monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path, snapshot: str, failing: tuple[str, ...], code: int
) -> None:
    dry_snapshot.write_text(snapshot)
    runner = _with(monkeypatch, *failing)
    assert ub_gates.main(["dry"]) == code
    assert runner.commands == [DRYER]


def test_dry_fails_when_dryer_wrote_no_snapshot(monkeypatch: pytest.MonkeyPatch, dry_snapshot: Path) -> None:
    dry_snapshot.unlink(missing_ok=True)
    _with(monkeypatch)
    assert ub_gates.main(["dry"]) == 1


def test_mutate_runs_every_site_of_the_given_paths_with_no_coverage_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main(["mutate", "src/a.py", "tools"]) == 0
    assert runner.commands == [[*MUTATOR, "src/a.py", "tools"]]


def test_mutate_fails_when_a_mutant_survives(monkeypatch: pytest.MonkeyPatch) -> None:
    _with(monkeypatch, "mutator")  # mutator exits 3 on a survivor — an unreached site is one too
    assert ub_gates.main(["mutate", "x.py"]) == 1


def test_mutate_without_paths_is_an_error_and_runs_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main(["mutate"]) == 1
    assert runner.commands == []
    assert capsys.readouterr().err == "mutate needs at least one file or directory\n"


def test_an_unknown_gate_prints_the_usage_and_runs_nothing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = _with(monkeypatch)
    assert ub_gates.main(["bogus"]) == 2
    assert runner.commands == []
    captured = capsys.readouterr()
    assert captured.err == f"{ub_gates.__doc__}\n"
    assert captured.out == ""
