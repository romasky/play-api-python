from __future__ import annotations

from typing import Any

import httpx2 as httpx
import pytest

from play_api.context import ScenarioContext

REQUEST = httpx.Request("GET", "https://x/y")


@pytest.fixture
def store() -> dict[str, Any]:
    return {}


@pytest.fixture
def ctx(store: dict[str, Any]) -> ScenarioContext:
    return ScenarioContext(store)


# ─── save / get scoping ───


def test_plain_and_l_keys_are_local_to_the_instance(ctx: ScenarioContext, store: dict[str, Any]) -> None:
    ctx.save("token", "a")
    ctx.save("id_l", "b")
    assert ctx.get("token") == "a"
    assert ctx.get("id") == "b"
    assert ctx.get("id_l") == "b"
    assert store == {}
    assert ScenarioContext(store).get("token") == "token"  # a new scenario does not see it


def test_g_keys_live_in_the_global_store_and_survive_scenarios(ctx: ScenarioContext, store: dict[str, Any]) -> None:
    ctx.save("email_g", "e@x")
    assert store == {"email": "e@x"}
    later = ScenarioContext(store)
    assert later.get("email_g") == "e@x"
    assert later.get("email") == "e@x"  # a local lookup falls back to the global store


def test_local_shadows_global_but_g_reads_only_the_global(ctx: ScenarioContext, store: dict[str, Any]) -> None:
    store["k"] = "global"
    ctx.save("k", "local")
    assert ctx.get("k") == "local"
    assert ctx.get("k_g") == "global"


def test_g_key_does_not_fall_back_to_local(ctx: ScenarioContext) -> None:
    ctx.save("only", "local")
    assert ctx.get("only_g") == "only_g"


def test_unknown_key_passes_through_as_literal(ctx: ScenarioContext) -> None:
    assert ctx.get("bio") == "bio"
    assert ctx.get("x_g") == "x_g"


def test_stored_falsy_values_are_returned_not_the_literal(ctx: ScenarioContext) -> None:
    ctx.save("none", None)
    ctx.save("zero", 0)
    assert ctx.get("none") is None
    assert ctx.get("zero") == 0
    assert ctx.require("none") is None


def test_require_fails_loudly_with_the_clean_name(ctx: ScenarioContext) -> None:
    with pytest.raises(KeyError, match="Context variable 'user' not found"):
        ctx.require("user_g")
    with pytest.raises(KeyError, match="'user' not found"):
        ctx.get("user_l", fail_if_missing=True)


def test_opt_returns_none_for_unknown_and_respects_scoping(ctx: ScenarioContext, store: dict[str, Any]) -> None:
    assert ctx.opt("missing") is None
    assert ctx.opt("missing_g") is None
    store["g"] = 1
    ctx.save("l", 2)
    assert ctx.opt("g") == 1
    assert ctx.opt("g_g") == 1
    assert ctx.opt("l") == 2
    assert ctx.opt("l_l") == 2
    assert ctx.opt("l_g") is None
    store["l"] = 9
    assert ctx.opt("l") == 2  # local wins


# ─── str / render ───


def test_str_of_a_stored_value_is_its_text(ctx: ScenarioContext) -> None:
    ctx.save("n", 42)
    ctx.save("tpl", "${n}")  # a stored value is NOT interpolated
    assert ctx.str("n") == "42"
    assert ctx.str("tpl") == "${n}"
    ctx.save("x${n}", "stored")  # a stored key is looked up, never rendered, even when it looks like a template
    assert ctx.str("x${n}") == "stored"


def test_str_of_a_literal_interpolates_placeholders(ctx: ScenarioContext) -> None:
    ctx.save("id", "u1")
    assert ctx.str("Bearer ${id}") == "Bearer u1"
    assert ctx.str("plain") == "plain"
    assert ctx.str("$id") == "$id"


def test_render_interpolates_every_placeholder_and_fails_on_unknown(ctx: ScenarioContext) -> None:
    ctx.save("a", 1)
    ctx.save("b_g", True)
    assert ctx.render("x=${a}&y=${b_g}&z=${a}") == "x=1&y=True&z=1"
    assert ctx.render("no placeholders") == "no placeholders"
    with pytest.raises(KeyError, match="'nope' not found"):
        ctx.render("q=${nope}")


# ─── response / body ───


def test_response_returns_a_saved_response(ctx: ScenarioContext) -> None:
    res = httpx.Response(200, json={}, request=REQUEST)
    ctx.save("r", res)
    assert ctx.response("r") is res


def test_response_rejects_a_non_response_and_a_missing_key(ctx: ScenarioContext) -> None:
    ctx.save("r", {"status": 200})
    with pytest.raises(AssertionError, match="'r' is not a saved response"):
        ctx.response("r")
    with pytest.raises(KeyError):
        ctx.response("missing")


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (httpx.Response(200, json={"id": "1"}, request=REQUEST), {"id": "1"}),
        (httpx.Response(200, json=[1, 2], request=REQUEST), [1, 2]),
        (httpx.Response(204, request=REQUEST), None),
        (httpx.Response(521, text="<!DOCTYPE html>521", request=REQUEST), "<!DOCTYPE html>521"),
    ],
)
def test_body_is_json_none_or_text(ctx: ScenarioContext, response: httpx.Response, expected: object) -> None:
    ctx.save("r", response)
    assert ctx.body("r") == expected


# ─── defer / run_cleanups ───


def test_cleanups_run_lifo_collect_errors_and_empty_the_queue(ctx: ScenarioContext) -> None:
    order: list[str] = []
    boom = RuntimeError("delete failed")

    def failing() -> None:
        order.append("failing")
        raise boom

    ctx.defer(lambda: order.append("first"))
    ctx.defer(failing)
    ctx.defer(lambda: order.append("last"))
    assert ctx.run_cleanups() == [boom]
    assert order == ["last", "failing", "first"]
    assert ctx.run_cleanups() == []
    assert order == ["last", "failing", "first"]


def test_run_cleanups_without_deferred_actions_returns_no_errors(ctx: ScenarioContext) -> None:
    assert ctx.run_cleanups() == []
