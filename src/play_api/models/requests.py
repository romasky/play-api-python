"""Request builders — port of src/models/*Req.js.

pydantic replaces `JSON.parse(JSON.stringify(obj))`: build with keyword args, serialize with
`.to_body()` → `model_dump(by_alias=True, exclude_none=True)` so unset optional fields are
simply absent (never `null`). Field aliases map pythonic names to the API's snake_case keys
where they differ.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Body(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    def to_body(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class Coordinates(_Body):
    latitude: float | None = None
    longitude: float | None = None


class Salary(_Body):
    amount: float | None = None
    currency: str | None = None


class ProfileReq(_Body):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    gender: str | None = None
    bio: str | None = None
    date_of_birth: str | None = None
    interests: list[str] | None = None
    avatar_url: str | None = None


class ContactsReq(_Body):
    phone: str | None = None
    telegram: str | None = None
    whatsapp: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None


class AddressReq(_Body):
    country: str | None = None
    state: str | None = None
    city: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None
    zip_code: str | None = None
    coordinates: Coordinates | None = None


class EmploymentReq(_Body):
    status: str | None = None
    company: str | None = None
    position: str | None = None
    department: str | None = None
    start_date: str | None = None
    salary: Salary | None = None


class SettingsReq(_Body):
    language: str | None = None
    timezone: str | None = None
    theme: str | None = None
    notifications_enabled: bool | None = None
    two_factor_enabled: bool | None = None
    private_profile: bool | None = None


class CreateUserReq(_Body):
    """POST /users/create, PUT /users/update/:id (no password) and PATCH /users/patch/:id (any subset)."""

    email: str | None = None
    username: str | None = None
    password: str | None = None
    profile: ProfileReq | None = None
    contacts: ContactsReq | None = None
    address: AddressReq | None = None
    employment: EmploymentReq | None = None
    settings: SettingsReq | None = None


class LoginReq(_Body):
    email: str
    password: str


class CreateMailboxReq(_Body):
    domain: str | None = None
    local_part: str | None = None


class SendMessageReq(_Body):
    from_: str = Field(alias="from")
    subject: str
    body: str
    html_body: str | None = None
