"""`quoted()` — step parser for phrases whose arguments are all quoted strings.

`parsers.parse('… for "{id}" and save response as "{var}"')` compiles `{id}` to a lazy `.+?` that can
swallow quotes, so it ALSO matches `… for "x" with raw auth header "Bearer" and save response as "r"`
(id = `x" with raw auth header "Bearer`) — two definitions match one step and pytest-bdd silently picks
one. `quoted()` keeps the same readable template but every `"{name}"` matches a quote-free string
(empty allowed, unlike parse's ≥ 1 char), so sibling phrasings can never overlap.

Not for `… with raw body "{…}"` steps: their JSON carries escaped quotes (`{\\"role\\":…}`) — keep `parsers.parse`.
"""

from __future__ import annotations

import re

from pytest_bdd import parsers

_FIELD = re.compile(r"\{(\w+)\}")


def quoted(template: str) -> parsers.re:
    pattern = "".join(
        f'(?P<{part}>[^"]*)' if i % 2 else re.escape(part) for i, part in enumerate(_FIELD.split(template))
    )
    return parsers.re(pattern)
