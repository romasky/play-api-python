"""Mailbox / message steps — port of src/steps/mailSteps.js.

TODO: Create mailbox (empty / domain / local_part / context local_part / domain+local_part / raw body),
Get mailbox, Delete mailbox, Get messages, Get message, Send message (context values / raw body),
`Assert messages list "{var}" items have no full body` → responses.assert_messages_have_no_full_body.
"""

from pytest_bdd import given, then, when, parsers  # noqa: F401

from play_api.api import client, paths  # noqa: F401
from play_api.models.requests import CreateMailboxReq, SendMessageReq  # noqa: F401
