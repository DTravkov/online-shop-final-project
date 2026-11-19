from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class TelegramStatus(BaseModel):
    enabled: bool
    linked: bool


class TelegramStart(BaseModel):
    url: str


class TelegramConfirmation(BaseModel):
    code: Annotated[str, Field(pattern=r"^[a-fA-F0-9]{12}$")]


class TelegramRedemption(BaseModel):
    envelope: Annotated[str, Field(min_length=60, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")]


class TelegramRedemptionResult(BaseModel):
    code: str


class TelegramChatUpdate(BaseModel):
    start: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{59}$")]
    chat_id: Annotated[str, Field(pattern=r"^[1-9][0-9]{0,15}$")]


class TelegramJob(BaseModel):
    notification_id: int
    lease_id: UUID
    chat_id: str
    order_id: int
    event: str


class TelegramDeliveryResult(BaseModel):
    lease_id: UUID
    outcome: Literal["sent", "retry", "failed"]
    retry_after: Annotated[int, Field(ge=0, le=86400)] = 0
