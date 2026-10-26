"""OPTIONS /users/options — port of src/steps/optionsSteps.js (live API answers 204 via Cloudflare)."""

from pytest_bdd import parsers, when

from play_api.services import users


@when(parsers.parse('Send OPTIONS users request and save response as "{var}"'))
def options_users(ctx, var):
    ctx.save(var, users.options())
