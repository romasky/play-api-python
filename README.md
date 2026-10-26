# play-api-python — API Test Automation Framework

[![API Tests — play-qa.com](https://github.com/romasky/play-api-python/workflows/API%20Tests%20%E2%80%94%20play-qa.com/badge.svg)](https://github.com/romasky/play-api-python/actions)
[![Allure Report](https://img.shields.io/badge/Allure-Report-brightgreen)](https://romasky.github.io/play-api-python/latest/)

**play-api-python** is a BDD API test automation framework for [play-qa.com](https://www.play-qa.com), built with
Python 3.12, pytest + pytest-bdd, pydantic 2, httpx and Allure Report 3 — **799 Gherkin scenarios in 45 feature files
calling all 79 operations of the [Swagger spec](https://play-qa.com/swagger/index.html)**: users and admin, opaque-token,
JWT, Basic and store auth, temporary mail with an SMTP simulator, file storage, webhooks, bug reports against an
intentionally buggy API, chaos engineering, guided challenges, Server-Sent Events and WebSocket.

---

## 📊 Allure Report

🔗 **[View Latest Report](https://romasky.github.io/play-api-python/latest/)**

---

## ✨ Key Highlights

- **Whole-spec coverage, measured** — `tools/spec_coverage.py` maps every HTTP call in the Allure results onto the
  Swagger path templates; CI fails below 100 %. `tools/spec_drift.py` compares the live Swagger with the committed
  snapshot, so an API change shows up as a precise diff (`~ DELETE /users/delete/{id} responses +403`)
- **Every negative scenario asserts both the HTTP status and `error.code`** — 57 distinct error codes, each verified
  against the live API, including validation order ("which error wins")
- **Strict typed contracts** — pydantic models (strict mode: `"900"` is not an int) for every 2xx JSON shape;
  `client.request()` validates each 2xx body automatically, on top of dotted-path checks (`Assert field "x.y" is absent …`) — never substring matching
- **Three-layer design** — Gherkin steps → domain services → one HTTP choke point (Allure step, attachments,
  pacing, contract check). Steps never build paths or touch the transport
- **Rate limits paced per endpoint** — the client spaces calls to each server-side token bucket at its refill
  rate, so buckets never drain and scenarios that hit no limited endpoint never wait (paced, never retried)
- **Security regression guards** — absent / empty / malformed `Authorization` headers, cross-account writes
  (401 vs 403), forged / tampered / `alg: none` JWTs, admin scoping, upload type sniffing, webhook HMAC signatures
- **Deterministic chaos** — seeded flakiness with a plan-driven retry loop, conditional requests, redirect chains
  (307/308 keep the POST body, 301/302 do not), client timeouts as asserted outcomes, gzip on the wire
- **Self-cleaning** — uploads, webhook inboxes and WebSocket sessions are torn down after each scenario, pass or fail
- **Offline step check** — `tools/check_steps.py` matches all 4 131 Gherkin steps against the step definitions and
  reports missing *and ambiguous* matches (and features without an epic) without touching the API
- **Parallel CI by IP** — six matrix jobs, one runner (IP, rate-limit budget) each; a report job merges the results

---

## 🛠 Tech Stack

| Tool | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime (`.python-version`) |
| [uv](https://docs.astral.sh/uv/) | 0.12+ | Packaging: venv, lockfile, runner |
| `pytest` | ≥ 8.3 | Test runner |
| `pytest-bdd` | 8.1 | Gherkin parser (`gherkin-official`) + step binding |
| `httpx2` | 2.12 | HTTP client (drop-in `httpx` fork maintained by Pydantic Services) |
| `websockets` | 17.x | WebSocket client (`/ws/echo` only) |
| `pydantic` | 2.x | Request builders and typed response contracts |
| `pydantic-settings` | 2.x | `.env` + environment configuration |
| `allure-pytest-bdd` | 2.16 | Allure results adapter |
| `faker` | 40.x | Human-looking test data (names, message text) |
| `ruff` / `mypy` | 0.16 / 2.3 | Lint + format / strict type-checking (CI gate) |
| Allure 3 CLI (`npx allure@3`) | 3.x | Report generation (Awesome UI) — the only Node dependency |

---

## 📁 Project Structure

```
play-api-python/
├── pyproject.toml                 # deps (uv), pytest config: markers, default -m filter, --alluredir
├── uv.lock                        # locked dependency set (CI uses --frozen)
├── .env.example                   # BASE_URL / REQUEST_TIMEOUT / ADMIN_SEED_CODE (copy to .env, git-ignored)
├── .github/workflows/test.yml     # lint → 6-job test matrix → merged report (coverage, Allure, Pages); spec drift
├── docs/
│   ├── API_REFERENCE.md           # API contract incl. live-verified behaviour — ground truth for expectations
│   └── openapi.json               # Swagger snapshot the expectations were written against
├── tools/
│   ├── check_steps.py             # offline: every feature step ↔ exactly one step definition
│   ├── spec_drift.py              # live Swagger vs snapshot
│   └── spec_coverage.py           # spec operations called by a run
├── src/play_api/
│   ├── config.py · context.py     # settings; ScenarioContext (scoping, ${key} rendering, deferred cleanup)
│   ├── pacing.py · jwt_session.py # per-endpoint throttle; shared JWT session
│   ├── timing.py                  # a call's outcome (response or client timeout) + wall time
│   ├── assertions.py              # generic typed checks (ordering, every item, Link header, pagination)
│   ├── api/                       # paths.py · client.py (the HTTP choke point) · auth.py (header builders)
│   ├── services/                  # one module per API domain: users, admin, login, jwt, mail, files, webhooks, …
│   ├── models/                    # requests.py · factories.py · responses/<domain>.py (contracts + registry)
│   └── utils/                     # generator, json_path, gherkin, jwt_tools, samples, webhook_sign
├── tests/
│   ├── conftest.py                # step-module plugins, ctx fixture + cleanup, @allure.label.* hook, --epic
│   ├── test_features.py           # scenarios("play_qa_api") — binds every feature file
│   └── steps/                     # 13 thin step modules + support.py (quote-safe parser, auth / cleanup helpers)
└── features/play_qa_api/          # 45 feature files — the executable specification
```

---

## 🚀 Quick Start

```bash
# Install uv (once), Python 3.12 and all dependencies
brew install uv            # or: curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv sync

# Static checks (same as the CI Lint job; no network needed)
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run python tools/check_steps.py      # every Gherkin step ↔ exactly one step definition

# Run all tests (default filter: @Run and not @Ignore/@Bug/@NotImplemented)
uv run pytest

# Smoke tests only (92 scenarios) / one area of the API
uv run pytest -m Smoke
uv run pytest --epic Webhooks --epic File_Storage

# Pick scenarios by name substring (feature-file paths are not selectable)
uv run pytest -k "jwt and forged"

# Is the live spec still the one the tests were written for? Which operations did the last run call?
uv run python tools/spec_drift.py
uv run python tools/spec_coverage.py

# Generate and open the Allure report locally (needs Node for the Allure 3 CLI)
npx --yes allure@3 generate allure-results -o allure-report
npx --yes allure@3 open allure-report
```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and adjust if needed:

```
BASE_URL=https://www.play-qa.com
REQUEST_TIMEOUT=20
ADMIN_SEED_CODE=play-qa-admin
```

`REQUEST_TIMEOUT` is the single httpx deadline (connect + read) in **seconds**. `ADMIN_SEED_CODE` is the seed for
`POST /users/create-admin` (published in the play-qa.com UI). Environment variables override `.env`:
`BASE_URL=https://staging.play-qa.com uv run pytest`.

---

## 🗂 API Coverage

All 79 operations of the spec are called (`tools/spec_coverage.py`). By area:

| Epic | Endpoints | Feature files |
|---|---|---|
| User_Lifecycle | `/users/create · list · get · exists · options · update · patch · delete` | CreateUser, ListUsers, ListUsersQuery, GetUser, OptionalAuthRead, UserExists, Options, UpdateUser, PatchUser, DeleteUser |
| Authentication | `/login`, `/users/logout`, `/auth/basic`, `/jwt/login · me · refresh · decode`, `/store/login` | Login, Logout, TokenSecurity, BasicAuth, JwtLogin, JwtMe, JwtRefresh, JwtDecode, StoreLogin |
| Administration | `/users/create-admin`, `/admin/stats · users · users/{id} · users/{id}/role` | CreateAdmin, Admin |
| Mail_Service | `/mail/create · {token} · messages · send · send-to` | MailboxCreate, MailboxGet, MailboxDelete, MailMessages, MailSend, MailSendTo |
| File_Storage | `/files/upload`, `/files`, `/files/{id}`, `/files/{id}/download` | FileUpload, FileAccess |
| Webhooks | `/webhooks/inbox · {token} · events · events/{id}`, `/webhooks/in/{ingest_token}` (6 methods) | WebhookInbox, WebhookCapture |
| Bug_Hunting | `/buggy · items · cart/total · schedule`, `/bug-reports` | BuggyApi, BugReport |
| Chaos_Engineering | `/chaos/cache · delay · timeout · echo · flaky · gzip · redirect · status` | ChaosCache, ChaosTiming, ChaosEcho, ChaosFlaky, ChaosTransport, ChaosStatus |
| Challenges | `/challenges`, `progress`, `{id}/hints · hints/reveal · start · verify` | Challenges, ChallengeFlow |
| System | `/health`, `/openapi.*`, `/postman/*`, `/sse/progress`, `/ws/echo`, `/verify-recaptcha` | Health, ApiDocs, Realtime, Recaptcha |

---

## 🏷 Tag Reference

Gherkin tags become pytest markers (`-m Smoke`); `@allure.label.*` tags become Allure labels.

| Tag | Meaning |
|---|---|
| `@Run` | Included in default CI run |
| `@Smoke` | Critical path — minimal fast subset |
| `@Positive` | Happy path scenario |
| `@Negative` | Error / validation scenario |
| `@Flow` | Multi-step end-to-end scenario |
| `@Ignore` | Excluded from run (known skip) |
| `@Bug` | Known failing — excluded from CI |
| `@NotImplemented` | Placeholder — excluded from CI |
| `@allure.label.{epic,suite,subSuite,story,severity}:X` | Allure report hierarchy / severity (`--epic X` selects by it) |

---

## 📈 Scenario Count

Scenario Outlines are counted per example row.

| Epic | Scenarios |
|---|---|
| User_Lifecycle | 189 |
| Authentication | 128 |
| Chaos_Engineering | 109 |
| Mail_Service | 95 |
| Bug_Hunting | 79 |
| Administration | 55 |
| Challenges | 39 |
| Webhooks | 39 |
| File_Storage | 38 |
| System | 28 |
| **Total** | **799** |

---

## 📚 Documentation

Full documentation lives in the [project wiki](https://github.com/romasky/play-api-python/wiki):
[Getting Started](https://github.com/romasky/play-api-python/wiki/Getting-Started) ·
[Architecture](https://github.com/romasky/play-api-python/wiki/Architecture) ·
[Step Definitions Reference](https://github.com/romasky/play-api-python/wiki/Step-Definitions-Reference) ·
[Models Reference](https://github.com/romasky/play-api-python/wiki/Models-Reference) ·
[Authorization Header Testing](https://github.com/romasky/play-api-python/wiki/Authorization-Header-Testing) ·
[Feature Files & Coverage](https://github.com/romasky/play-api-python/wiki/Feature-Files-and-Coverage) ·
[Allure Reporting](https://github.com/romasky/play-api-python/wiki/Allure-Reporting) ·
[CI/CD](https://github.com/romasky/play-api-python/wiki/CI-CD).
The live-verified API behaviour is in [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## 🔗 Related

- [play-qa.com](https://www.play-qa.com) — The API under test
- [Swagger UI](https://play-qa.com/swagger/index.html) — Interactive API docs
