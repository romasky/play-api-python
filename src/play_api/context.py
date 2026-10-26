"""Scenario context — port of src/context/scenarioContext.js.

Gherkin steps share data through string keys:
* plain key or `_l` suffix → local to the current scenario
* `_g` suffix              → global, survives across scenarios (e.g. duplicate-email chains)
* `get()` of an unknown key returns the key itself, so quoted literals work without a
  prior `Save string` step. Consequence: pick literals that cannot collide with a key
  (the JS port stores the bio under `profileBio` so the literal "bio" stays usable).

In pytest-bdd the *instance* is a function-scoped fixture (see tests/conftest.py), so the
local store does not need to be keyed by scenario name as in JS.

`defer(fn)` registers a teardown action (delete the inbox / file / mailbox a step created); the
fixture runs them LIFO after the scenario, pass or fail. Server-side quotas (20 webhook inboxes per
IP, shared file storage) make this mandatory for anything a scenario creates and does not delete.
"""

from __future__ import annotations

import builtins
import re
from collections.abc import Callable
from typing import Any

import httpx2 as httpx

_MISSING = object()
_PLACEHOLDER = re.compile(r"\$\{(\w+)\}")


class ScenarioContext:
    def __init__(self, global_store: dict[str, Any]) -> None:
        self._global = global_store
        self._local: dict[str, Any] = {}
        self._cleanups: list[Callable[[], object]] = []

    def defer(self, action: Callable[[], object]) -> None:
        self._cleanups.append(action)

    def run_cleanups(self) -> list[BaseException]:
        """Run every deferred action (LIFO); return the errors instead of raising mid-way."""
        errors: list[BaseException] = []
        while self._cleanups:
            try:
                self._cleanups.pop()()
            except Exception as exc:
                errors.append(exc)
        return errors

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
        """A context value as text; a literal (unknown key) gets its `${key}` placeholders interpolated."""
        value = self.get(key)
        return self.render(key) if value is key and "${" in key else builtins.str(value)

    def render(self, template: builtins.str) -> builtins.str:
        """Interpolate `${key}` placeholders (query strings, raw bodies); an unknown key fails loudly."""
        return _PLACEHOLDER.sub(lambda m: builtins.str(self.get(m.group(1), fail_if_missing=True)), template)

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
