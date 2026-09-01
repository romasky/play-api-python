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

import builtins
from typing import Any

import httpx2 as httpx

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
        value = (
            self._global.get(clean, _MISSING)
            if is_global
            else self._local.get(clean, self._global.get(clean, _MISSING))
        )
        if value is _MISSING:
            if fail_if_missing:
                raise KeyError(f"Context variable '{clean}' not found")
            return key  # passthrough: literal string
        return value

    def opt(self, key: str) -> Any | None:
        clean, is_global = self._split(key)
        return self._global.get(clean) if is_global else self._local.get(clean, self._global.get(clean))

    def str(self, key: builtins.str) -> builtins.str:
        return builtins.str(self.get(key))

    def response(self, var_name: builtins.str) -> httpx.Response:
        """A saved httpx.Response (fails loudly if missing)."""
        res = self.get(var_name, fail_if_missing=True)
        assert isinstance(res, httpx.Response), f"Context variable '{var_name}' is not a saved response: {res!r}"
        return res

    def body(self, var_name: builtins.str) -> Any:
        """Parsed JSON body of a saved response; None for an empty body.

        Non-JSON content (e.g. a Cloudflare 521 HTML page) is returned as text, like axios
        `res.data` in the JS port — so assertions fail with "Field … not found. Body: <html…"
        instead of a JSONDecodeError traceback.
        """
        res = self.response(var_name)
        if not res.content:
            return None
        try:
            return res.json()
        except ValueError:
            return res.text
