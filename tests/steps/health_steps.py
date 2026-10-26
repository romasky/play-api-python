"""GET /health — port of src/steps/healthSteps.js."""

from pytest_bdd import parsers, when

from play_api.services import system


@when(parsers.parse('Send GET health request and save as "{var}"'))
def get_health(ctx, var):
    ctx.save(var, system.health())


@when(parsers.parse('Send GET health request with X-Request-ID "{request_id_key}" and save as "{var}"'))
def get_health_with_request_id(ctx, request_id_key, var):
    ctx.save(var, system.health({"X-Request-ID": ctx.str(request_id_key)}))
