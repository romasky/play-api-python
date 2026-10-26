"""`choose(table, name, what)` — the one way a step-supplied name selects an entry from a fixed table,
with an error that lists the valid names."""

from __future__ import annotations

from collections.abc import Mapping


def choose[T](table: Mapping[str, T], name: str, what: str) -> T:
    assert name in table, f"unknown {what} '{name}', expected one of {sorted(table)}"
    return table[name]
