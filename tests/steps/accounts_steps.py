"""User / login / logout steps — port of src/steps/accountsSteps.js, on top of `play_api.services`.

Steps resolve context keys and build bodies; the services own paths and HTTP. Authorization
variants come from `play_api.api.auth` (bearer / raw / none — see its docstring).
Rate-limit pacing lives in `play_api.pacing`, not here.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, step, then, when

from play_api.api import auth
from play_api.assertions import assert_total_pages
from play_api.context import ScenarioContext
from play_api.models import factories
from play_api.models.requests import (
    AddressReq,
    ContactsReq,
    CreateUserReq,
    EmploymentReq,
    LoginReq,
    ProfileReq,
    SettingsReq,
)
from play_api.models.responses.base import assert_error_code
from play_api.models.responses.users import (
    UserResponse,
    UsersListResponse,
    assert_list_items_have_no_field,
    assert_login_successful,
)
from play_api.services import session, users
from play_api.utils import generator as gen
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.parsing import quoted

# ─── Request-body builders ─────────────────────────────────────────────────


def _context_profile(ctx: ScenarioContext) -> ProfileReq:
    return ProfileReq(first_name=ctx.str("firstName"), last_name=ctx.str("lastName"))


def _context_update_body(ctx: ScenarioContext) -> CreateUserReq:
    """Body assembled from context variables set by earlier Given steps."""
    return CreateUserReq(email=ctx.str("email"), username=ctx.str("username"), profile=_context_profile(ctx))


def _opt_model(ctx, key: str, model):
    value = ctx.opt(key)
    return model(**value) if value else None


# ─── Create user ───────────────────────────────────────────────────────────


def _create_and_remember(ctx, body, create, var):
    """POST the body; remember its credentials as generatedEmail / generatedPassword for later Login steps."""
    ctx.save(var, create(body))
    ctx.save("generatedEmail", body.email)
    ctx.save("generatedPassword", body.password)


@given(parsers.parse('Create minimal user and save response as "{var}"'))
def create_minimal_user(ctx, var):
    _create_and_remember(ctx, factories.minimal_user(), users.create, var)


@step(parsers.parse('Create user in country "{country_key}" and save response as "{var}"'))
def create_user_in_country(ctx, country_key, var):
    _create_and_remember(ctx, factories.minimal_user(country=ctx.str(country_key)), users.create, var)


# ─── Create admin (POST /users/create-admin) ───────────────────────────────


@step(parsers.parse('Create admin user and save response as "{var}"'))
def create_admin_user(ctx, var):
    _create_and_remember(ctx, factories.admin(), users.create_admin, var)


@when(quoted('Create admin with seed code "{seed}" and save response as "{var}"'))
def create_admin_with_seed(ctx, seed, var):
    ctx.save(var, users.create_admin(factories.admin(seed_code=ctx.str(seed))))


@when(parsers.parse('Create admin without seed code and save response as "{var}"'))
def create_admin_without_seed(ctx, var):
    ctx.save(var, users.create_admin(factories.admin(seed_code=None)))


@when(quoted('Create admin with email "{email_key}" and the published seed code and save response as "{var}"'))
def create_admin_with_email(ctx, email_key, var):
    ctx.save(var, users.create_admin(factories.admin(email=ctx.str(email_key))))


@when(quoted('Create admin with email "{email_key}" and seed code "{seed}" and save response as "{var}"'))
def create_admin_with_email_and_seed(ctx, email_key, seed, var):
    ctx.save(var, users.create_admin(factories.admin(seed_code=ctx.str(seed), email=ctx.str(email_key))))


@when(parsers.parse('Create admin with raw body "{raw}" and save response as "{var}"'))
def create_admin_raw(ctx, raw, var):
    ctx.save(var, users.create_admin(raw_json(ctx.render(raw))))


@when(parsers.parse('Create user with body and save response as "{var}"'))
def create_user_with_body(ctx, var):
    body = CreateUserReq(
        email=ctx.str("email"),
        username=ctx.str("username"),
        password=ctx.str("password"),
        profile=_context_profile(ctx),
    )
    ctx.save(var, users.create(body))


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
    ctx.save(var, users.create(body))


@when(parsers.parse('Create user with all optional fields and save response as "{var}"'))
def create_user_all_optional(ctx, var):
    ctx.save(var, users.create(factories.user_with_all_optional_fields()))


@when(parsers.parse('Create user with raw body "{raw}" and save response as "{var}"'))
def create_user_raw(ctx, raw, var):
    ctx.save(var, users.create(raw_json(ctx.render(raw))))


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


# Reads are public, but a PRESENT Authorization header must be valid (Feature 17). `quoted()` keeps the
# anonymous phrasing from also matching the "with raw auth header" / "with token" variants.
@when(quoted('Send GET user request for "{id_key}" and save response as "{var}"'))
def get_user(ctx, id_key, var):
    ctx.save(var, users.get(ctx.str(id_key)))


@when(quoted('Send GET user request for "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def get_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.get(ctx.str(id_key), auth.raw(ctx.render(header))))


@when(quoted('Send GET user request for "{id_key}" with token "{token_key}" and save response as "{var}"'))
def get_user_token(ctx, id_key, token_key, var):
    ctx.save(var, users.get(ctx.str(id_key), auth.bearer(ctx.str(token_key))))


# ─── List users ────────────────────────────────────────────────────────────


@when(parsers.parse('Send GET users list request and save response as "{var}"'))
def list_users(ctx, var):
    ctx.save(var, users.list_users())


# `query` is a raw query string with ${key} placeholders: repeated keys and present-but-empty values survive
@when(quoted('Send GET users list request with query "{query}" and save response as "{var}"'))
def list_users_query(ctx, query, var):
    ctx.save(var, users.list_users(query_pairs(ctx.render(query))))


@when(
    quoted(
        'Send GET users list request with query "{query}" and raw auth header "{header}" and save response as "{var}"'
    )
)
def list_users_query_raw_auth(ctx, query, header, var):
    ctx.save(var, users.list_users(query_pairs(ctx.render(query)), auth.raw(ctx.render(header))))


@when(quoted('Send GET users list request with query "{query}" and token "{token_key}" and save response as "{var}"'))
def list_users_query_token(ctx, query, token_key, var):
    ctx.save(var, users.list_users(query_pairs(ctx.render(query)), auth.bearer(ctx.str(token_key))))


@then(parsers.parse('Assert users list total_pages matches total and per_page in "{var}"'))
def assert_users_list_total_pages(ctx, var):
    assert_total_pages(ctx.body(var))


# String-typed so boundary rows can pass non-numeric values (abc, -5, xyz)
@when(
    parsers.parse('Send GET users list request with page "{page}" per_page "{per_page}" and save response as "{var}"')
)
def list_users_paged(ctx, page, per_page, var):
    ctx.save(var, users.list_users({"page": page, "per_page": per_page}))


@then(parsers.parse('Assert users list is not empty in "{var}"'))
def assert_users_list_not_empty(ctx, var):
    assert UsersListResponse.check(ctx.body(var)).users, "Expected non-empty users list"


@then(parsers.parse('Assert users list items have no "{field}" field in "{var}"'))
def assert_users_list_no_field(ctx, field, var):
    assert_list_items_have_no_field(ctx.body(var), field)


# ─── User exists ───────────────────────────────────────────────────────────


@when(parsers.parse('Send HEAD exists request for "{id_key}" and save response as "{var}"'))
def head_exists(ctx, id_key, var):
    ctx.save(var, users.exists(ctx.str(id_key), "HEAD"))


@when(parsers.parse('Send GET exists request for "{id_key}" and save response as "{var}"'))
def get_exists(ctx, id_key, var):
    ctx.save(var, users.exists(ctx.str(id_key), "GET"))


# ─── Update user (PUT) ─────────────────────────────────────────────────────


@when(parsers.parse('Update user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def update_user_token(ctx, id_key, token_key, var):
    ctx.save(var, users.update(ctx.str(id_key), _context_update_body(ctx), auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Update user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"'))
def update_user_raw_body(ctx, id_key, raw, token_key, var):
    ctx.save(var, users.update(ctx.str(id_key), raw_json(raw), auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Update user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def update_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.update(ctx.str(id_key), factories.random_update(), auth.raw(header)))


@when(parsers.parse('Update user "{id_key}" with no auth token and save response as "{var}"'))
def update_user_no_auth(ctx, id_key, var):
    ctx.save(var, users.update(ctx.str(id_key), factories.random_update(), auth.none()))


# ─── Patch user (PATCH) ────────────────────────────────────────────────────


@when(
    parsers.parse(
        'Patch user "{id_key}" with field "{field}" value "{value}" token "{token_key}" and save response as "{var}"'
    )
)
def patch_user_field(ctx, id_key, field, value, token_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), {field: ctx.str(value)}, auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Patch user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"'))
def patch_user_raw_body(ctx, id_key, raw, token_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), raw_json(raw), auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Patch user "{id_key}" with empty body token "{token_key}" and save response as "{var}"'))
def patch_user_empty_body(ctx, id_key, token_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), {}, auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Patch user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def patch_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.patch(ctx.str(id_key), factories.random_patch(), auth.raw(header)))


@when(parsers.parse('Patch user "{id_key}" with no auth token and save response as "{var}"'))
def patch_user_no_auth(ctx, id_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), factories.random_patch(), auth.none()))


# ─── Delete user ───────────────────────────────────────────────────────────


@when(parsers.parse('Delete user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def delete_user_token(ctx, id_key, token_key, var):
    ctx.save(var, users.delete(ctx.str(id_key), auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Delete user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def delete_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.delete(ctx.str(id_key), auth.raw(header)))


@when(parsers.parse('Delete user "{id_key}" with no auth token and save response as "{var}"'))
def delete_user_no_auth(ctx, id_key, var):
    ctx.save(var, users.delete(ctx.str(id_key), auth.none()))


# ─── Login ─────────────────────────────────────────────────────────────────


@when(parsers.parse('Login with "{email_key}" and "{password_key}" and save response as "{var}"'))
def login(ctx, email_key, password_key, var):
    ctx.save(var, session.login(LoginReq(email=ctx.str(email_key), password=ctx.str(password_key))))


@when(parsers.parse('Login with raw body "{raw}" and save response as "{var}"'))
def login_raw(ctx, raw, var):
    ctx.save(var, session.login(raw_json(raw)))


# ─── Logout (POST without body) ────────────────────────────────────────────


@when(parsers.parse('Logout user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def logout_token(ctx, id_key, token_key, var):
    ctx.save(var, users.logout(ctx.str(id_key), auth.bearer(ctx.str(token_key))))


@when(parsers.parse('Logout user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def logout_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.logout(ctx.str(id_key), auth.raw(header)))


@when(parsers.parse('Logout user "{id_key}" with no auth token and save response as "{var}"'))
def logout_no_auth(ctx, id_key, var):
    ctx.save(var, users.logout(ctx.str(id_key), auth.none()))


# ─── Typed response assertions ─────────────────────────────────────────────


@then(parsers.parse('Assert error code is "{code}" in response "{var}"'))
def assert_error_code_step(ctx, code, var):
    assert_error_code(ctx.body(var), code)


@then(parsers.parse('Assert user response has all core fields in "{var}"'))
def assert_user_core_fields_step(ctx, var):
    UserResponse.check(ctx.body(var))


@then(parsers.parse('Assert login response is successful in "{var}"'))
def assert_login_successful_step(ctx, var):
    assert_login_successful(ctx.body(var))
