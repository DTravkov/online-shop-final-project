from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.db import get_db
from app.exceptions import RecordConflict
from app.models.account import Account
from app.models.telegram import TelegramLink, TelegramNotification
from app.schemas.telegram import TelegramDeliveryResult

LEASE_SECONDS = 90
MAX_ATTEMPTS = 8


class TelegramRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        try:
            async with self.db.begin():
                yield
        except IntegrityError as exc:
            raise RecordConflict("This Telegram chat or marketplace account is already linked.") from exc

    async def for_account(self, account_id: int) -> TelegramLink | None:
        return await self.db.scalar(select(TelegramLink).where(TelegramLink.account_id == account_id))

    async def for_chat(self, chat_id: int) -> TelegramLink | None:
        return await self.db.scalar(select(TelegramLink).where(TelegramLink.chat_id == chat_id))

    async def create_link(self, account_id: int, chat_id: int) -> None:
        self.db.add(TelegramLink(link_id=uuid4(), account_id=account_id, chat_id=chat_id))
        await self.db.flush()

    async def delete_link(self, link: TelegramLink) -> None:
        await self.db.delete(link)
        await self.db.flush()

    async def enqueue(
        self, order_id: int, event: str, now: datetime, *,
        customer_id: int | None = None, seller_ids: Sequence[int] = (),
    ) -> None:
        recipient = Account.customer_id == customer_id if customer_id is not None else Account.seller_id.in_(seller_ids)
        # Keep the link present until the job is inserted. Concurrent unlink then deletes the job by cascade.
        links = await self.db.scalars(
            select(TelegramLink.link_id).join(Account).where(recipient)
            .order_by(TelegramLink.link_id).with_for_update(read=True, key_share=True, of=TelegramLink)
        )
        self.db.add_all([
            TelegramNotification(link_id=link_id, order_id=order_id, event=event, available_at=now)
            for link_id in links
        ])
        await self.db.flush()

    async def claim(self, now: datetime) -> tuple[TelegramNotification, int] | None:
        earlier = aliased(TelegramNotification)
        # Keep messages in order per chat, while allowing other chats to proceed during a retry.
        has_earlier_job = select(earlier.notification_id).where(
            earlier.link_id == TelegramNotification.link_id,
            earlier.notification_id < TelegramNotification.notification_id,
            earlier.finished_at.is_(None),
        ).exists()
        statement = (
            select(TelegramNotification, TelegramLink.chat_id).join(TelegramLink)
            .where(
                TelegramNotification.finished_at.is_(None), TelegramNotification.available_at <= now, ~has_earlier_job,
            ).order_by(TelegramNotification.notification_id).limit(1)
            .with_for_update(of=TelegramNotification, skip_locked=True)
        )
        row = (await self.db.execute(statement)).one_or_none()
        if row is None:
            return None
        job, chat_id = row
        if job.attempts >= MAX_ATTEMPTS:
            job.finished_at = now
            job.outcome = "failed"
            job.lease_id = None
            return None
        job.lease_id = uuid4()
        job.available_at = now + timedelta(seconds=LEASE_SECONDS)
        job.attempts += 1
        await self.db.flush()
        return job, chat_id

    async def report(self, notification_id: int, result: TelegramDeliveryResult, now: datetime) -> None:
        job = await self.db.scalar(
            select(TelegramNotification).where(
                TelegramNotification.notification_id == notification_id,
                TelegramNotification.lease_id == result.lease_id,
                TelegramNotification.finished_at.is_(None),
            ).with_for_update()
        )
        if job is None:
            return  # The link was removed, or this lease is no longer current.
        job.lease_id = None
        if result.outcome == "retry" and job.attempts < MAX_ATTEMPTS:
            delay = max(result.retry_after, min(10 * 2 ** (job.attempts - 1), 600))
            job.available_at = now + timedelta(seconds=delay)
        else:
            job.finished_at = now
            job.outcome = "sent" if result.outcome == "sent" else "failed"
        await self.db.flush()


def get_telegram_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> TelegramRepository:
    return TelegramRepository(db)
