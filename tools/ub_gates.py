"""ub-mode quality gates (https://github.com/unclebob/ub-mode) — offline, local only, never the live API.

crapper and mutator would run plain `pytest` (= the live suite, ~21 min, rate-limited), so this script points them
at the offline unit tests in `tests/unit` instead: crapper reads their lcov (`--use-existing-coverage`); mutator runs
them per mutant (`--test-command`) on every site (`--no-coverage`), so an unreached site fails as a survivor.

    uv run --group ub python tools/ub_gates.py unit                 # offline unit tests only
    uv run --group ub python tools/ub_gates.py crap                 # coverage + crapper: fail when a CRAP is ≥ 10
    uv run --group ub python tools/ub_gates.py dry                  # dryer: fail when a pair scores ≥ 0.8
    uv run --group ub python tools/ub_gates.py mutate src/play_api/pacing.py   # mutator on files / trees (slow)
    uv run --group ub python tools/ub_gates.py fast                 # unit + crap + dry (no mutation)
    uv run --group ub python tools/ub_gates.py all [paths...]       # the complete gate: fast + mutator on the paths,
                                                                    # or on the git-changed sources when none given

Exit 0 when every requested gate passes. Snapshots land in `.metrics/` (git-ignored).
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ["src", "tools"]
LCOV = "target/coverage/python/lcov.info"  # where crapper / mutator look for an existing Python report
CRAP_LIMIT = "9.99"  # crapper fails when the worst score is ABOVE the threshold; ub-mode wants CRAP < 10
DRY_LIMIT = "0.8"
DRY_SNAPSHOT = ROOT / ".metrics" / "dry.edn"

# The live suite's addopts (`-m Run …`, --alluredir) and tests/conftest.py (13 step plugins) stay out.
UNIT = ["pytest", "tests/unit", "-o", "addopts=", "--confcutdir=tests/unit", "-p", "no:cacheprovider", "-q"]


def python(*args: str) -> bool:
    """`python -m <args>` with this interpreter, in the repo root; True when it exits 0."""
    command = [sys.executable, "-m", *args]
    print("$", shlex.join(command), flush=True)
    return subprocess.run(command, cwd=ROOT, check=False).returncode == 0


def unit() -> bool:
    return python(*UNIT)


def coverage() -> bool:
    return python("coverage", "run", f"--source={','.join(SOURCES)}", "-m", *UNIT) and python(
        "coverage", "lcov", "-q", "-o", LCOV
    )


def crap() -> bool:
    return coverage() and python("crapper", "--use-existing-coverage", "--threshold", CRAP_LIMIT, *SOURCES)


def dry() -> bool:
    # dryer always exits 0; any candidate in its snapshot (or no snapshot at all) is the failure
    ran = python("dryer", "--threshold", DRY_LIMIT, *SOURCES)
    return ran and DRY_SNAPSHOT.is_file() and ":score" not in DRY_SNAPSHOT.read_text()


def mutate(paths: list[str]) -> bool:
    if not paths:
        print("mutate needs at least one file or directory", file=sys.stderr)
        return False
    # --no-coverage: mutator would SKIP (and pass) sites lcov marks unhit; running them all turns a site no test
    # reaches into a survivor, so "cover the uncovered" fails the gate too — and no lcov attribution artifacts.
    # --test-command is still mandatory: without it every mutant would run plain `pytest` = the live suite.
    tests = shlex.join([sys.executable, "-m", *UNIT])
    return python("mutator", "--no-coverage", "--test-command", tests, *paths)


GATES = {"unit": unit, "crap": crap, "dry": dry}
SUITES = {name: [name] for name in GATES} | {"fast": list(GATES), "all": [*GATES, "mutate"]}


def main(argv: list[str]) -> int:
    command, *paths = argv or ["all"]
    if command == "mutate":
        return int(not mutate(paths))
    if command not in SUITES or (paths and command != "all"):
        print(__doc__, file=sys.stderr)
        return 2
    # `all` is the complete ub-mode gate: no path given → mutate what git status shows as added / modified
    gates = GATES | {"mutate": lambda: mutate(paths or ["--changed"])}
    failed = [name for name in SUITES[command] if not gates[name]()]
    print("ub gates:", f"FAILED {', '.join(failed)}" if failed else "OK")
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
