"""User / login / logout steps — port of src/steps/accountsSteps.js.

The three Authorization variants are the heart of the negative coverage (see CLAUDE.md):
  auth.bearer(ctx, key) → "Bearer <token>"   wrong/revoked token → INVALID_TOKEN
  auth.raw(value)       → verbatim value     malformed           → INVALID_TOKEN_FORMAT
  auth.none()           → no header          missing             → MISSING_TOKEN

Rate-limit pacing lives in tests/conftest.py (`_rate_limit_pacing`), not here.
"""

from __future__ import annotations

from typing import Any

from pytest_bdd import given, parsers, then, when

from play_api.api import client, paths
from play_api.context import ScenarioContext
from play_api.models.requests import (
    AddressReq,
    ContactsReq,
    CreateUserReq,
    EmploymentReq,
    LoginReq,
    ProfileReq,
    SettingsReq,
)
from play_api.models.responses import (
    UsersListResponse,
    assert_error_code,
    assert_list_items_have_no_field,
    assert_login_successful,
    assert_user_core_fields,
)
from play_api.utils import generator as gen
from play_api.utils.gherkin import raw_json


class auth:
    @staticmethod
    def bearer(ctx, token_key: str) -> dict[str, str]:
        return {"Authorization": client.bearer_header(ctx.str(token_key))}

    @staticmethod
    def raw(value: str) -> dict[str, str]:
        return {"Authorization": value}

    @staticmethod
    def none() -> dict[str, str]:
        return {}


# ─── Request-body builders ─────────────────────────────────────────────────


def _minimal_profile() -> ProfileReq:
    return ProfileReq(first_name=gen.first_name(), last_name=gen.last_name())


def _random_update_body() -> dict[str, Any]:
    """Valid random body for scenarios that test auth, not payload validation."""
    return CreateUserReq(email=gen.email(), username=gen.username(), profile=_minimal_profile()).to_body()


def _random_patch_body() -> dict[str, Any]:
    return {"username": gen.username()}


def _context_profile(ctx) -> ProfileReq:
    return ProfileReq(first_name=ctx.str("firstName"), last_name=ctx.str("lastName"))


def _context_update_body(ctx: ScenarioContext) -> dict[str, Any]:
    """Body assembled from context variables set by earlier Given steps."""
    return CreateUserReq(email=ctx.str("email"), username=ctx.str("username"), profile=_context_profile(ctx)).to_body()


def _opt_model(ctx, key: str, model):
    value = ctx.opt(key)
    return model(**value) if value else None


# ─── Create user ───────────────────────────────────────────────────────────


@given(parsers.parse('Create minimal user and save response as "{var}"'))
def create_minimal_user(ctx, var):
    email, password = gen.email(), gen.password()
    body = CreateUserReq(email=email, username=gen.username(), password=password, profile=_minimal_profile())
    ctx.save(var, client.post(paths.USERS_CREATE, body.to_body()))
    ctx.save("generatedEmail", email)
    ctx.save("generatedPassword", password)


@when(parsers.parse('Create user with body and save response as "{var}"'))
def create_user_with_body(ctx, var):
    body = CreateUserReq(
        email=ctx.str("email"),
        username=ctx.str("username"),
        password=ctx.str("password"),
        profile=_context_profile(ctx),
    )
    ctx.save(var, client.post(paths.USERS_CREATE, body.to_body()))


@when(parsers.parse('Create user with full body and save response as "{var}"'))
def create_user_with_full_body(ctx, var):
    body = CreateUserReq(
        email=ctx.str("email"),
        username=ctx.str("username"),
        password=ctx.str("password"),
        profile=ProfileReq(
            first_name=ctx.str("firstName"),
            last_name=ctx.str("lastName"),
            gender=ctx.opt("gender"),
            bio=ctx.opt("profileBio"),
            date_of_birth=ctx.opt("dateOfBirth"),
            interests=ctx.opt("interests"),
            avatar_url=ctx.opt("avatarUrl"),
        ),
        contacts=_opt_model(ctx, "contacts", ContactsReq),
        address=_opt_model(ctx, "address", AddressReq),
        employment=_opt_model(ctx, "employment", EmploymentReq),
        settings=_opt_model(ctx, "settings", SettingsReq),
    )
    ctx.save(var, client.post(paths.USERS_CREATE, body.to_body()))


@when(parsers.parse('Create user with all optional fields and save response as "{var}"'))
def create_user_all_optional(ctx, var):
    body = CreateUserReq(
        email=gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=ProfileReq(
            first_name=gen.first_name(),
            last_name=gen.last_name(),
            middle_name="Michael",
            gender="other",
            bio="Short bio here.",
            date_of_birth="1990-01-15",
            interests=["coding", "travel"],
            avatar_url="https://example.com/avatar.jpg",
        ),
        contacts=ContactsReq(
            phone=gen.phone_number(),
            telegram="@tester",
            whatsapp=gen.phone_number(),
            linkedin="https://linkedin.com/in/tester",
            github="https://github.com/tester",
            website="https://tester.dev",
        ),
        address=AddressReq(
            country="US",
            state="California",
            city="San Francisco",
            street="Market St",
            building="100",
            apartment="5A",
            zip_code="94105",
            coordinates={"latitude": 37.7749, "longitude": -122.4194},
        ),
        employment=EmploymentReq(
            status="employed",
            company="Acme Inc",
            position="Engineer",
            department="R&D",
            start_date="2020-03-01",
            salary={"amount": 120000, "currency": "USD"},
        ),
        settings=SettingsReq(
            language="en",
            timezone="America/Los_Angeles",
            theme="dark",
            notifications_enabled=True,
            two_factor_enabled=False,
            private_profile=False,
        ),
    )
    ctx.save(var, client.post(paths.USERS_CREATE, body.to_body()))


@when(parsers.parse('Create user with raw body "{raw}" and save response as "{var}"'))
def create_user_raw(ctx, raw, var):
    ctx.save(var, client.post(paths.USERS_CREATE, raw_json(raw)))


# Optional-field inputs consumed by "Create user with full body"


@given(parsers.parse('Set employment status "{status}"'))
def set_employment_status(ctx, status):
    ctx.save("employment", {"status": status})


@given(parsers.parse('Set theme "{theme}"'))
def set_theme(ctx, theme):
    ctx.save("settings", {"theme": theme})


# `parsers.re` because the feature also uses `Set interests ""` (parse's {} needs ≥1 char)
@given(parsers.re(r'Set interests "(?P<csv>.*)"'))
def set_interests(ctx, csv):
    ctx.save("interests", csv.split(",") if csv else [])


# saved as 'profileBio' so the literal "bio" stays usable in assertions (ctx.str resolves context keys first)
@given(parsers.parse("Set bio of length {n:d}"))
def set_bio_of_length(ctx, n):
    ctx.save("profileBio", gen.text(n, spaces=True))


@given(parsers.parse('Generate username of length {n:d} and save as "{key}"'))
def generate_username_of_length(ctx, n, key):
    ctx.save(key, gen.alphanumeric(n))


# ─── Get user ──────────────────────────────────────────────────────────────


@when(parsers.parse('Send GET user request for "{id_key}" and save response as "{var}"'))
def get_user(ctx, id_key, var):
    ctx.save(var, client.get(paths.users_get(ctx.str(id_key))))


# ─── List users ────────────────────────────────────────────────────────────


@when(parsers.parse('Send GET users list request and save response as "{var}"'))
def list_users(ctx, var):
    ctx.save(var, client.get(paths.USERS_LIST))


# String-typed so boundary rows can pass non-numeric values (abc, -5, xyz)
@when(
    parsers.parse('Send GET users list request with page "{page}" per_page "{per_page}" and save response as "{var}"')
)
def list_users_paged(ctx, page, per_page, var):
    ctx.save(var, client.get(paths.USERS_LIST, params={"page": page, "per_page": per_page}))


@then(parsers.parse('Assert users list is not empty in "{var}"'))
def assert_users_list_not_empty(ctx, var):
    assert UsersListResponse.check(ctx.body(var)).users, "Expected non-empty users list"


@then(parsers.parse('Assert users list items have no "{field}" field in "{var}"'))
def assert_users_list_no_field(ctx, field, var):
    assert_list_items_have_no_field(ctx.body(var), field)


# ─── User exists ───────────────────────────────────────────────────────────


@when(parsers.parse('Send HEAD exists request for "{id_key}" and save response as "{var}"'))
def head_exists(ctx, id_key, var):
    ctx.save(var, client.head(paths.users_exists(ctx.str(id_key))))


@when(parsers.parse('Send GET exists request for "{id_key}" and save response as "{var}"'))
def get_exists(ctx, id_key, var):
    ctx.save(var, client.get(paths.users_exists(ctx.str(id_key))))


# ─── Update user (PUT) ─────────────────────────────────────────────────────


def _update(ctx, id_key, body, headers, var):
    ctx.save(var, client.put(paths.users_update(ctx.str(id_key)), body, headers))


@when(parsers.parse('Update user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def update_user_token(ctx, id_key, token_key, var):
    _update(ctx, id_key, _context_update_body(ctx), auth.bearer(ctx, token_key), var)


@when(parsers.parse('Update user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"'))
def update_user_raw_body(ctx, id_key, raw, token_key, var):
    _update(ctx, id_key, raw_json(raw), auth.bearer(ctx, token_key), var)


@when(parsers.parse('Update user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def update_user_raw_auth(ctx, id_key, header, var):
    _update(ctx, id_key, _random_update_body(), auth.raw(header), var)


@when(parsers.parse('Update user "{id_key}" with no auth token and save response as "{var}"'))
def update_user_no_auth(ctx, id_key, var):
    _update(ctx, id_key, _random_update_body(), auth.none(), var)


# ─── Patch user (PATCH) ────────────────────────────────────────────────────


def _patch(ctx, id_key, body, headers, var):
    ctx.save(var, client.patch(paths.users_patch(ctx.str(id_key)), body, headers))


@when(
    parsers.parse(
        'Patch user "{id_key}" with field "{field}" value "{value}" token "{token_key}" and save response as "{var}"'
    )
)
def patch_user_field(ctx, id_key, field, value, token_key, var):
    _patch(ctx, id_key, {field: ctx.str(value)}, auth.bearer(ctx, token_key), var)


@when(parsers.parse('Patch user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"'))
def patch_user_raw_body(ctx, id_key, raw, token_key, var):
    _patch(ctx, id_key, raw_json(raw), auth.bearer(ctx, token_key), var)


@when(parsers.parse('Patch user "{id_key}" with empty body token "{token_key}" and save response as "{var}"'))
def patch_user_empty_body(ctx, id_key, token_key, var):
    _patch(ctx, id_key, {}, auth.bearer(ctx, token_key), var)


@when(parsers.parse('Patch user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def patch_user_raw_auth(ctx, id_key, header, var):
    _patch(ctx, id_key, _random_patch_body(), auth.raw(header), var)


@when(parsers.parse('Patch user "{id_key}" with no auth token and save response as "{var}"'))
def patch_user_no_auth(ctx, id_key, var):
    _patch(ctx, id_key, _random_patch_body(), auth.none(), var)


# ─── Delete user ───────────────────────────────────────────────────────────


def _delete(ctx, id_key, headers, var):
    ctx.save(var, client.delete(paths.users_delete(ctx.str(id_key)), headers))


@when(parsers.parse('Delete user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def delete_user_token(ctx, id_key, token_key, var):
    _delete(ctx, id_key, auth.bearer(ctx, token_key), var)


@when(parsers.parse('Delete user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def delete_user_raw_auth(ctx, id_key, header, var):
    _delete(ctx, id_key, auth.raw(header), var)


@when(parsers.parse('Delete user "{id_key}" with no auth token and save response as "{var}"'))
def delete_user_no_auth(ctx, id_key, var):
    _delete(ctx, id_key, auth.none(), var)


# ─── Login ─────────────────────────────────────────────────────────────────


@when(parsers.parse('Login with "{email_key}" and "{password_key}" and save response as "{var}"'))
def login(ctx, email_key, password_key, var):
    body = LoginReq(email=ctx.str(email_key), password=ctx.str(password_key))
    ctx.save(var, client.post(paths.LOGIN, body.to_body()))


@when(parsers.parse('Login with raw body "{raw}" and save response as "{var}"'))
def login_raw(ctx, raw, var):
    ctx.save(var, client.post(paths.LOGIN, raw_json(raw)))


# ─── Logout (POST without body) ────────────────────────────────────────────


def _logout(ctx, id_key, headers, var):
    ctx.save(var, client.post(paths.users_logout(ctx.str(id_key)), None, headers))


@when(parsers.parse('Logout user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def logout_token(ctx, id_key, token_key, var):
    _logout(ctx, id_key, auth.bearer(ctx, token_key), var)


@when(parsers.parse('Logout user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def logout_raw_auth(ctx, id_key, header, var):
    _logout(ctx, id_key, auth.raw(header), var)


@when(parsers.parse('Logout user "{id_key}" with no auth token and save response as "{var}"'))
def logout_no_auth(ctx, id_key, var):
    _logout(ctx, id_key, auth.none(), var)


# ─── Typed response assertions ─────────────────────────────────────────────


@then(parsers.parse('Assert error code is "{code}" in response "{var}"'))
def assert_error_code_step(ctx, code, var):
    assert_error_code(ctx.body(var), code)


@then(parsers.parse('Assert user response has all core fields in "{var}"'))
def assert_user_core_fields_step(ctx, var):
    assert_user_core_fields(ctx.body(var))


@then(parsers.parse('Assert login response is successful in "{var}"'))
def assert_login_successful_step(ctx, var):
    assert_login_successful(ctx.body(var))
