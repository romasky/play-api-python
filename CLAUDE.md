# play-api-python — agent entry point

**Read this file first.** It is the single source of context for continuing this project.
Everything an agent needs — goal, stack decisions (and why), conventions, the plan with checkboxes,
live-API quirks and known pitfalls — is here. Update the checkboxes as you go.

## 1. Mission

BDD API test framework for https://www.play-qa.com — started as the Python port of **play-api-js**
(`/Users/macbook/Documents/Storage/rs/projects/play-api-js`, https://github.com/romasky/play-api-js; 181 scenarios
in 18 feature files, ported 1:1 and green 2026-09-01) and since 2026-10-26 extended to **the whole Swagger spec**
(`https://play-qa.com/swagger/doc.json`, snapshot `docs/openapi.json`): **799 scenarios in 45 feature files,
79/79 spec operations called** (`tools/spec_coverage.py`).

**The spec is the live API + Swagger, no longer the JS copy.** The 18 original feature files were edited where the
API changed (403 FORBIDDEN, exact pagination codes) and gained scenarios; the other 27 files are new.

**Definition of done:** the lint gate passes, `uv run pytest` is green against the live API, every Swagger
operation is called at least once, and the Allure 3 report keeps the Epic → Suite → SubSuite → Story hierarchy.

## 2. Stack (decided 2026-09-01 after research — do not re-litigate without a reason)

| Layer | Choice | Version (PyPI, Sep 2026) | Why |
|---|---|---|---|
| Runner + BDD | **pytest + pytest-bdd** | pytest ≥8.3 / pytest-bdd 8.1.0 | `gherkin-official` parser (outlines, tags, datatables), pytest fixtures/markers/IDE; behave 1.3.3 was the alternative (closer to Cucumber, but its own runner and no fixtures) |
| HTTP | **httpx2** (`import httpx2 as httpx`) | 2.12.0 | Same API as httpx, now maintained by Pydantic Services (original `httpx` stalled at 0.28.1, Dec 2024); never raises on 4xx/5xx; single `timeout` |
| WebSocket | **websockets** (sync client) | 17.x | httpx cannot speak WebSocket — only `/ws/echo` uses it (`services/realtime.py`) |
| Models | **pydantic 2** | 2.13 | `model_dump(by_alias=True, exclude_none=True)` = JS `JSON.parse(JSON.stringify())`; typed response contracts |
| Config | **pydantic-settings** | 2.x | `.env` + env-var override, typed |
| Reporting | **allure-pytest-bdd** + Allure 3 CLI (`npx allure@3`, "awesome" UI) | 2.16.0 / 3.x | Python adapter writes allure2-format JSON; the Allure 3 CLI consumes it |
| Packaging | **uv** (`pyproject.toml` + `uv.lock`) | 0.12 | venv + lock + run in one tool; CI uses `astral-sh/setup-uv` |
| Quality | **ruff** + **mypy** (strict, `pydantic.mypy` plugin) | 0.16 / 2.3 | CI gate before tests; config in `pyproject.toml` |
| Python | **3.12** (`.python-version`) | — | pytest-bdd 8.1 needs ≥3.10 and is dropping 3.9 next |

## 3. Environment caveats on this machine

- Bootstrapped 2026-09-01: `brew install uv` (0.12.8) → `uv python install 3.12` (3.12.14) → `uv sync`
  (`.venv` + `uv.lock`, committed). `uv` lives in `/opt/homebrew/bin`, uv-managed Pythons in `~/.local/bin` —
  in a non-login shell prefix commands with `export PATH="/opt/homebrew/bin:$PATH"`.
- System Python is 3.9 — never run `python3 …` for project code; always `uv run …`.
- `.env` is git-ignored; copy `.env.example`. Defaults in `src/play_api/config.py` work without it.
- Git remote uses the SSH alias `github.com-romasky` (plain `github.com` has no key for this account).
- Node 22 is installed (`npx allure@3` works).
- When chaining shell commands that end in `git commit`, never put a `;` after a gate command — a failing
  lint then still commits (happened once on this branch; the commit was amended).

## 4. Layout — three layers: steps → services → client

```
features/play_qa_api/*.feature   # THE SPEC (45 files). Phrase new steps like the existing ones.
src/play_api/
  config.py                      # Settings: BASE_URL, REQUEST_TIMEOUT (s), ADMIN_SEED_CODE
  context.py                     # ScenarioContext: save/get/require/opt/str/render/response/body, _g/_l scoping, defer()
  pacing.py                      # per-ENDPOINT throttle (token-bucket refill intervals), called by client.request()/stream()
  jwt_session.py                 # run-wide shared JWT session in the _g store (one rate-limited JWT login pair)
  timing.py                      # timed(call) → Outcome(response | TimeoutException, seconds)
  assertions.py                  # generic typed checks: ordering, every item, pages, Link, SSE, JWT claims, CF pages; as_text()
  api/paths.py                   # ALL endpoint paths (+ API_DOCUMENTS name → path)
  api/client.py                  # request(): the only HTTP choke point — Allure sub-step, attachments, pacing, 2xx contract;
                                 # RawJson (verbatim body), ContractViolation (carries the response), Headers/Params types
  api/auth.py                    # header builders: bearer / raw / none / basic
  services/<domain>.py           # one module per API domain; plain values in, httpx.Response out (no ctx, no asserts);
                                 # login.py = /login, /auth/basic, /store/login; realtime.py = SSE + WsSession
  models/requests.py             # pydantic request bodies (`Body.to_body()`; the client serialises models itself)
  models/factories.py            # bodies: minimal user / admin, user_from_context(ctx), bug-report variants, cart(spec)
  models/responses/<domain>.py   # STRICT contracts + CONTRACTS_2XX rows per domain + domain assert_* helpers
  utils/json_path.py             # get_path / has_path (typed dotted-path checks; never substring matching)
  utils/generator.py             # random data with the API's exact shapes (+ unique_country for list isolation)
  utils/gherkin.py               # raw_json(), unescape_quotes(), query_pairs()
  utils/lookup.py                # choose(table, name, what) — the one "unknown X, expected one of …" lookup
  utils/jwt_tools.py             # craft(kind, genuine): forged / malformed JWTs, stdlib only
  utils/samples.py               # in-memory upload files (PNG, PDF, fake PNG, .exe, 5 MiB boundaries …)
  utils/webhook_sign.py          # X-PlayQA-Signature (HMAC-SHA256, t=…,v1=…)
tests/
  unit/                          # OFFLINE unit tests of src/play_api + tools (MockTransport, monkeypatch) — the coverage
                                 # source for the ub-mode gates; own conftest, run via tools/ub_gates.py (never the live suite)
  conftest.py                    # pytest_plugins (13 step modules), ctx fixture (runs ctx.defer cleanups), tag→allure_label, --epic
  test_features.py               # scenarios("play_qa_api") — binds every feature file (recursive)
  steps/support.py               # quoted() parser, bearer()/raw_header(), save_created() (cleanup-safe create), route_call()
  steps/*_steps.py               # common, accounts, admin, auth (basic+JWT+store), mail, files, webhooks, bug_reports,
                                 # buggy, chaos, challenges, system (health/options/docs/reCAPTCHA), realtime (SSE/WS)
docs/API_REFERENCE.md            # API contract (error codes, validation rules) — ground truth for expectations
docs/openapi.json                # Swagger snapshot the expectations were written against (tools/spec_drift.py)
tools/check_steps.py             # OFFLINE: step ↔ exactly one definition, every feature has an epic; lists unused definitions
tools/spec_drift.py              # live Swagger vs snapshot: new / removed operations, changed response codes
tools/spec_coverage.py           # which spec operations a run called (most specific template wins; reads allure-results)
tools/_spec.py                   # shared snapshot loading / operation iteration
tools/ub_gates.py                # ub-mode gates: unit | crap (CRAP < 10) | dry (< 0.8) | mutate <path> | fast | all — local only
.claude/skills/ub-mode/SKILL.md  # https://github.com/unclebob/ub-mode + "In this repo" mapping (/ub-mode)
.claude/agents/ub-*.md           # ub-implementer (Make it Work), ub-gatekeeper (Make it Right), ub-reviewer (read-only)
allure-results/categories.json   # committed; never --clean-alluredir
.github/workflows/test.yml       # lint → test matrix (6 epic groups) → report (merge, coverage, Allure, Pages); spec-drift
```

## 5. How to add or change a step

| Need | Do this |
|---|---|
| A new endpoint | path in `api/paths.py` → function in `services/<domain>.py` → contract + `CONTRACTS_2XX` row in `models/responses/<domain>.py` (registered in `__init__`) → step → feature |
| Step text with only quoted, quote-free args | `@when(quoted('Do "{x}" and save response as "{var}"'))` — `"{x}"` matches `[^"]*` (empty allowed), so sibling phrasings never overlap |
| Step text with a raw JSON body | `parsers.parse(...)` + `raw_json(...)` (JSON carries `\"`, which `quoted()` cannot match). Invalid JSON on purpose comes back as `RawJson` and is sent verbatim |
| Integer arg | `parsers.parse` with `{n:d}` |
| Context values | `ctx.str(key)` → value, or the literal with `${key}` interpolated; `ctx.render("q=${k}")` for queries / raw bodies / raw headers; `ctx.require(key)` when a previous step must have saved it |
| Query strings | `"limit=3&filter=a:1&filter=b:2&sort="` → `query_pairs(ctx.render(q))` keeps repeats and empty values |
| Auth headers | `bearer(ctx, token_key)`, `raw_header(ctx, value)`, `auth.none()` (tests/steps/support.py) |
| Created server-side state | `save_created(ctx, var, create, cleanup)` — registers the delete even when the 201 body breaks its contract; else `ctx.defer(...)` |
| Setup a user / admin | `Given a user with token "t"` / `… with id "i" and token "t"` / `an admin with …` (new features); the original 18 keep `Create minimal user …` + `Extract` |
| Rate-limited endpoint | add its bucket to `pacing._BUCKETS` (method, path regex, bucket name, refill seconds) |
| Keywords | assertions `@then`, HTTP `@when`/`@given`; steps used after Given *and* When/Then → `@step` |
| Run one area | `uv run pytest --epic Webhooks` (repeatable; Allure epic label) |

The old JS → Python porting table (`{string}` → `"{x}"`, `ctx.get(v, true).data` → `ctx.body(v)`,
`createUserReq` → `CreateUserReq(...).to_body()` …) still holds for the original 18 files.

## 6. Conventions (MUST follow)

- **Feature files are the spec.** Never change step phrasing to fit Python; change the step definition.
  Tags: `@Run` required + `@Smoke/@Positive/@Negative/@Flow` + `@allure.label.{epic,suite,subSuite,story}`;
  `@allure.label.severity:critical` only where it applies (the default is normal). A `@Positive` scenario may assert an
  error status when that status IS the endpoint's behaviour (chaos) — say so in a comment.
  Every new epic must be added to the CI matrix (the lint job fails otherwise).
- HTTP only through `play_api.api.client` (via a service); paths only from `play_api.api.paths`; bodies via
  `models/requests.py` / `models/factories.py` (`… with raw body "{…}"` steps are the only place raw JSON is allowed).
- **Every negative scenario asserts BOTH status and `error.code`** (exceptions with no envelope: `GET /auth/basic`,
  HEAD/GET `/users/exists/:id`, `/verify-recaptcha` `{success, error:<string>}`, unrouted methods `404 page not found`,
  Cloudflare-replaced 502/504/52x pages).
- Typed checks only: `get_path/has_path`, pydantic contracts or `play_api.assertions`. No substring checks on a dumped body.
- New 2xx endpoint → contract **and** `CONTRACTS_2XX` row; `client.request()` raises `ContractViolation` inside the HTTP
  step when a 2xx body violates it. Contracts are STRICT (`"900"` is not an int, `"true"` not a bool) and list only
  always-present fields (`extra="allow"`; optional → `| None = None`; "always present but nullable" → `Field(...)`).
- The lint gate (the CI `lint` job): `uv run ruff check . && uv run ruff format --check . && uv run mypy &&
  uv run python tools/check_steps.py` + "every epic is in the test matrix" — all must pass.
  Gherkin step strings longer than 120 chars get `# noqa: E501` (never wrap the phrase).
- Context passthrough: unknown keys resolve to the literal. Don't create context keys that collide with
  literals used in assertions (bio → `profileBio`).
- Rate limits are **paced, never retried** — per endpoint in `play_api.pacing` (≥ refill interval between two calls
  of the same bucket). No 429 scenarios: they would drain the shared per-IP buckets.
- Shared data (users list ≈ 400 users from other clients): assert exact counts only inside a filter that isolates
  your own data (`Generate unique country` + `filter=address.country:${country}`).
- Single-threaded (`ScenarioContext` global store) — do not add pytest-xdist; parallelism = the CI matrix (one IP each).
- Keep step modules thin; logic belongs in `src/play_api`. No dead exports.

## 7. Plan (tick as you go)

- [x] **P0–P8 Port** (2026-09-01) — bootstrap, all six JS step modules ported, 181/181 green in 8 min 16 s, Allure 3
  tree, CI + Pages (https://romasky.github.io/play-api-python/latest/), README + wiki (16 pages, sibling checkout
  `../play-api-python.wiki`, branch `master`), ruff/mypy gate, Faker, 2xx contracts, action bumps
  (checkout@v7 / setup-uv@**v10.0.1** — no floating `v8+` tags exist / setup-node@v7 / upload-artifact@v7 /
  download-artifact@v7 / actions-gh-pages@v4).
- [x] **P9 Feature 17 fix** (2026-10-26, `aa5128c`) — another user's valid token → 403 FORBIDDEN (was 401).
- [x] **P10 Whole-spec coverage** (2026-10-26, branch `feat/swagger-coverage`) — service layer, per-endpoint pacing,
  spec drift + coverage tools, CI matrix; users list v2, Feature 17 reads, admin, JWT, store, files, webhooks,
  SMTP simulator, bug reports, buggy API, chaos, challenges, API docs, SSE/WebSocket, reCAPTCHA.
  800 scenarios, 79/79 operations.
- [x] **P11 Review fixes + refactor** (2026-10-26) — three independent reviews (correctness, simplicity, conventions)
  applied: cleanup-safe creates, strict contracts, spec-coverage attribution, CI re-run safety, WebSocket behind the
  service, composite setup steps, shared support helpers, request models for every body, dead code removed.
- [x] **P12 Wiki** (2026-10-26, wiki `f094437`) — all 15 pages rewritten for the new framework + API-Domains,
  Spec-Drift-and-Coverage. First CI matrix run (PR #1): green in 7 min 43 s wall time (serial ≈ 21 min).
- [x] **P13 ub-mode** (2026-10-28) — https://github.com/unclebob/ub-mode as a project skill + three agents
  (`ub-implementer`, `ub-gatekeeper`, `ub-reviewer`); offline `tests/unit` suite as the coverage source; crapper /
  dryer / mutator via `tools/ub_gates.py` (`ub` dependency group, pinned commits). Local only — not in CI yet.

## 8. Live-API facts not in the Swagger spec (verified 2026-10-26)

General
- 429 never carries `Retry-After` / `X-RateLimit-*`. Buckets (per IP): create-user + create-admin + challenge start
  1/600 ms burst 100 · `/login` 1/12 s burst 5 · `/jwt/login` separate, same rate, **every call counts** (400s too) ·
  `/jwt/decode` 1/2 s burst 10 · uploads and inbox creation 10/min burst 5 · store login and bug reports 30/min burst 10
  (400s count) · global 10/s burst 20.
- Unrouted methods → `404 text/plain "404 page not found"`, never 405 (HEAD /health, POST /chaos/cache, …).
- Cloudflare replaces the origin body of 502/504/520–526 (incl. `/chaos/timeout`) with its own page — plain text, or
  **HTML when the client accepts gzip (httpx always does)**. Assert the status only (`is a Cloudflare error page`).
- `metadata` optional fields are omitted, not null; create returns ns timestamps, GET returns ms.

Users / auth
- Feature 17: a valid token of ANOTHER user on PUT/PATCH/DELETE/logout → **403 `FORBIDDEN`** (since 2026-10-23), also
  for a non-existent or malformed id (never 404 — ids cannot be probed). Ownership is checked before body validation.
- Reads (`/users/get`, `/users/list`) stay public; a PRESENT bad header → 401 (`Bearer`/`Basic`/no prefix/lowercase →
  `INVALID_TOKEN_FORMAT`, unknown/revoked → `INVALID_TOKEN`), checked before the id. Only the owner sees `metadata.last_login_ip`.
- `/users/list`: validation order page → limit → per_page → sort → filter → search; `limit` wins over `per_page` (both
  validated); >100 clamped; Link URLs are relative and rewrite `per_page` → `limit`; `settings.language:EN` accepted.
- Admin: seed `play-qa-admin` (published in the UI); non-admin → 403 `ADMIN_REQUIRED`; admin on any foreign/missing id →
  403 `FORBIDDEN`; wrong/absent seed → 403 `INVALID_SEED_CODE` (body validation 400 first, uniqueness 409 last);
  `/admin/users` has no X-Total-Count/Link; self-demotion is irreversible.
- JWT: refresh token NOT single-use, body only (Authorization ignored), new access always 900 s; `/jwt/decode` format
  errors are 400 `INVALID_JWT_FORMAT` (me/refresh: 401 `INVALID_TOKEN_FORMAT`); JWTs > ~12 KB in a header → CF 520.
- Store: lock checked after the password (wrong password on locked_out_user → 401); performance_glitch_user ≈ 3 s.
- `OPTIONS /users/options` → 204, empty body (Cloudflare). `GET /auth/basic` works (admin/admin).

Files / webhooks / mail
- Files: content type is sniffed (Go `DetectContentType`; a leading `ff fe` is a UTF-16 BOM → text/plain);
  metadata ignores a bad token; a token-owned file deleted by anyone else, or with no token → 404 (not 401/403);
  HEAD download → 404; no checksum header (compare bytes).
- Webhooks: two 429 codes (`RATE_LIMIT_EXCEEDED`, `TOO_MANY_INBOXES` at 20 active per IP); signature tolerance ±300 s;
  empty signature header = none (`null`); events `per_page` invalid → silently 20; event `query`/`body` keys are
  OMITTED when empty (HEAD included); no `success` field on any webhook 2xx.
- send-to: magic local parts match on ANY domain (or none), case-insensitive; accepted mail is stored in the SENDER's
  mailbox, never delivered; no recipient validation; magic local parts → 409 `RESERVED_LOCAL_PART` on mailbox create.

Chaos / buggy / challenges / misc
- gzip follows the client's Accept-Encoding (spec: always gzip); redirect status = `type` (301/302/307/308), Location
  relative, `/done` always says `redirected:true`; flaky body is returned on every status.
- Buggy bugs are permanent and deterministic (full page drops its last item; cart ignores the last position; 09:00 in UTC).
- Challenges: malformed `attempt_id` → 409 `NO_OPEN_ATTEMPT`; `can_reset` only with `target_missing`; the locale hint
  for patch-first-name is wrong (partial `profile` PATCH → 400 "last name is required").
- SSE bounds steps 5–100, interval_ms 100–2000 (not in the spec); WS max message 32 KiB (close 1009 arrives ~20 s
  later — not tested); reCAPTCHA 400 message is "Invalid request body", a bogus token → 200 `success:false`.
- `RemoteProtocolError: Server disconnected without sending a response` — Cloudflare's edge drops pooled keep-alive
  connections without notice (every response says `connection: keep-alive`; the `cf-ray` colo can change mid-job).
  It failed the scheduled `auth` job 2026-10-26/27 (1–5 ms after the previous response, random scenario).
  `client.request()` retries it ONCE, re-paced, with a `Retry` attachment; httpx itself never retries.

## 9. Pitfalls specific to the Python stack

- **`parsers.parse` `{x}` is a lazy `.+?` that swallows quotes**: `… for "{id}" and save …` also matches
  `… for "a" with raw auth header "b" and save …` → two definitions, pytest-bdd silently picks one. Use `quoted()`.
  `tools/check_steps.py` reports such ambiguity (it found a latent one in the original mail steps).
- `parsers.parse` `{name}` needs ≥ 1 char → `equals ""` needs a regex (`Assert field … equals` uses one) or `quoted()`.
- **Examples-table cells deliver `\"` with a DOUBLED backslash** (step text: single) — `unescape_quotes()` handles both.
- **Gherkin trims table cells** — a value with leading/trailing whitespace must live in the step text, not a table.
- `allure-pytest-bdd` does not parse `@allure.label.*` tags — the `pytest_bdd_apply_tag` hook in `conftest.py` does.
- h11 refuses header values with surrounding whitespace — `client.request()` trims them (axios parity).
- httpx: `data=` alone sends x-www-form-urlencoded, not multipart — form fields go in `files=` as `(None, value, None)`.
  httpx never follows redirects unless `follow_redirects=True`; 301/302 turn POST into GET, 307/308 keep it.
- HEAD responses never have a body — never assert a text body on HEAD.
- Python unbinds the `except … as exc` name when the block ends — a deferred lambda must capture a local copy
  (see `save_created`), or it raises NameError at cleanup time.
- `pytest --co` does NOT detect undefined or ambiguous steps — run `tools/check_steps.py`.
- `ctx.body()` returns the raw text for non-JSON bodies, so a 521 page fails as "Field 'id' not found … <!DOCTYPE html>"
  (status *failed*) rather than a JSONDecodeError. A whole run failing that way = origin outage, re-run later.
- **Never run `crapper` / `mutator` bare** — by default they run plain `pytest`, i.e. the live suite (per mutant!).
  Always go through `tools/ub_gates.py`: crapper reads lcov from `tests/unit`; mutator runs `tests/unit` per mutant
  with `--no-coverage`, so a site no test reaches fails as a survivor instead of being skipped "uncovered". The `ub`
  dependency group is not installed by plain `uv sync` (`uv run --group ub …` installs it); the first gate run downloads
  the tree-sitter Python grammar (needs network — outside the Claude sandbox). dryer always exits 0; the script fails on
  a candidate in `.metrics/dry.edn`.
- Never edit `src/`, `tools/` or `tests/unit/` while mutator runs — workers symlink the live files, a failing test
  "kills" every mutant. If it happened: `rm -rf .metrics/mutate` and re-run (it is differential otherwise).
- Unit tests must spell out expected values, not rebuild them from the module's constants — a test that derives the
  expected command from `ub_gates.UNIT` pinned the very bug it should have caught.
- The live run never collects `tests/unit` (`collect_ignore` in `tests/conftest.py`); the gate script passes the path
  explicitly with `-o addopts= --confcutdir=tests/unit`, so neither the marker filter nor `tests/conftest.py` applies.
- Do not use `--clean-alluredir` — it would delete the committed `allure-results/categories.json`.
- `spec_coverage.py` counts calls in `allure-results/`, which accumulates across local runs — for an honest number
  run it on a fresh results dir (CI does: the report job merges only this run's artifacts).

## 10. Useful commands

```bash
uv sync                                   # install
uv run python tools/check_steps.py        # offline: every step ↔ exactly one step definition (run this first)
uv run ruff check . && uv run ruff format --check . && uv run mypy   # + check_steps = the CI lint job
uv run pytest -m Smoke                    # 92 scenarios
uv run pytest --epic Chaos_Engineering    # one Allure epic (repeatable) — what the CI matrix does
uv run pytest -k "empty_bearer or malformed_authorization"   # by test-name substring (feature paths do NOT work)
uv run python tools/spec_drift.py         # live Swagger vs docs/openapi.json (--update to accept a new spec)
uv run python tools/spec_coverage.py      # spec operations called by the runs in allure-results/
uv run --group ub python tools/ub_gates.py fast           # ub-mode quick loop: offline unit tests + crapper + dryer
uv run --group ub python tools/ub_gates.py all            # ub-mode full gate: fast + mutator on the git-changed sources
uv run --group ub python tools/ub_gates.py all src/play_api/pacing.py      # … or on these paths
BASE_URL=https://staging.play-qa.com uv run pytest
npx --yes allure@3 generate allure-results -o allure-report && npx --yes allure@3 open allure-report
```

Reference material: the JS repo above (steps + wiki), the Java repo `/Users/macbook/Documents/Storage/rs/projects/play-api-java`,
the API backend `/Users/macbook/Documents/Storage/rs/projects/play-qa-api` (Go; `internal/middleware/ratelimit.go`
has the bucket table), `docs/API_REFERENCE.md` and `docs/openapi.json`.
