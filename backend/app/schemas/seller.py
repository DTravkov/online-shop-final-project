from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.email import EMAIL_PATTERN, normalize_email


class SellerCreate(BaseModel):
    store_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=20)
    rating: Decimal = Field(ge=0, le=5, max_digits=2, decimal_places=1)


class SellerUpdate(SellerCreate):
    pass


class SellerRead(SellerCreate):
    model_config = ConfigDict(from_attributes=True)

    seller_id: int


class SellerProfileUpdate(BaseModel):
    """Partial update of the store profile. The rating is not editable by the seller."""

    store_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=100, pattern=EMAIL_PATTERN)
    phone: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> object:
        return normalize_email(value)
