"""Scenario context — port of src/context/scenarioContext.js.

Gherkin steps share data through string keys:
* plain key or `_l` suffix → local to the current scenario
* `_g` suffix              → global, survives across scenarios (e.g. duplicate-email chains)
* `get()` of an unknown key returns the key itself, so quoted literals work without a
  prior `Save string` step. Consequence: pick literals that cannot collide with a key
  (the JS port stores the bio under `profileBio` so the literal "bio" stays usable).

In pytest-bdd the *instance* is a function-scoped fixture (see tests/conftest.py), so the
local store does not need to be keyed by scenario name as in JS.
"""

from __future__ import annotations

from typing import Any

_MISSING = object()


class ScenarioContext:
    def __init__(self, global_store: dict[str, Any]) -> None:
        self._global = global_store
        self._local: dict[str, Any] = {}

    @staticmethod
    def _split(key: str) -> tuple[str, bool]:
        if key.endswith("_g"):
            return key[:-2], True
        if key.endswith("_l"):
            return key[:-2], False
        return key, False

    def save(self, key: str, value: Any) -> None:
        clean, is_global = self._split(key)
        (self._global if is_global else self._local)[clean] = value

    def get(self, key: str, fail_if_missing: bool = False) -> Any:
        clean, is_global = self._split(key)
        value = self._global.get(clean, _MISSING) if is_global else self._local.get(clean, self._global.get(clean, _MISSING))
        if value is _MISSING:
            if fail_if_missing:
                raise KeyError(f"Context variable '{clean}' not found")
            return key  # passthrough: literal string
        return value

    def opt(self, key: str) -> Any | None:
        clean, is_global = self._split(key)
        return self._global.get(clean) if is_global else self._local.get(clean, self._global.get(clean))

    def str(self, key: str) -> str:
        return str(self.get(key))

    def response(self, var_name: str):
        """A saved httpx.Response (fails loudly if missing)."""
        return self.get(var_name, fail_if_missing=True)

    def body(self, var_name: str) -> Any:
        res = self.response(var_name)
        return res.json() if res.content else None
