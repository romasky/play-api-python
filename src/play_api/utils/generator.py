"""Random test data (port of src/utils/generator.js). Faker is available for richer data;
these helpers keep the exact shapes the API expects (username prefix, token format, …)."""

import random
import string

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


def first_name() -> str:
    return f"Test{random_from(LATIN, 6)}"


def last_name() -> str:
    return f"User{random_from(LATIN, 6)}"


def phone_number() -> str:
    return f"+1{random_from(NUMERIC, 10)}"


def sender_email() -> str:
    return f"{alphanumeric(8)}@example.com"


def message_subject() -> str:
    return f"Subject {alphanumeric(6)}"


def message_body() -> str:
    return f"Body {alphanumeric(10)}"


def invalid_email() -> str:
    return f"notanemail_{alphanumeric(4)}"


def short_password() -> str:
    return alphanumeric(4)


def fake_mongo_id() -> str:
    return random_from(NUMERIC, 24)


def fake_uuid() -> str:
    return f"00000000-0000-0000-0000-{random_from(NUMERIC, 12)}"


def text(length: int, *, cyrillic: bool = False, latin: bool = True, numeric: bool = False,
         spaces: bool = False, special: bool = False) -> str:
    pool = (LATIN if latin else "") + (NUMERIC if numeric else "") + (SPECIAL if special else "") \
        + (" " if spaces else "") + (CYRILLIC if cyrillic else "")
    return random_from(pool or LATIN, length)
