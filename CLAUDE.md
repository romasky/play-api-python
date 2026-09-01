# play-api-python — agent entry point

**Read this file first.** It is the single source of context for continuing this project.
Everything an agent needs — goal, stack decisions (and why), conventions, the porting plan with
checkboxes, live-API quirks and known pitfalls — is here. Update the checkboxes as you go.

## 1. Mission

Python port of **play-api-js** (`/Users/macbook/Documents/Storage/rs/projects/play-api-js`,
https://github.com/romasky/play-api-js) — a BDD API test framework for https://www.play-qa.com.
The JS project (itself a port of `play-api-java`) is the **reference implementation**: 181 scenarios
in 18 feature files, all green against the live API as of 2026-08-31.

**Definition of done for the port:** `uv run pytest` runs the *same 18 feature files* (copied verbatim
into `features/play_qa_api/`) with the same expected statuses and `error.code`s, and produces an
Allure 3 report with the same Epic → Suite → SubSuite → Story hierarchy.

## 2. Stack (decided 2026-09-01 after research — do not re-litigate without a reason)

| Layer | Choice | Version (PyPI, Sep 2026) | Why |
|---|---|---|---|
| Runner + BDD | **pytest + pytest-bdd** | pytest ≥8.3 / pytest-bdd 8.1.0 | `gherkin-official` parser (outlines, tags, datatables), pytest fixtures/markers/IDE; behave 1.3.3 was the alternative (closer to Cucumber, but its own runner and no fixtures) |
| HTTP | **httpx2** (`import httpx2 as httpx`) | 2.12.0 | Same API as httpx, now maintained by Pydantic Services (original `httpx` stalled at 0.28.1, Dec 2024); never raises on 4xx/5xx; single `timeout` |
| Models | **pydantic 2** | 2.13 | `model_dump(by_alias=True, exclude_none=True)` = JS `JSON.parse(JSON.stringify())`; typed response contracts (`responses.py`) — an upgrade over JS |
| Config | **pydantic-settings** | 2.x | `.env` + env-var override, typed |
| Reporting | **allure-pytest-bdd** + Allure 3 CLI (`npx allure@3`, "awesome" UI) | 2.16.0 / 3.x | Python adapter writes allure2-format JSON; the Allure 3 CLI already consumes that format in the JS project |
| Packaging | **uv** (`pyproject.toml` + `uv.lock`) | 0.12 | venv + lock + run in one tool; CI uses `astral-sh/setup-uv` |
| Python | **3.12** (`.python-version`) | — | pytest-bdd 8.1 needs ≥3.10 and is dropping 3.9 next |

## 3. Environment caveats on this machine

- Bootstrapped 2026-09-01: `brew install uv` (0.12.8) → `uv python install 3.12` (3.12.14) → `uv sync`
  (`.venv` + `uv.lock`, committed). `uv` lives in `/opt/homebrew/bin`, uv-managed Pythons in `~/.local/bin` —
  in a non-login shell prefix commands with `export PATH="/opt/homebrew/bin:$PATH"`.
- System Python is 3.9 — never run `python3 …` for project code; always `uv run …`.
- `.env` is git-ignored; copy `.env.example`. Defaults in `src/play_api/config.py` work without it.
- Git remote uses the SSH alias `github.com-romasky` (plain `github.com` has no key for this account).
- Node 22 is installed (`npx allure@3` works).

## 4. Layout

```
features/play_qa_api/*.feature   # copied 1:1 from play-api-js — the SPEC. Do not rephrase steps.
src/play_api/
  config.py                      # Settings (BASE_URL, REQUEST_TIMEOUT seconds)
  context.py                     # ScenarioContext: save/get/opt/str/response/body, _g/_l scoping
  api/paths.py                   # all endpoint paths
  api/client.py                  # request() choke point: Allure sub-step + attachments; bearer_header()
  models/requests.py             # pydantic builders: CreateUserReq/ProfileReq/…/LoginReq/CreateMailboxReq/SendMessageReq
  models/responses.py            # pydantic contracts + assert_* helpers (error code, request_id, login, user core fields, list/no-field, messages/no-full-body)
  utils/json_path.py             # get_path / has_path (typed dotted-path checks; never substring matching)
  utils/generator.py             # random data with the API's exact shapes
  utils/gherkin.py               # raw_json(): unescapes \" in `… with raw body "{…}"` step args before json.loads
tests/
  conftest.py                    # pytest_plugins (step modules), ctx/global_ctx fixtures, pytest_bdd_apply_tag (@allure.label.* → allure_label), rate-limit pacing
  test_features.py               # scenarios("play_qa_api") — binds every feature file
  steps/{common,accounts,mail,health,basic_auth,options}_steps.py   # ← the porting work happens here
docs/API_REFERENCE.md            # API contract (error codes, validation rules) — ground truth for expectations
tools/check_steps.py             # OFFLINE: every feature step ↔ exactly one step def (pytest --co does NOT check this)
allure-results/categories.json   # committed; never --clean-alluredir
.github/workflows/test.yml       # uv + pytest → npx allure@3 generate → GitHub Pages (same layout as JS)
```

## 5. JS → Python mapping (how to port a step)

| play-api-js | play-api-python |
|---|---|
| `Given('Create minimal user and save response as {string}', async (varName) => …)` | `@given(parsers.parse('Create minimal user and save response as "{var}"'))` `def _(ctx, var): …` |
| `{string}` / `{int}` | `"{name}"` / `{name:d}` inside `parsers.parse` |
| `ctx.save / get / opt / str` | same names on the `ctx` fixture (`ScenarioContext`) |
| `ctx.get(varName, true).data` | `ctx.body(var)`; the raw `httpx.Response` via `ctx.response(var)` |
| `client.post(path, body, headers)` | `client.post(path, body, headers)` — body is a `dict` (`Model.to_body()`) |
| `auth.bearer / raw / none` | same helper in `accounts_steps.py` (`auth.bearer(ctx, key)` needs `ctx`) |
| `createUserReq({...})` strips undefined | `CreateUserReq(...).to_body()` (`exclude_none`) |
| `errorResponse.assertCode(res, code)` | `responses.assert_error_code(ctx.body(var), code)` |
| `getPath / hasPath` | `get_path / has_path` (arrays: `"messages.0.subject"`) |
| `Before({tags: …})` sleeps | `_rate_limit_pacing` autouse fixture in `conftest.py` (reads allure_label markers) |
| `@allure.label.epic:X` tags | translated by `pytest_bdd_apply_tag` → `pytest.mark.allure_label("X", label_type="epic")` |
| `Then … (Cucumber And/Then interchangeable)` | pytest-bdd matches by text **and keyword** (`And` inherits the previous one). Assertions → `@then`, HTTP actions → `@when`/`@given`; data-setup steps that the features use after Given *and* When/Then (`Extract`, `Generate …`, `Save …`, `Get and check status code`) → keyword-agnostic `@step` |

All six step modules are fully ported (94 step definitions; `tools/check_steps.py` → 181 scenarios / 1082 steps, 0 missing, 0 ambiguous).

## 6. Conventions (inherited from the JS/Java projects — MUST follow)

- **Feature files are the spec.** Never change step phrasing to fit Python; change the step definition.
  Scenario Outlines are counted per row (181 total). Tags: `@Run` required + `@Smoke/@Positive/@Negative/@Flow`
  + `@allure.label.{epic,suite,subSuite,story,severity}`.
- HTTP only through `play_api.api.client`; paths only from `play_api.api.paths`; bodies via `models/requests.py`
  (`… with raw body "{…}"` steps are the only place raw JSON is allowed — for deliberately broken payloads).
- **Every negative scenario asserts BOTH status and `error.code`** (exceptions with no envelope: `GET /auth/basic`, HEAD/GET `/users/exists/:id`).
- Typed checks only: `get_path/has_path` or pydantic contracts. No `str(body)` / `in json.dumps(...)` substring checks.
- Context passthrough: unknown keys resolve to the literal. Don't create context keys that collide with
  literals used in assertions (bio → `profileBio`).
- Rate limits are **paced, never retried** (2 s per User_Management scenario, 13 s per Login scenario).
  `TokenSecurityTests` carries `suite:User_Management` on purpose to inherit the 2 s pacing.
- Single-threaded (`ScenarioContext` global store) — do not add pytest-xdist.
- Keep step modules thin; logic belongs in `src/play_api`. No dead exports (the JS project was cleaned of these — keep it that way).

## 7. Porting plan (tick as you go)

- [x] **P0 Bootstrap** (2026-09-01) — `brew install uv`, `uv python install 3.12`, `uv sync`, `uv run pytest --co -q` collects 181 items with **no** `StepDefinitionNotFoundError` for the 6 completed modules (expect many for the unported ones).
- [x] **P1 common_steps.py** — port every generic step from `src/steps/commonSteps.js` (generators, header asserts, `is one of`, `not a server error`, `contains`, `is present`, `body is empty`, `has request_id`, context asserts, `Print response`).
- [x] **P2 accounts_steps.py** — port `src/steps/accountsSteps.js` completely (create × 5, Set employment/theme/interests/bio, username of length, GET user, list + string page/per_page, exists HEAD/GET, update/patch/delete/logout × {token, raw auth header, no auth token}, login, typed assertions).
- [x] **P3 mail_steps.py** — port `src/steps/mailSteps.js` + `assert_messages_have_no_full_body`.
- [x] **P4 Green run** (2026-09-01) — Smoke 17/17 (40 s); full run **181 passed in 8 min 16 s** (JS: ≈10 min). First attempt hit a 521 origin outage (~3 min), second surfaced the h11 header-trim issue (6 "empty Bearer" scenarios) — both recorded in §8/§9. Always `curl /api/v1/health` first.
- [x] **P5 Allure** (2026-09-01) — `npx allure@3 generate allure-results -o allure-report` → 181/181; Epic→Suite→SubSuite tree = 18 sub-suites with the exact per-feature counts; 298 HTTP sub-steps, 838 attachments. (`summary.json` "total" can look odd when results contain retries — check `data/test-results/*.json` labels instead.)
- [x] **P6 CI** (2026-09-01) — first push run green (181 passed); GitHub Pages enabled via API (source `gh-pages` / `/`) → https://romasky.github.io/play-api-python/latest/. No `BASE_URL` variable needed (default). Node 20 deprecation annotations on the actions are informational.
- [x] **P7 Docs** — README done (mirrors the JS README + porting-notes table). Wiki: 16 pages written as a git repo; GitHub only creates `play-api-python.wiki.git` after the first page is created in the web UI — then `git push -f origin master` from the wiki checkout.
- [ ] **P8 Python-only upgrades (optional)** — response contracts for every 2xx shape (already partly in `responses.py`), `Faker` for richer data, `ruff` + `mypy` in CI.

## 8. Live-API facts not in `docs/API_REFERENCE.md` (verified 2026-08-31)

- `GET /users/list` with non-positive / non-numeric `page` or `per_page` → `400 INVALID_PAGINATION`; `per_page > 100` → 200 (clamped). Feature asserts only "not 5xx, one of 200/400".
- `OPTIONS /users/options` → **204, empty body** (Cloudflare), not the documented 200 + JSON.
- Auth middleware order confirmed: no header → `MISSING_TOKEN`; `Bearer ` / `Bearer` / `Basic …` / no prefix → `INVALID_TOKEN_FORMAT`; any other `Bearer x` → `INVALID_TOKEN`.
- `GET /auth/basic` works live (admin/admin); 401 body `{error:"Unauthorized", message}` + `WWW-Authenticate`.
- Validation error for bio > 500: `error.details == "bio must be at most 500 characters long"` (no `validation[]`).
- Origin outages show as Cloudflare 521 `origin_down` — not a test failure.

## 9. Pitfalls specific to the Python stack

- `allure-pytest-bdd` does **not** parse `@allure.label.*` Gherkin tags (checked in its source: only `allure_label` markers) — the `pytest_bdd_apply_tag` hook in `conftest.py` does it. `allure-behave` would do it natively; irrelevant here.
- allure-python has no per-step *parameters* (JS used `ctx.parameter`) — `client.request()` attaches small JSON/TEXT attachments instead. `allure.attach` is sync, so the JS "attachment after step closed" race does not exist.
- h11 (httpx's HTTP/1.1 layer) **refuses to send** a header value with surrounding whitespace (`LocalProtocolError: Illegal header value b'Bearer '`) — found on the first full run (6 "empty Bearer" scenarios). `client.request()` therefore trims header values before sending, which is exactly what axios did in the JS port, so `"Bearer "` reaches the server as `"Bearer"` → `INVALID_TOKEN_FORMAT`. The Allure attachment still shows the untrimmed value.
- `Get and check status code {code:d} from "{var}"` is used after `Then` **and** `When` in the features — it is registered with both decorators.
- `pytest -m` marker names come from tags; tags with dots/colons never reach `pytest.mark` because the hook converts them (otherwise pytest warns about unknown marks).
- Do not use `--clean-alluredir` — it would delete the committed `allure-results/categories.json`.
- `pytest-bdd` 8 requires the file to start with `Feature:` and tags without spaces — the copied features already comply.
- **`pytest --co` does NOT detect undefined steps** — pytest-bdd 8 resolves step definitions at runtime, one scenario at a time — and it never reports *ambiguous* steps at all (two matching definitions → one silently wins by fixture-resolution order). Run `uv run python tools/check_steps.py` (offline, < 1 s) — it reports both.
- `parsers.parse` `{name}` is `.+?` → needs ≥ 1 char. `Set interests ""` (CreateUserTests:79) therefore uses `parsers.re(r'Set interests "(?P<csv>.*)"')`.
- Cucumber's `{string}` unescaped `\"`; pytest-bdd passes step text verbatim → `… with raw body "{\"email\":…}"` must go through `utils.gherkin.raw_json()`.
- `ctx.body()` returns the raw text for non-JSON bodies (Cloudflare 521 HTML) so failures read "Field 'id' not found … Body: <!DOCTYPE html>…521: Web server is down" (status *failed*, category "API Defects") rather than a JSONDecodeError (*broken*). A whole run failing that way = origin outage, re-run later.
- Registering one function with both `@when` and `@then` is not needed (and fragile) — use `@step`.

## 10. Useful commands

```bash
uv sync                                   # install
uv run pytest --co -q                     # collect only — 181 items; does NOT check step definitions
uv run python tools/check_steps.py        # offline: every step ↔ exactly one step definition (run this first)
uv run pytest -m Smoke                    # 17 scenarios, ~1 min
uv run pytest -k empty_bearer               # by scenario name (test ids are snake_case)
uv run pytest -k "empty_bearer or malformed_authorization"   # by test-name substring — feature-file paths do NOT work with scenarios()
BASE_URL=https://staging.play-qa.com uv run pytest
npx --yes allure@3 generate allure-results -o allure-report && npx --yes allure@3 open allure-report
```

Reference material: the JS repo above (steps + wiki), the Java repo `/Users/macbook/Documents/Storage/rs/projects/play-api-java`
(same features with typed-DTO step phrasing — do **not** copy its step names), and `docs/API_REFERENCE.md`.
