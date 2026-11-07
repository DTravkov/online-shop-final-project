from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.email import EMAIL_PATTERN, normalize_email


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    delivery_address: str = Field(min_length=1, max_length=255)


class CustomerUpdate(CustomerCreate):
    pass


class CustomerRead(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    customer_id: int


class CustomerProfileUpdate(BaseModel):
    """Partial update: omitted or null fields keep their current values."""

    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=100, pattern=EMAIL_PATTERN)
    phone: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return normalize_email(value)


class DeliveryAddress(BaseModel):
    delivery_address: str = Field(min_length=1, max_length=255)
