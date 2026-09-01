# play-api-python — API Test Automation Framework

[![API Tests — play-qa.com](https://github.com/romasky/play-api-python/workflows/API%20Tests%20%E2%80%94%20play-qa.com/badge.svg)](https://github.com/romasky/play-api-python/actions)
[![Allure Report](https://img.shields.io/badge/Allure-Report-brightgreen)](https://romasky.github.io/play-api-python/latest/)

**play-api-python** is a BDD API test automation framework for [play-qa.com](https://www.play-qa.com), built with
Python 3.12, pytest + pytest-bdd, pydantic 2, httpx and Allure Report 3. It is the Python port of
[play-api-js](https://github.com/romasky/play-api-js) (itself a port of
[play-api-java](https://github.com/romasky/play-api-java)) and runs the **same 18 feature files** unchanged.

---

## 📊 Allure Report

🔗 **[View Latest Report](https://romasky.github.io/play-api-python/latest/)**

---

## ✨ Key Highlights

- **BDD scenarios** — Gherkin feature files (identical to the JS/Java projects) covering positive, negative and end-to-end flows
- **181 scenarios across 18 feature files** — covering 19 API endpoints, including Bearer and Basic auth
- **Allure 3 HTML reports** — Epic → Suite → SubSuite → Story hierarchy, every HTTP call a nested step with request/response attachments, auto-published to GitHub Pages on every CI run
- **Token-security regression guards** — absent / empty / malformed `Authorization` headers and cross-account (IDOR) attempts; every negative scenario asserts **both** the HTTP status and `error.code`
- **Typed contracts** — pydantic response models (`ErrorEnvelope`, `UserResponse`, `LoginResponse`, …) plus dotted-path own-property checks (`Assert field "x.y" is absent …`) — never substring matching
- **Typed request builders** — pydantic models with `exclude_none` serialization, so unset optional fields are absent (never `null`)
- **Temp-mail API coverage** — mailbox and message endpoints exercised through the same Gherkin steps, no external mail service needed
- **Rate-limit pacing** — an autouse fixture sleeps pre-emptively per suite/sub-suite to respect server-enforced limits (paced, never retried)
- **Scenario context** — global (`_g`) / local scoping for cross-scenario data dependencies
- **Offline step check** — `tools/check_steps.py` matches all 1 082 Gherkin steps against the step definitions without touching the API

---

## 🛠 Tech Stack

| Tool | Version | Role |
|---|---|---|
| Python | 3.12 | Runtime (`.python-version`) |
| [uv](https://docs.astral.sh/uv/) | 0.12+ | Packaging: venv, lockfile, runner |
| `pytest` | ≥ 8.3 | Test runner |
| `pytest-bdd` | 8.1 | Gherkin parser (`gherkin-official`) + step binding |
| `httpx2` | 2.12 | HTTP client (drop-in `httpx` fork maintained by Pydantic Services) |
| `pydantic` | 2.x | Request builders and typed response contracts |
| `pydantic-settings` | 2.x | `.env` + environment configuration |
| `allure-pytest-bdd` | 2.16 | Allure results adapter |
| Allure 3 CLI (`npx allure@3`) | 3.x | Report generation (Awesome UI) — the only Node dependency |

---

## 📁 Project Structure

```
play-api-python/
├── pyproject.toml                 # deps (uv), pytest config: markers, default -m filter, --alluredir
├── uv.lock                        # locked dependency set (CI uses --frozen)
├── .env.example                   # BASE_URL / REQUEST_TIMEOUT (copy to .env, git-ignored)
├── .github/workflows/test.yml     # CI — uv + pytest → Allure 3 → GitHub Pages
├── allure-results/
│   └── categories.json            # Allure failure categories
├── docs/API_REFERENCE.md          # API contract — ground truth for expectations
├── tools/check_steps.py           # offline: every feature step ↔ exactly one step definition
├── src/play_api/
│   ├── config.py                  # Settings (pydantic-settings)
│   ├── context.py                 # ScenarioContext — save/get/opt/str/response/body, _g/_l scoping
│   ├── api/
│   │   ├── paths.py               # All endpoint paths as constants / functions
│   │   └── client.py              # httpx wrapper — one Allure step per request, headers passed verbatim
│   ├── models/
│   │   ├── requests.py            # CreateUserReq / ProfileReq / … / LoginReq / CreateMailboxReq / SendMessageReq
│   │   └── responses.py           # pydantic contracts + assert_* helpers used by steps
│   └── utils/
│       ├── generator.py           # Random data generators (email, username, …)
│       ├── json_path.py           # get_path / has_path — typed dotted-path body checks
│       └── gherkin.py             # raw_json — unescapes `… with raw body "{…}"` step arguments
├── tests/
│   ├── conftest.py                # step-module plugins, ctx fixtures, @allure.label.* tag hook, rate-limit pacing
│   ├── test_features.py           # scenarios("play_qa_api") — binds every feature file
│   └── steps/
│       ├── common_steps.py        # Data generation, Extract, typed field/header/status assertions, debug
│       ├── accounts_steps.py      # Users, login, logout (bearer / raw / no-auth variants)
│       ├── mail_steps.py          # Mailbox and message steps
│       ├── health_steps.py        # GET /health
│       ├── basic_auth_steps.py    # GET /auth/basic
│       └── options_steps.py       # OPTIONS /users/options
└── features/play_qa_api/          # 18 feature files — copied verbatim from play-api-js
    ├── CreateUserTests.feature
    ├── GetUserTests.feature
    ├── ListUsersTests.feature
    ├── UserExistsTests.feature
    ├── UpdateUserTests.feature
    ├── PatchUserTests.feature
    ├── DeleteUserTests.feature
    ├── LoginTests.feature
    ├── LogoutTests.feature
    ├── TokenSecurityTests.feature
    ├── BasicAuthTests.feature
    ├── OptionsTests.feature
    ├── HealthTests.feature
    ├── MailboxCreateTests.feature
    ├── MailboxGetTests.feature
    ├── MailboxDeleteTests.feature
    ├── MailSendTests.feature
    └── MailMessagesTests.feature
```

---

## 🚀 Quick Start

```bash
# Install uv (once), Python 3.12 and all dependencies
brew install uv            # or: curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv sync

# Verify every Gherkin step has exactly one step definition (no network needed)
uv run python tools/check_steps.py

# Run all tests (default filter: @Run and not @Ignore/@Bug/@NotImplemented)
uv run pytest

# Smoke tests only
uv run pytest -m Smoke

# Combine markers / pick scenarios by name substring (feature-file paths are not selectable)
uv run pytest -m "Positive and Run"
uv run pytest -k empty_bearer

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
```

`REQUEST_TIMEOUT` is the single httpx deadline (connect + read) in **seconds** — the JS port used milliseconds.
Environment variables override `.env`: `BASE_URL=https://staging.play-qa.com uv run pytest`.

---

## 🗂 API Coverage

| Method | Endpoint | Feature File | Status |
|---|---|---|---|
| GET | `/api/v1/health` | HealthTests.feature | ✅ Tested |
| POST | `/api/v1/login` | LoginTests.feature | ✅ Tested |
| GET | `/api/v1/auth/basic` | BasicAuthTests.feature | ✅ Tested |
| POST | `/api/v1/users/create` | CreateUserTests.feature | ✅ Tested |
| GET | `/api/v1/users/list` | ListUsersTests.feature | ✅ Tested |
| GET | `/api/v1/users/get/:id` | GetUserTests.feature | ✅ Tested |
| HEAD | `/api/v1/users/exists/:id` | UserExistsTests.feature | ✅ Tested |
| GET | `/api/v1/users/exists/:id` | UserExistsTests.feature | ✅ Tested |
| OPTIONS | `/api/v1/users/options` | OptionsTests.feature | ✅ Tested |
| PUT | `/api/v1/users/update/:id` | UpdateUserTests.feature | ✅ Tested |
| PATCH | `/api/v1/users/patch/:id` | PatchUserTests.feature | ✅ Tested |
| DELETE | `/api/v1/users/delete/:id` | DeleteUserTests.feature | ✅ Tested |
| POST | `/api/v1/users/logout/:id` | LogoutTests.feature | ✅ Tested |
| PUT/PATCH/DELETE/POST | user mutation endpoints — auth hardening | TokenSecurityTests.feature | ✅ Tested |
| POST | `/api/v1/mail/create` | MailboxCreateTests.feature | ✅ Tested |
| GET | `/api/v1/mail/:token` | MailboxGetTests.feature | ✅ Tested |
| DELETE | `/api/v1/mail/:token` | MailboxDeleteTests.feature | ✅ Tested |
| GET | `/api/v1/mail/:token/messages` | MailMessagesTests.feature | ✅ Tested |
| GET | `/api/v1/mail/:token/messages/:id` | MailMessagesTests.feature | ✅ Tested |
| POST | `/api/v1/mail/:token/send` | MailSendTests.feature | ✅ Tested |
| POST | `/api/v1/verify-recaptcha` | — | ⏭ Out of scope (needs a live Google reCAPTCHA token) |

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
| `@allure.label.{epic,suite,subSuite,story,severity}:X` | Allure report hierarchy / severity |

---

## 📈 Scenario Count

Scenario Outlines are counted per example row.

| Feature | Scenarios |
|---|---|
| CreateUserTests | 39 |
| MailboxCreateTests | 18 |
| ListUsersTests | 13 |
| LoginTests | 13 |
| TokenSecurityTests | 12 |
| PatchUserTests | 10 |
| DeleteUserTests | 8 |
| LogoutTests | 8 |
| MailMessagesTests | 8 |
| MailboxDeleteTests | 8 |
| UpdateUserTests | 8 |
| GetUserTests | 7 |
| MailSendTests | 7 |
| UserExistsTests | 7 |
| BasicAuthTests | 6 |
| HealthTests | 4 |
| MailboxGetTests | 3 |
| OptionsTests | 2 |
| **Total** | **181** |

---

## 🔁 Porting notes (JS → Python)

| play-api-js | play-api-python |
|---|---|
| Cucumber `{string}` / `{int}` | `parsers.parse('… "{name}" …')` / `{name:d}` |
| Any keyword matches any step | pytest-bdd matches by keyword — steps used after Given **and** When/Then use `@step` |
| `{string}` unescapes `\"` | `utils.gherkin.raw_json()` unescapes before `json.loads` |
| `createUserReq({...})` strips `undefined` | `CreateUserReq(...).to_body()` → `model_dump(exclude_none=True)` |
| `Before({tags})` sleeps | `_rate_limit_pacing` autouse fixture reads `allure_label` markers |
| `@allure.label.*` handled by allure-cucumberjs | `pytest_bdd_apply_tag` hook → `pytest.mark.allure_label` |

---

## 🔗 Related

- [play-api-js](https://github.com/romasky/play-api-js) — JavaScript version (reference implementation) · [wiki](https://github.com/romasky/play-api-js/wiki)
- [play-api-java](https://github.com/romasky/play-api-java) — Java version
- [play-qa.com](https://www.play-qa.com) — The API under test
- [Swagger UI](https://play-qa.com/swagger/index.html) — Interactive API docs
