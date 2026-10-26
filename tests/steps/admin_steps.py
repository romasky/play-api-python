"""/admin/* steps — stats, users list, role change, delete (on top of `play_api.services.admin`)."""

from __future__ import annotations

from collections.abc import Callable

import httpx2 as httpx
from pytest_bdd import parsers, then, when

from play_api.api import auth
from play_api.api.client import Headers
from play_api.models.requests import SetRoleReq
from play_api.models.responses.admin import assert_admin_stats_consistent
from play_api.services import admin
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.support import bearer, quoted, raw_header, route_call

# Auth-matrix outlines address the four routes by name. The target id is irrelevant there: the auth and
# role checks run before the scope check, so any id exercises them.
_ANY_ID = "000000000000000000000000"
_ROUTES: dict[str, Callable[[Headers], httpx.Response]] = {
    "stats": admin.stats,
    "users": admin.list_users,
    "set role": lambda headers: admin.set_role(_ANY_ID, SetRoleReq(role="user"), headers),
    "delete user": lambda headers: admin.delete_user(_ANY_ID, headers),
}


@when(quoted('Send admin "{route}" request with no auth token and save response as "{var}"'))
def admin_route_no_auth(ctx, route, var):
    ctx.save(var, route_call(_ROUTES, route)(auth.none()))


@when(quoted('Send admin "{route}" request with raw auth header "{header}" and save response as "{var}"'))
def admin_route_raw_auth(ctx, route, header, var):
    ctx.save(var, route_call(_ROUTES, route)(raw_header(ctx, header)))


@when(quoted('Send admin "{route}" request with token "{token_key}" and save response as "{var}"'))
def admin_route_token(ctx, route, token_key, var):
    ctx.save(var, route_call(_ROUTES, route)(bearer(ctx, token_key)))


# ─── Routes ────────────────────────────────────────────────────────────────


@when(parsers.parse('Get admin stats with token "{token_key}" and save response as "{var}"'))
def get_admin_stats(ctx, token_key, var):
    ctx.save(var, admin.stats(bearer(ctx, token_key)))


@when(quoted('Get admin users with query "{query}" and token "{token_key}" and save response as "{var}"'))
def get_admin_users(ctx, query, token_key, var):
    ctx.save(var, admin.list_users(bearer(ctx, token_key), query_pairs(ctx.render(query))))


@when(quoted('Set role "{role}" for user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def set_role(ctx, role, id_key, token_key, var):
    ctx.save(var, admin.set_role(ctx.str(id_key), SetRoleReq(role=role), bearer(ctx, token_key)))


# raw JSON contains escaped quotes → parse, not quoted()
@when(
    parsers.parse('Set role for user "{id_key}" with raw body "{raw}" token "{token_key}" and save response as "{var}"')
)
def set_role_raw(ctx, id_key, raw, token_key, var):
    ctx.save(var, admin.set_role(ctx.str(id_key), raw_json(ctx.render(raw)), bearer(ctx, token_key)))


@when(parsers.parse('Admin delete user "{id_key}" with token "{token_key}" and save response as "{var}"'))
def admin_delete_user(ctx, id_key, token_key, var):
    ctx.save(var, admin.delete_user(ctx.str(id_key), bearer(ctx, token_key)))


@then(parsers.parse('Assert admin stats are consistent in "{var}"'))
def assert_admin_stats(ctx, var):
    assert_admin_stats_consistent(ctx.body(var))
