"""GET /auth/basic — port of src/steps/basicAuthSteps.js (non-standard error shape { error, message })."""

import base64

from pytest_bdd import parsers, when

from play_api.api import client, paths


@when(parsers.parse('Send GET basic auth request with no auth header and save as "{var}"'))
def basic_no_header(ctx, var):
    ctx.save(var, client.get(paths.AUTH_BASIC))


@when(parsers.parse('Send GET basic auth request with credentials "{user_pass}" and save as "{var}"'))
def basic_credentials(ctx, user_pass, var):
    encoded = base64.b64encode(user_pass.encode()).decode()
    ctx.save(var, client.get(paths.AUTH_BASIC, headers={"Authorization": f"Basic {encoded}"}))


@when(parsers.parse('Send GET basic auth request with raw auth header "{header}" and save as "{var}"'))
def basic_raw_header(ctx, header, var):
    ctx.save(var, client.get(paths.AUTH_BASIC, headers={"Authorization": header}))
