"""Spec coverage — which Swagger operations did a test run actually call?

Every HTTP call is an Allure sub-step named `<METHOD> /api/v1/<path>` (see api/client.py), so the
results directory is the evidence. Each called path is matched against the spec's path templates
(`/users/get/{id}` → `/users/get/[^/]+`) from the committed snapshot docs/openapi.json.

    uv run python tools/spec_coverage.py                  # reads allure-results/
    uv run python tools/spec_coverage.py --min 100        # exit 1 below 100 % (CI merge job)
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from _spec import METHODS, ROOT, iter_operations, load_snapshot

_CALL = re.compile(rf"^({'|'.join(METHODS)}) (/api/v1/\S*?)(?: \(stream\))?$")
# a WebSocket handshake is its own sub-step name (realtime.ws_connect)
_WS = re.compile(r"^WebSocket connect (/api/v1/\S+)$")


def operations(spec: dict[str, Any]) -> dict[str, re.Pattern[str]]:
    """{"GET /users/get/{id}": re("^/api/v1/users/get/[^/]+$"), …}"""
    return {
        f"{method} {path}": re.compile("^/api/v1" + re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(path)) + "$")
        for method, path, _ in iter_operations(spec)
    }


def owner(method: str, path: str, ops: dict[str, re.Pattern[str]]) -> str | None:
    """The ONE operation a call belongs to — the most specific template wins (fewest `{…}`), so
    `/chaos/redirect/done` counts for `…/done`, not also for `…/{n}`."""
    candidates = [op for op, rx in ops.items() if op.split(" ", 1)[0] == method and rx.match(path)]
    return min(candidates, key=lambda op: op.count("{"), default=None)


def _steps(node: dict[str, Any]) -> Iterator[str]:
    for child in node.get("steps", []):
        yield child.get("name", "")
        yield from _steps(child)


def called(results_dir: Path) -> set[tuple[str, str]]:
    calls = set()
    for result_file in glob.glob(str(results_dir / "*-result.json")):
        for name in _steps(json.loads(Path(result_file).read_text())):
            if match := _CALL.match(name):
                calls.add((match.group(1), match.group(2).split("?")[0]))
            elif match := _WS.match(name):
                calls.add(("GET", match.group(1)))
    return calls


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default=str(ROOT / "allure-results"), help="allure results directory")
    parser.add_argument("--min", type=float, default=0, help="fail below this coverage percentage")
    args = parser.parse_args()

    ops = operations(load_snapshot())
    covered = {op for method, path in called(Path(args.results)) if (op := owner(method, path, ops))}
    for op in sorted(ops.keys() - covered):
        print("NOT CALLED", op)
    percent = 100 * len(covered) / len(ops)
    print(f"{len(covered)}/{len(ops)} spec operations called ({percent:.1f} %)")
    return 1 if percent < args.min else 0


if __name__ == "__main__":
    sys.exit(main())
