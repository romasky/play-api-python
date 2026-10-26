"""/chaos/* steps. A client-side timeout is an OUTCOME here, not an error: `timing.timed` keeps the response
or the exception under the response key (and the wall time under `<key>Seconds`)."""

from __future__ import annotations

from collections.abc import Callable

import httpx2 as httpx
from pytest_bdd import parsers, step, then, when

from play_api.assertions import assert_cloudflare_page, assert_plain_text, assert_plan_replays
from play_api.services import chaos
from play_api.timing import timed
from play_api.utils.gherkin import query_pairs, unescape_quotes
from play_api.utils.json_path import get_path
from tests.steps.support import quoted


def _timed(ctx, var: str, call: Callable[[], httpx.Response]) -> None:
    outcome = timed(call)
    ctx.save(var, outcome.result)
    ctx.save(f"{var}Seconds", outcome.seconds)


# ─── Cache (conditional requests) ──────────────────────────────────────────


@when(parsers.parse('Get chaos cache and save response as "{var}"'))
def get_cache(ctx, var):
    ctx.save(var, chaos.cache())


@when(quoted('Send "{method}" chaos cache request and save response as "{var}"'))
def cache_method(ctx, method, var):
    ctx.save(var, chaos.cache(method=method))


# parse + unescape: ETag values carry quotes ("chaos-v1", W/"chaos-v1")
@when(parsers.parse('Get chaos cache with header "{name}" value "{value}" and save response as "{var}"'))
def get_cache_header(ctx, name, value, var):
    ctx.save(var, chaos.cache({name: unescape_quotes(value)}))


@when(
    parsers.parse(
        'Get chaos cache with If-None-Match "{etag}" and If-Modified-Since "{since}" and save response as "{var}"'
    )
)
def get_cache_both(ctx, etag, since, var):
    ctx.save(var, chaos.cache({"If-None-Match": unescape_quotes(etag), "If-Modified-Since": since}))


# ─── Delay / timeout ───────────────────────────────────────────────────────


@when(quoted('Get chaos delay "{seconds}" and save response as "{var}"'))
def get_delay(ctx, seconds, var):
    _timed(ctx, var, lambda: chaos.delay(seconds))


@when(parsers.parse('Get chaos delay "{seconds}" with a read timeout of {limit:d} second and save response as "{var}"'))
def get_delay_with_timeout(ctx, seconds, limit, var):
    _timed(ctx, var, lambda: chaos.delay(seconds, read_timeout=limit))


@when(quoted('Get chaos timeout with query "{query}" and save response as "{var}"'))
def get_timeout(ctx, query, var):
    _timed(ctx, var, lambda: chaos.timeout(query_pairs(query)))


@when(
    parsers.parse(
        'Get chaos timeout with query "{query}" and a read timeout of {limit:d} second and save response as "{var}"'
    )
)
def get_timeout_with_timeout(ctx, query, limit, var):
    _timed(ctx, var, lambda: chaos.timeout(query_pairs(query), read_timeout=limit))


@then(parsers.parse('Assert request "{var}" timed out'))
def assert_timed_out(ctx, var):
    outcome = ctx.require(var)
    assert isinstance(outcome, httpx.TimeoutException), f"Expected a client timeout, got {outcome!r}"


@then(parsers.parse('Assert request "{var}" took between {low:d} and {high:d} seconds'))
def assert_took_between(ctx, var, low, high):
    seconds = ctx.require(f"{var}Seconds")
    assert low <= seconds <= high, f"'{var}' took {seconds:.2f} s, expected {low}..{high} s"


# ─── Echo ──────────────────────────────────────────────────────────────────


@when(quoted('Send "{method}" chaos echo with query "{query}" and save response as "{var}"'))
def echo_query(ctx, method, query, var):
    ctx.save(var, chaos.echo(method, params=query_pairs(query)))


@when(quoted('Send GET chaos echo with header "{name}" value "{value}" and save response as "{var}"'))
def echo_header(ctx, name, value, var):
    ctx.save(var, chaos.echo("GET", headers={name: ctx.str(value)}))


@when(parsers.parse('Post chaos echo as "{content_type}" with body "{body}" and save response as "{var}"'))
def echo_body(ctx, content_type, body, var):
    text = unescape_quotes(body)
    ctx.save("sentBody", text)
    ctx.save(var, chaos.echo("POST", headers={"Content-Type": content_type}, content=text))


@when(quoted('Post chaos echo with the bytes "{hex_bytes}" and save response as "{var}"'))
def echo_bytes(ctx, hex_bytes, var):
    headers = {"Content-Type": "application/octet-stream"}
    ctx.save(var, chaos.echo("POST", headers=headers, content=bytes.fromhex(hex_bytes)))


@when(parsers.parse('Post chaos echo with a text body of {size:d} bytes and save response as "{var}"'))
def echo_sized(ctx, size, var):
    ctx.save(var, chaos.echo("POST", headers={"Content-Type": "text/plain"}, content="a" * size))


# ─── Flaky ─────────────────────────────────────────────────────────────────


@step(quoted('Get chaos flaky with query "{query}" and save response as "{var}"'))
def get_flaky(ctx, query, var):
    ctx.save(var, chaos.flaky(query_pairs(query)))


@step(quoted('Get chaos flaky sequence with query "{query}" and save response as "{var}"'))
def get_flaky_sequence(ctx, query, var):
    ctx.save(var, chaos.flaky_sequence(query_pairs(query)))


@step(quoted('Get chaos flaky step "{index}" with query "{query}" and save response as "{var}"'))
def get_flaky_step(ctx, index, query, var):
    ctx.save(var, chaos.flaky_step(index, query_pairs(query)))


@then(quoted('Assert flaky plan statuses are "{statuses}" in response "{var}"'))
def assert_plan_statuses(ctx, statuses, var):
    actual = [str(s["status"]) for s in get_path(ctx.body(var), "steps")]
    assert actual == statuses.split(","), f"planned statuses {actual}, expected {statuses}"


@when(quoted('Retry chaos flaky steps of plan "{plan_var}" with query "{query}" until success and save as "{key}"'))
def retry_until_success(ctx, plan_var, query, key):
    plan = get_path(ctx.body(plan_var), "steps")
    ctx.save(key, assert_plan_replays(plan, lambda index: chaos.flaky_step(index, query_pairs(query))))


# ─── Gzip ──────────────────────────────────────────────────────────────────


@when(quoted('Get chaos gzip with Accept-Encoding "{encoding}" and save response as "{var}"'))
def get_gzip(ctx, encoding, var):
    ctx.save(var, chaos.gzip({"Accept-Encoding": encoding}))


@when(quoted('Read the raw chaos gzip body with Accept-Encoding "{encoding}" and save its first bytes as "{key}"'))
def read_raw_gzip(ctx, encoding, key):
    ctx.save(key, chaos.gzip_magic({"Accept-Encoding": encoding}).hex())


# ─── Redirect ──────────────────────────────────────────────────────────────


@when(quoted('Send "{method}" chaos redirect "{hops}" with query "{query}" and save response as "{var}"'))
def redirect_no_follow(ctx, method, hops, query, var):
    ctx.save(var, chaos.redirect(method, hops, params=query_pairs(query)))


@when(
    quoted(
        'Send "{method}" chaos redirect "{hops}" with query "{query}" and body "{body}" following redirects and save response as "{var}"'  # noqa: E501
    )
)
def redirect_follow(ctx, method, hops, query, body, var):
    ctx.save(var, chaos.redirect(method, hops, params=query_pairs(query), content=body or None, follow=True))


@when(quoted('Send "{method}" directly to chaos redirect done and save response as "{var}"'))
def redirect_done_direct(ctx, method, var):
    ctx.save(var, chaos.redirect_done(method))


@when(parsers.parse('Post directly to chaos redirect done a body of {size:d} bytes and save response as "{var}"'))
def redirect_done_sized(ctx, size, var):
    ctx.save(var, chaos.redirect_done("POST", "a" * size))


@then(parsers.parse('Assert response "{var}" followed {hops:d} redirects'))
def assert_redirect_count(ctx, var, hops):
    history = ctx.response(var).history
    assert len(history) == hops, f"followed {len(history)} redirects, expected {hops}: {[h.url for h in history]}"


# ─── Status ────────────────────────────────────────────────────────────────


@when(quoted('Get chaos status "{code}" and save response as "{var}"'))
def get_status(ctx, code, var):
    ctx.save(var, chaos.status(code))


@then(quoted('Assert response "{var}" is plain text "{text}"'))
def assert_response_plain_text(ctx, var, text):
    assert_plain_text(ctx.response(var), text)


@then(parsers.parse('Assert response "{var}" is a Cloudflare error page for status {code:d}'))
def assert_response_cloudflare_page(ctx, var, code):
    assert_cloudflare_page(ctx.response(var), code)
