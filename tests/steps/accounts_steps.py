"""User / login / logout steps — port of src/steps/accountsSteps.js, on top of `play_api.services`.

Steps resolve context keys and pick bodies (`models.factories`); the services own paths and HTTP.
Authorization variants: `bearer(ctx, key)` / `raw_header(ctx, value)` / `auth.none()` (see `api/auth.py`).
Rate-limit pacing lives in `play_api.pacing`, not here.
"""

from __future__ import annotations

from pytest_bdd import given, parsers, step, then, when

from play_api.api import auth
from play_api.assertions import assert_every_item, assert_total_pages
from play_api.models import factories
from play_api.models.requests import CreateUserReq, LoginReq
from play_api.models.responses.users import UsersListResponse
from play_api.services import login, users
from play_api.utils import generator as gen
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.support import bearer, quoted, raw_header

# ─── Create user / admin ───────────────────────────────────────────────────


def _create_and_remember(ctx, body: CreateUserReq, create, var: str) -> None:
    """POST the body; remember its credentials as generatedEmail / generatedPassword for later Login steps."""
    ctx.save(var, create(body))
    ctx.save("generatedEmail", body.email)
    ctx.save("generatedPassword", body.password)


def _created(ctx, body: CreateUserReq, create, token_key: str, id_key: str | None = None) -> None:
    """Composite setup: create, assert 201, keep only the token (and id) — the response itself is not needed."""
    _create_and_remember(ctx, body, create, "_setup")
    response = ctx.response("_setup")
    assert response.status_code == 201, f"setup create failed {response.status_code}: {response.text}"
    ctx.save(token_key, response.json()["access_token"])
    if id_key:
        ctx.save(id_key, response.json()["id"])


@given(parsers.parse('Create minimal user and save response as "{var}"'))
def create_minimal_user(ctx, var):
    _create_and_remember(ctx, factories.minimal_user(), users.create, var)


@step(quoted('a user with token "{token_key}"'))
def a_user(ctx, token_key):
    _created(ctx, factories.minimal_user(), users.create, token_key)


@step(quoted('a user with id "{id_key}" and token "{token_key}"'))
def a_user_with_id(ctx, id_key, token_key):
    _created(ctx, factories.minimal_user(), users.create, token_key, id_key)


@step(quoted('an admin with token "{token_key}"'))
def an_admin(ctx, token_key):
    _created(ctx, factories.admin(), users.create_admin, token_key)


@step(quoted('an admin with id "{id_key}" and token "{token_key}"'))
def an_admin_with_id(ctx, id_key, token_key):
    _created(ctx, factories.admin(), users.create_admin, token_key, id_key)


@step(parsers.parse('Create user in country "{country_key}" and save response as "{var}"'))
def create_user_in_country(ctx, country_key, var):
    _create_and_remember(ctx, factories.minimal_user(country=ctx.str(country_key)), users.create, var)


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


# "with body" and "with full body" read the same context keys; unset optional parts are simply absent
@when(parsers.parse('Create user with body and save response as "{var}"'))
def create_user_with_body(ctx, var):
    ctx.save(var, users.create(factories.user_from_context(ctx)))


@when(parsers.parse('Create user with full body and save response as "{var}"'))
def create_user_with_full_body(ctx, var):
    ctx.save(var, users.create(factories.user_from_context(ctx)))


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
    ctx.save("profileBio", gen.text(n))


@given(parsers.parse('Generate username of length {n:d} and save as "{key}"'))
def generate_username_of_length(ctx, n, key):
    ctx.save(key, gen.alphanumeric(n))


# ─── Get user (public read; a PRESENT Authorization header must be valid — Feature 17) ───


@when(quoted('Send GET user request for "{id_key}" and save response as "{var}"'))
def get_user(ctx, id_key, var):
    ctx.save(var, users.get(ctx.str(id_key)))


@when(quoted('Send GET user request for "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def get_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.get(ctx.str(id_key), raw_header(ctx, header)))


@when(quoted('Send GET user request for "{id_key}" with token "{token_key}" and save response as "{var}"'))
def get_user_token(ctx, id_key, token_key, var):
    ctx.save(var, users.get(ctx.str(id_key), bearer(ctx, token_key)))


# ─── List users ────────────────────────────────────────────────────────────


@when(parsers.parse('Send GET users list request and save response as "{var}"'))
def list_users(ctx, var):
    ctx.save(var, users.list_users())


# String-typed so boundary rows can pass non-numeric values (abc, -5, xyz)
@when(
    parsers.parse('Send GET users list request with page "{page}" per_page "{per_page}" and save response as "{var}"')
)
def list_users_paged(ctx, page, per_page, var):
    ctx.save(var, users.list_users({"page": page, "per_page": per_page}))


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
    ctx.save(var, users.list_users(query_pairs(ctx.render(query)), raw_header(ctx, header)))


@when(quoted('Send GET users list request with query "{query}" and token "{token_key}" and save response as "{var}"'))
def list_users_query_token(ctx, query, token_key, var):
    ctx.save(var, users.list_users(query_pairs(ctx.render(query)), bearer(ctx, token_key)))


@then(parsers.parse('Assert users list total_pages matches total and per_page in "{var}"'))
def assert_users_list_total_pages(ctx, var):
    assert_total_pages(ctx.body(var))


@then(parsers.parse('Assert users list is not empty in "{var}"'))
def assert_users_list_not_empty(ctx, var):
    assert UsersListResponse.check(ctx.body(var)).users, "Expected non-empty users list"


@then(parsers.parse('Assert users list items have no "{field}" field in "{var}"'))
def assert_users_list_no_field(ctx, field, var):
    assert_every_item(ctx.body(var), "users", field, present=False)


# ─── User exists ───────────────────────────────────────────────────────────


@when(parsers.parse('Send HEAD exists request for "{id_key}" and save response as "{var}"'))
def head_exists(ctx, id_key, var):
    ctx.save(var, users.exists(ctx.str(id_key), "HEAD"))


@when(parsers.parse('Send GET exists request for "{id_key}" and save response as "{var}"'))
def get_exists(ctx, id_key, var):
    ctx.save(var, users.exists(ctx.str(id_key), "GET"))


# ─── Update user (PUT) — the token variant sends the context body, the auth variants a random valid one ───


@when(parsers.parse('Update user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def update_user_token(ctx, id_key, token_key, var):
    body = factories.user_from_context(ctx, with_password=False)
    ctx.save(var, users.update(ctx.str(id_key), body, bearer(ctx, token_key)))


@when(parsers.parse('Update user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"'))
def update_user_raw_body(ctx, id_key, raw, token_key, var):
    ctx.save(var, users.update(ctx.str(id_key), raw_json(ctx.render(raw)), bearer(ctx, token_key)))


@when(parsers.parse('Update user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def update_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.update(ctx.str(id_key), factories.random_update(), raw_header(ctx, header)))


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
    ctx.save(var, users.patch(ctx.str(id_key), {field: ctx.str(value)}, bearer(ctx, token_key)))


@when(parsers.parse('Patch user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"'))
def patch_user_raw_body(ctx, id_key, raw, token_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), raw_json(ctx.render(raw)), bearer(ctx, token_key)))


@when(parsers.parse('Patch user "{id_key}" with empty body token "{token_key}" and save response as "{var}"'))
def patch_user_empty_body(ctx, id_key, token_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), {}, bearer(ctx, token_key)))


@when(parsers.parse('Patch user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def patch_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.patch(ctx.str(id_key), factories.random_patch(), raw_header(ctx, header)))


@when(parsers.parse('Patch user "{id_key}" with no auth token and save response as "{var}"'))
def patch_user_no_auth(ctx, id_key, var):
    ctx.save(var, users.patch(ctx.str(id_key), factories.random_patch(), auth.none()))


# ─── Delete user ───────────────────────────────────────────────────────────


@when(parsers.parse('Delete user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def delete_user_token(ctx, id_key, token_key, var):
    ctx.save(var, users.delete(ctx.str(id_key), bearer(ctx, token_key)))


@when(parsers.parse('Delete user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def delete_user_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.delete(ctx.str(id_key), raw_header(ctx, header)))


@when(parsers.parse('Delete user "{id_key}" with no auth token and save response as "{var}"'))
def delete_user_no_auth(ctx, id_key, var):
    ctx.save(var, users.delete(ctx.str(id_key), auth.none()))


# ─── Login ─────────────────────────────────────────────────────────────────


@when(parsers.parse('Login with "{email_key}" and "{password_key}" and save response as "{var}"'))
def login_with(ctx, email_key, password_key, var):
    ctx.save(var, login.login(LoginReq(email=ctx.str(email_key), password=ctx.str(password_key))))


@when(parsers.parse('Login with raw body "{raw}" and save response as "{var}"'))
def login_raw(ctx, raw, var):
    ctx.save(var, login.login(raw_json(ctx.render(raw))))


# ─── Logout (POST without body) ────────────────────────────────────────────


@when(parsers.parse('Logout user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def logout_token(ctx, id_key, token_key, var):
    ctx.save(var, users.logout(ctx.str(id_key), bearer(ctx, token_key)))


@when(parsers.parse('Logout user "{id_key}" with raw auth header "{header}" and save response as "{var}"'))
def logout_raw_auth(ctx, id_key, header, var):
    ctx.save(var, users.logout(ctx.str(id_key), raw_header(ctx, header)))


@when(parsers.parse('Logout user "{id_key}" with no auth token and save response as "{var}"'))
def logout_no_auth(ctx, id_key, var):
    ctx.save(var, users.logout(ctx.str(id_key), auth.none()))
