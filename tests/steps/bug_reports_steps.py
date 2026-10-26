"""/bug-reports steps — bodies come from `factories.perfect_bug_report` / named `factories.bug_report` variants.

"anonymously": a report without a header is a valid, unsaved anonymous submission (200), not an auth failure."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.api import auth
from play_api.models import factories
from play_api.models.responses.bug_reports import assert_criterion, assert_every_criterion
from play_api.services import bug_reports
from play_api.utils.gherkin import query_pairs, raw_json
from tests.steps.support import bearer, quoted, raw_header


@when(quoted('Submit a perfect "{bug_id}" bug report anonymously and save response as "{var}"'))
def submit_perfect_anonymously(ctx, bug_id, var):
    ctx.save(var, bug_reports.submit(factories.perfect_bug_report(bug_id), auth.none()))


@when(quoted('Submit a perfect "{bug_id}" bug report with token "{token_key}" and save response as "{var}"'))
def submit_perfect_with_token(ctx, bug_id, token_key, var):
    ctx.save(var, bug_reports.submit(factories.perfect_bug_report(bug_id), bearer(ctx, token_key)))


@when(quoted('Submit a "{bug_id}" bug report with severity "{severity}" anonymously and save response as "{var}"'))
def submit_with_severity(ctx, bug_id, severity, var):
    ctx.save(var, bug_reports.submit(factories.perfect_bug_report(bug_id, severity), auth.none()))


@when(quoted('Submit a "{variant}" bug report anonymously and save response as "{var}"'))
def submit_variant(ctx, variant, var):
    ctx.save(var, bug_reports.submit(factories.bug_report(variant), auth.none()))


@when(quoted('Submit a perfect "{bug_id}" bug report with raw auth header "{header}" and save response as "{var}"'))
def submit_perfect_raw_auth(ctx, bug_id, header, var):
    ctx.save(var, bug_reports.submit(factories.perfect_bug_report(bug_id), raw_header(ctx, header)))


@when(parsers.parse('Submit a bug report with raw body "{raw}" anonymously and save response as "{var}"'))
def submit_raw(ctx, raw, var):
    ctx.save(var, bug_reports.submit(raw_json(ctx.render(raw)), auth.none()))


@when(quoted('List my bug reports with token "{token_key}" and save response as "{var}"'))
def list_reports(ctx, token_key, var):
    ctx.save(var, bug_reports.list_mine(bearer(ctx, token_key)))


@when(quoted('List my bug reports with query "{query}" and token "{token_key}" and save response as "{var}"'))
def list_reports_query(ctx, query, token_key, var):
    ctx.save(var, bug_reports.list_mine(bearer(ctx, token_key), query_pairs(ctx.render(query))))


@when(parsers.parse('List my bug reports with no auth token and save response as "{var}"'))
def list_reports_no_auth(ctx, var):
    ctx.save(var, bug_reports.list_mine(auth.none()))


@when(quoted('Get bug report "{id_key}" with token "{token_key}" and save response as "{var}"'))
def get_report(ctx, id_key, token_key, var):
    ctx.save(var, bug_reports.get(ctx.str(id_key), bearer(ctx, token_key)))


@when(quoted('Get bug report "{id_key}" with no auth token and save response as "{var}"'))
def get_report_no_auth(ctx, id_key, var):
    ctx.save(var, bug_reports.get(ctx.str(id_key), auth.none()))


@then(quoted('Assert score criterion "{criterion}" is "{ok}" in response "{var}"'))
def assert_score_criterion(ctx, criterion, ok, var):
    assert_criterion(ctx.body(var), criterion, ok == "true")


@then(quoted('Assert every score criterion is "{ok}" in response "{var}"'))
def assert_every_score_criterion(ctx, ok, var):
    assert_every_criterion(ctx.body(var), ok == "true")
