"""Random test data (port of src/utils/generator.js).

Two sources, chosen per field:
* **Faker** for human-looking, non-unique data — names, message subject/body, sender local part.
* **random alphanumerics** wherever the API demands uniqueness (`email`, `username`, mailbox
  `local_part` → 409 on collision) or an exact shape (`password`, phone `+1XXXXXXXXXX`, fake ids).
Names are filtered to plain letters: the API only requires ≥ 2 chars, but a Faker surname such as
"O'Brien" would leak apostrophes into scenarios that compare the value back.
"""

import random
import string
from collections.abc import Callable

from faker import Faker

_faker = Faker("en_US")

LATIN = string.ascii_lowercase
NUMERIC = string.digits
SPECIAL = "!@#$%^&*()_+-=[]{}|;:,.<>?"
CYRILLIC = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def random_from(chars: str, length: int) -> str:
    return "".join(random.choice(chars) for _ in range(length))


def alphanumeric(n: int) -> str:
    return random_from(LATIN + NUMERIC, n)


def email() -> str:
    return f"{alphanumeric(10)}@play-qa.com"


def username() -> str:
    return f"user_{alphanumeric(8)}"


def password() -> str:
    return f"Pass_{alphanumeric(10)}!1"


def _alpha_name(produce: Callable[[], str], fallback_prefix: str) -> str:
    for _ in range(5):
        candidate = produce()
        if candidate.isalpha() and candidate.isascii() and len(candidate) >= 2:
            return candidate
    return f"{fallback_prefix}{random_from(LATIN, 6)}"


def first_name() -> str:
    return _alpha_name(_faker.first_name, "Test")


def last_name() -> str:
    return _alpha_name(_faker.last_name, "User")


def phone_number() -> str:
    return f"+1{random_from(NUMERIC, 10)}"


def sender_email() -> str:
    return f"{_faker.user_name()}.{alphanumeric(4)}@example.com"


def message_subject() -> str:
    return f"{_faker.sentence(nb_words=4).rstrip('.')} {alphanumeric(6)}"


def message_body() -> str:
    return f"{_faker.paragraph(nb_sentences=2)} {alphanumeric(10)}"


def invalid_email() -> str:
    return f"notanemail_{alphanumeric(4)}"


def short_password() -> str:
    return alphanumeric(4)


def fake_mongo_id() -> str:
    return random_from(NUMERIC, 24)


def fake_uuid() -> str:
    return f"00000000-0000-0000-0000-{random_from(NUMERIC, 12)}"


def text(
    length: int,
    *,
    cyrillic: bool = False,
    latin: bool = True,
    numeric: bool = False,
    spaces: bool = False,
    special: bool = False,
) -> str:
    pool = (
        (LATIN if latin else "")
        + (NUMERIC if numeric else "")
        + (SPECIAL if special else "")
        + (" " if spaces else "")
        + (CYRILLIC if cyrillic else "")
    )
    return random_from(pool or LATIN, length)
