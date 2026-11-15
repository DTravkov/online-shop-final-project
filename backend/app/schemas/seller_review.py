from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SellerReviewWrite(BaseModel):
    rating: int = Field(strict=True, ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)

    @field_validator("comment", mode="before")
    @classmethod
    def strip_comment(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SellerReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    review_id: int
    seller_id: int
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime
    customer_name: str


class ReviewEligibility(BaseModel):
    can_review: bool
    review: SellerReviewRead | None
