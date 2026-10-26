"""Ready-made valid request bodies for scenarios that test something *other* than payload validation
(auth, ownership, flows). Validation scenarios build their bodies field by field in the steps."""

from __future__ import annotations

from play_api.config import settings
from play_api.models.requests import (
    AddressReq,
    ContactsReq,
    Coordinates,
    CreateAdminReq,
    CreateUserReq,
    EmploymentReq,
    ProfileReq,
    Salary,
    SettingsReq,
)
from play_api.utils import generator as gen


def minimal_profile() -> ProfileReq:
    return ProfileReq(first_name=gen.first_name(), last_name=gen.last_name())


def minimal_user(country: str | None = None) -> CreateUserReq:
    """Valid create body; `country` isolates the user in shared list queries (`filter=address.country:…`)."""
    return CreateUserReq(
        email=gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=minimal_profile(),
        address=AddressReq(country=country) if country else None,
    )


def admin(seed_code: str | None = settings.admin_seed_code, email: str | None = None) -> CreateAdminReq:
    """Valid create-admin body; `seed_code=None` omits the field entirely."""
    return CreateAdminReq(
        email=email or gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=minimal_profile(),
        seed_code=seed_code,
    )


def random_update() -> CreateUserReq:
    """Valid PUT body (no password)."""
    return CreateUserReq(email=gen.email(), username=gen.username(), profile=minimal_profile())


def random_patch() -> CreateUserReq:
    return CreateUserReq(username=gen.username())


def user_with_all_optional_fields() -> CreateUserReq:
    return CreateUserReq(
        email=gen.email(),
        username=gen.username(),
        password=gen.password(),
        profile=ProfileReq(
            first_name=gen.first_name(),
            last_name=gen.last_name(),
            middle_name="Michael",
            gender="other",
            bio="Short bio here.",
            date_of_birth="1990-01-15",
            interests=["coding", "travel"],
            avatar_url="https://example.com/avatar.jpg",
        ),
        contacts=ContactsReq(
            phone=gen.phone_number(),
            telegram="@tester",
            whatsapp=gen.phone_number(),
            linkedin="https://linkedin.com/in/tester",
            github="https://github.com/tester",
            website="https://tester.dev",
        ),
        address=AddressReq(
            country="US",
            state="California",
            city="San Francisco",
            street="Market St",
            building="100",
            apartment="5A",
            zip_code="94105",
            coordinates=Coordinates(latitude=37.7749, longitude=-122.4194),
        ),
        employment=EmploymentReq(
            status="employed",
            company="Acme Inc",
            position="Engineer",
            department="R&D",
            start_date="2020-03-01",
            salary=Salary(amount=120000, currency="USD"),
        ),
        settings=SettingsReq(
            language="en",
            timezone="America/Los_Angeles",
            theme="dark",
            notifications_enabled=True,
            two_factor_enabled=False,
            private_profile=False,
        ),
    )
