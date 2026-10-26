"""/chaos/* steps. A client-side timeout is an OUTCOME here, not an error: the step saves the exception
under the response key and `Assert request "…" timed out` checks it."""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx2 as httpx
from pytest_bdd import parsers, step, then, when

from play_api.services import chaos
from play_api.utils.gherkin import query_pairs, unescape_quotes
from play_api.utils.json_path import get_path
from tests.steps.parsing import quoted


def _timed(ctx, var: str, call: Callable[[], httpx.Response]) -> None:
    """Save the response — or the TimeoutException — and the wall time under `<var>Seconds`."""
    started = time.monotonic()
    try:
        ctx.save(var, call())
    except httpx.TimeoutException as exc:
        ctx.save(var, exc)
    ctx.save(f"{var}Seconds", time.monotonic() - started)


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
    outcome = ctx.get(var, fail_if_missing=True)
    assert isinstance(outcome, httpx.TimeoutException), f"Expected a client timeout, got {outcome!r}"


@then(parsers.parse('Assert request "{var}" took between {low:d} and {high:d} seconds'))
def assert_took_between(ctx, var, low, high):
    seconds = ctx.get(f"{var}Seconds", fail_if_missing=True)
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
    """The client-side retry loop the sequence exists for: each attempt must answer its PLANNED status."""
    plan = get_path(ctx.body(plan_var), "steps")
    for attempt, planned in enumerate(plan, start=1):
        response = chaos.flaky_step(str(planned["index"]), query_pairs(query))
        assert response.status_code == planned["status"], (
            f"step {planned['index']} answered {response.status_code}, the plan says {planned['status']}"
        )
        if response.status_code == 200:
            ctx.save(key, attempt)
            return
    raise AssertionError(f"no successful step in the plan: {plan}")


# ─── Gzip ──────────────────────────────────────────────────────────────────


@when(quoted('Get chaos gzip with Accept-Encoding "{encoding}" and save response as "{var}"'))
def get_gzip(ctx, encoding, var):
    ctx.save(var, chaos.gzip({"Accept-Encoding": encoding}))


@when(quoted('Read the raw chaos gzip body with Accept-Encoding "{encoding}" and save its first bytes as "{key}"'))
def read_raw_gzip(ctx, encoding, key):
    ctx.save(key, chaos.gzip_raw_prefix({"Accept-Encoding": encoding}).hex())


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


@then(parsers.parse('Assert response "{var}" followed {hops:d} redirects'))
def assert_redirect_count(ctx, var, hops):
    history = ctx.response(var).history
    assert len(history) == hops, f"followed {len(history)} redirects, expected {hops}: {[h.url for h in history]}"


# ─── Status ────────────────────────────────────────────────────────────────


@when(quoted('Get chaos status "{code}" and save response as "{var}"'))
def get_status(ctx, code, var):
    ctx.save(var, chaos.status(code))


@then(quoted('Assert response "{var}" is plain text "{text}"'))
def assert_plain_text(ctx, var, text):
    response = ctx.response(var)
    assert response.headers.get("content-type", "").startswith("text/"), response.headers.get("content-type")
    assert response.text.strip() == text, f"body {response.text!r}, expected {text!r}"


@then(parsers.parse('Assert response "{var}" is a Cloudflare error page for status {code:d}'))
def assert_cloudflare_page(ctx, var, code):
    """Cloudflare discards the origin body of 502/504/52x: plain text, or an HTML page when the client accepts
    gzip (httpx always does) — either way NOT the documented JSON."""
    response = ctx.response(var)
    assert response.headers.get("content-type", "").startswith("text/"), response.headers.get("content-type")
    assert str(code) in response.text, f"Cloudflare page does not mention {code}: {response.text[:200]!r}"
    assert "status_code" not in response.text, "origin JSON body leaked through Cloudflare"
