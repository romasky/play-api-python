"""/files/* steps. Samples are in-memory (`play_api.utils.samples`); every successful upload is deleted
after the scenario (`ctx.defer`) because files share a server-side storage budget."""

from __future__ import annotations

from pytest_bdd import parsers, then, when

from play_api.api import auth
from play_api.api.client import Headers
from play_api.services import files
from play_api.utils.gherkin import query_pairs
from play_api.utils.samples import sample
from tests.steps.parsing import quoted


def _upload(ctx, var: str, headers: Headers, **kwargs) -> None:
    response = files.upload(headers, **kwargs)
    ctx.save(var, response)
    if response.status_code == 201:
        file_id = response.json()["file_id"]
        ctx.defer(lambda: files.delete(file_id, headers))


@when(quoted('Upload sample "{name}" with token "{token_key}" and save response as "{var}"'))
def upload_with_token(ctx, name, token_key, var):
    _upload(ctx, var, auth.bearer(ctx.str(token_key)), file=sample(name))


@when(quoted('Upload sample "{name}" anonymously and save response as "{var}"'))
def upload_anonymously(ctx, name, var):
    _upload(ctx, var, auth.none(), file=sample(name))


@when(quoted('Upload sample "{name}" declared as "{content_type}" anonymously and save response as "{var}"'))
def upload_declared_as(ctx, name, content_type, var):
    filename, content, _ = sample(name)
    _upload(ctx, var, auth.none(), file=(filename, content, content_type))


@when(quoted('Upload sample "{name}" with description "{desc_key}" anonymously and save response as "{var}"'))
def upload_with_description(ctx, name, desc_key, var):
    _upload(ctx, var, auth.none(), file=sample(name), description=ctx.str(desc_key))


@when(quoted('Upload sample "{name}" in multipart field "{field}" anonymously and save response as "{var}"'))
def upload_in_field(ctx, name, field, var):
    _upload(ctx, var, auth.none(), file=sample(name), field=field)


@when(quoted('Upload sample "{name}" with raw auth header "{header}" and save response as "{var}"'))
def upload_raw_auth(ctx, name, header, var):
    _upload(ctx, var, auth.raw(header), file=sample(name))


@when(parsers.parse('Upload a multipart body without a file part and save response as "{var}"'))
def upload_without_file(ctx, var):
    _upload(ctx, var, auth.none(), file=None, description="no file here")


@when(parsers.parse('Upload a JSON body instead of multipart and save response as "{var}"'))
def upload_json_body(ctx, var):
    ctx.save(var, files.upload_json({"file": "not-a-file"}, auth.none()))


# ─── List / metadata / download / delete ───────────────────────────────────


@when(quoted('List my files with token "{token_key}" and save response as "{var}"'))
def list_files(ctx, token_key, var):
    ctx.save(var, files.list_mine(auth.bearer(ctx.str(token_key))))


@when(quoted('List my files with query "{query}" and token "{token_key}" and save response as "{var}"'))
def list_files_query(ctx, query, token_key, var):
    ctx.save(var, files.list_mine(auth.bearer(ctx.str(token_key)), query_pairs(ctx.render(query))))


@when(parsers.parse('List my files with no auth token and save response as "{var}"'))
def list_files_no_auth(ctx, var):
    ctx.save(var, files.list_mine(auth.none()))


@when(quoted('Get file "{id_key}" metadata and save response as "{var}"'))
def file_metadata(ctx, id_key, var):
    ctx.save(var, files.metadata(ctx.str(id_key)))


@when(quoted('Get file "{id_key}" metadata with raw auth header "{header}" and save response as "{var}"'))
def file_metadata_raw_auth(ctx, id_key, header, var):
    ctx.save(var, files.metadata(ctx.str(id_key), auth.raw(header)))


@when(quoted('Download file "{id_key}" and save response as "{var}"'))
def download_file(ctx, id_key, var):
    ctx.save(var, files.download(ctx.str(id_key)))


@when(quoted('Download file "{id_key}" with query "{query}" and save response as "{var}"'))
def download_file_query(ctx, id_key, query, var):
    ctx.save(var, files.download(ctx.str(id_key), query_pairs(query)))


@when(quoted('Delete file "{id_key}" with token "{token_key}" and save response as "{var}"'))
def delete_file_token(ctx, id_key, token_key, var):
    ctx.save(var, files.delete(ctx.str(id_key), auth.bearer(ctx.str(token_key))))


@when(quoted('Delete file "{id_key}" anonymously and save response as "{var}"'))
def delete_file_anonymously(ctx, id_key, var):
    ctx.save(var, files.delete(ctx.str(id_key), auth.none()))


# ─── Byte-level assertions ─────────────────────────────────────────────────


@then(quoted('Assert response "{var}" body equals sample "{name}"'))
def assert_body_equals_sample(ctx, var, name):
    _, expected, _ = sample(name)
    actual = ctx.response(var).content
    assert actual == expected, f"Downloaded {len(actual)} bytes differ from sample '{name}' ({len(expected)} bytes)"


@then(quoted('Assert field "{field}" equals the size of sample "{name}" in response "{var}"'))
def assert_size_of_sample(ctx, field, name, var):
    _, content, _ = sample(name)
    actual = ctx.body(var).get(field)
    assert actual == len(content), f"'{field}' = {actual}, expected {len(content)} (size of sample '{name}')"
