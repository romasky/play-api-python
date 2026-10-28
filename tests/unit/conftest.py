"""Offline unit tests for `src/play_api` and `tools/` — the coverage source for the ub-mode gates.

Never touch the network: HTTP goes through `httpx.MockTransport`, time through monkeypatch.
Run them with `uv run python tools/ub_gates.py unit` — it bypasses the live suite's `-m Run` addopts and
`tests/conftest.py` (`--confcutdir`). The live `uv run pytest` never collects them (`collect_ignore` there).
"""
