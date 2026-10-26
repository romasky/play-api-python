"""Secret scrubbing for everything that ends up in the PUBLISHED Allure report (GitHub Pages).

Webhook inboxes return a `signing_secret` (`whsec_` + 32 hex — the same shape as a Stripe webhook secret,
so GitHub secret scanning raises an alert for every published one). The values belong to test inboxes that
are deleted after each scenario, but they must not reach a public page: `scrub()` masks them in every
attachment (`api.client.attach`). The Swagger example value is masked the same way.
"""

from __future__ import annotations

import re

_SECRETS = re.compile(r"\bwhsec_[0-9A-Za-z]{16,}")


def scrub(text: str) -> str:
    return _SECRETS.sub("whsec_***", text)
