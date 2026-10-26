"""GET /auth/basic — port of src/steps/basicAuthSteps.js (non-standard error shape { error, message })."""

from pytest_bdd import parsers, when

from play_api.api import auth
from play_api.services import session


@when(parsers.parse('Send GET basic auth request with no auth header and save as "{var}"'))
def basic_no_header(ctx, var):
    ctx.save(var, session.basic_auth())


@when(parsers.parse('Send GET basic auth request with credentials "{user_pass}" and save as "{var}"'))
def basic_credentials(ctx, user_pass, var):
    ctx.save(var, session.basic_auth(auth.basic(user_pass)))


@when(parsers.parse('Send GET basic auth request with raw auth header "{header}" and save as "{var}"'))
def basic_raw_header(ctx, header, var):
    ctx.save(var, session.basic_auth(auth.raw(header)))
