"""Swagger drift check — compares the LIVE OpenAPI spec with the committed snapshot docs/openapi.json.

The suite's expectations were derived from the snapshot; when the API team changes the spec
(e.g. 2026-10-23: `403` added to PUT/PATCH/DELETE/logout), this fails with the exact operations and
response codes that moved, instead of three scenarios failing in the nightly run.

    uv run python tools/spec_drift.py             # exit 1 on drift
    uv run python tools/spec_drift.py --update    # accept the live spec as the new snapshot

Then update features / contracts / docs/API_REFERENCE.md for every reported line.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src")]

import httpx2 as httpx  # noqa: E402

from play_api.config import settings  # noqa: E402

SNAPSHOT = ROOT / "docs" / "openapi.json"
SPEC_PATH = "/swagger/doc.json"
METHODS = {"get", "put", "post", "delete", "options", "head", "patch"}


def operations(spec: dict[str, Any]) -> dict[str, set[str]]:
    """{"GET /users/get/{id}": {"200", "401", "404", "500"}, …}"""
    return {
        f"{method.upper()} {path}": set(op.get("responses", {}))
        for path, item in spec.get("paths", {}).items()
        for method, op in item.items()
        if method in METHODS
    }


def diff(old: dict[str, set[str]], new: dict[str, set[str]]) -> list[str]:
    lines = [f"+ {op}  (new operation: {', '.join(sorted(new[op]))})" for op in sorted(new.keys() - old.keys())]
    lines += [f"- {op}  (operation removed)" for op in sorted(old.keys() - new.keys())]
    for op in sorted(old.keys() & new.keys()):
        added, removed = new[op] - old[op], old[op] - new[op]
        if added or removed:
            changes = [f"+{c}" for c in sorted(added)] + [f"-{c}" for c in sorted(removed)]
            lines.append(f"~ {op}  responses {' '.join(changes)}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true", help="overwrite the snapshot with the live spec")
    args = parser.parse_args()

    response = httpx.get(settings.base_url.rstrip("/") + SPEC_PATH, timeout=settings.request_timeout)
    response.raise_for_status()
    live = response.json()

    if args.update:
        SNAPSHOT.write_text(json.dumps(live, indent=2, ensure_ascii=False) + "\n")
        print(f"snapshot updated: {SNAPSHOT.relative_to(ROOT)} ({len(operations(live))} operations)")
        return 0

    changes = diff(operations(json.loads(SNAPSHOT.read_text())), operations(live))
    for line in changes:
        print(line)
    print(f"{len(changes)} change(s) vs {SNAPSHOT.relative_to(ROOT)}" if changes else "OK — live spec matches snapshot")
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
