from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.email import EMAIL_PATTERN, normalize_email

Role = Literal["customer", "seller", "admin"]


class _NewCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=100, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return normalize_email(value)


class CustomerRegister(_NewCredentials):
    full_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    delivery_address: str = Field(min_length=1, max_length=255)


class SellerRegister(_NewCredentials):
    store_name: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return normalize_email(value)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    account_id: int
    role: Role
    customer_id: int | None = None
    seller_id: int | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    email: str
    role: Role
    customer_id: int | None
    seller_id: int | None


class CurrentAccount(BaseModel):
    """Identity decoded from a verified access token."""

    account_id: int
    role: Role
    customer_id: int | None = None
    seller_id: int | None = None
