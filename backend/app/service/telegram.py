from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest
from secrets import token_bytes, token_hex
from typing import Annotated, Literal

from cryptography.exceptions import InvalidTag
from fastapi import Depends, Request
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis

from app.core.telegram import BOT_CONTEXT, START_CONTEXT, TelegramSettings, encode_urlsafe, seal, unseal
from app.exceptions import BusinessRuleViolation, PermissionDenied, RecordConflict, RecordNotFound
from app.repository.account import AccountRepository, get_account_repository
from app.repository.telegram import TelegramRepository, get_telegram_repository
from app.schemas.auth import CurrentAccount
from app.schemas.telegram import TelegramChatUpdate, TelegramDeliveryResult, TelegramJob, TelegramStatus

LINK_TTL = 300
KEY_PREFIX = "mint-market:telegram:v1:"
EXPIRED_LINK = "Telegram link expired or was already used. Generate a new link from your profile."


class LinkAttempt(BaseModel):
    account_id: int
    role: Literal["customer", "seller"]
    expires_at: int
    chat_id: int | None = None
    code_hash: str | None = None


def active_key(account_id: int) -> str:
    return f"{KEY_PREFIX}active:{account_id}"


def attempt_key(reference: bytes) -> str:
    return f"{KEY_PREFIX}attempt:{encode_urlsafe(reference)}"


class TelegramService:
    def __init__(
        self, links: TelegramRepository, accounts: AccountRepository, redis: Redis, settings: TelegramSettings | None,
    ):
        self.tg_repo = links
        self.accounts = accounts
        self.redis = redis
        self.settings = settings

    async def _lock_account(self, account_id: int, role: str) -> None:
        if role not in {"customer", "seller"}:
            raise PermissionDenied("A customer or seller account is required.")
        records = await self.accounts.get_many_for_update([account_id])
        if not records:
            raise RecordNotFound("Account", account_id)
        if records[0].role != role:
            raise PermissionDenied("Account role has changed. Sign in again.")

    async def status(self, account_id: int) -> TelegramStatus:
        linked = await self.tg_repo.for_account(account_id) is not None
        return TelegramStatus(enabled=self.settings is not None, linked=linked)

    async def start(self, account: CurrentAccount, settings: TelegramSettings) -> str:
        reference = token_bytes(16)
        key = attempt_key(reference)
        async with self.tg_repo.transaction():
            await self._lock_account(account.account_id, account.role)
            if await self.tg_repo.for_account(account.account_id):
                raise RecordConflict("Disconnect the current Telegram chat before linking another one.")
            attempt = LinkAttempt(
                account_id=account.account_id,
                role=account.role,
                expires_at=int(datetime.now(UTC).timestamp()) + LINK_TTL,
            )
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.set(key, attempt.model_dump_json(), ex=LINK_TTL)
                pipe.set(active_key(account.account_id), key, ex=LINK_TTL)
                await pipe.execute()
        return f"https://t.me/{settings.username}?start={seal(settings.start_key, reference, START_CONTEXT)}"

    async def redeem(self, envelope: str, settings: TelegramSettings) -> str:
        try:
            data = TelegramChatUpdate.model_validate_json(unseal(settings.bot_key, envelope, BOT_CONTEXT))
            reference = unseal(settings.start_key, data.start, START_CONTEXT)
            chat_id = int(data.chat_id)
            if len(reference) != 16 or chat_id >= 2 ** 52:
                raise ValueError("Invalid Telegram link data.")
        except (InvalidTag, ValueError) as exc:
            raise BusinessRuleViolation(EXPIRED_LINK) from exc

        key = attempt_key(reference)
        attempt = await self._read_attempt(key)
        if attempt is None:
            raise BusinessRuleViolation(EXPIRED_LINK)

        async with self.tg_repo.transaction():
            # All transitions for an account share this lock, including requests handled by other API instances.
            await self._lock_account(attempt.account_id, attempt.role)
            if await self.redis.get(active_key(attempt.account_id)) != key.encode():
                raise BusinessRuleViolation(EXPIRED_LINK)
            attempt = await self._read_attempt(key)
            if attempt is None or attempt.chat_id is not None:
                raise BusinessRuleViolation(EXPIRED_LINK)
            if await self.tg_repo.for_chat(chat_id):
                raise RecordConflict("This Telegram chat is already linked to another marketplace account.")
            code = token_hex(6)
            attempt.chat_id = chat_id
            attempt.code_hash = sha256(code.encode()).hexdigest()
            if not await self.redis.set(key, attempt.model_dump_json(), xx=True, keepttl=True):
                raise BusinessRuleViolation(EXPIRED_LINK)
        return code

    async def confirm(self, account: CurrentAccount, code: str) -> None:
        async with self.tg_repo.transaction():
            await self._lock_account(account.account_id, account.role)
            if await self.tg_repo.for_account(account.account_id):
                raise RecordConflict("Your marketplace account already has a Telegram link.")
            key = await self.redis.get(active_key(account.account_id))
            attempt = await self._read_attempt(key) if key else None
            if (
                attempt is None or attempt.account_id != account.account_id or attempt.role != account.role
                or attempt.chat_id is None or attempt.code_hash is None
                or not compare_digest(attempt.code_hash, sha256(code.lower().encode()).hexdigest())
            ):
                raise BusinessRuleViolation("Invalid or expired Telegram confirmation code.")
            if not await self.redis.getdel(key):
                raise BusinessRuleViolation(EXPIRED_LINK)
            await self.redis.delete(active_key(account.account_id))
            await self.tg_repo.create_link(account.account_id, attempt.chat_id)
            await self.tg_repo.enqueue(
                -1, "link_success", datetime.now(UTC), customer_id=account.customer_id,
                seller_ids=(account.seller_id,) if account.seller_id is not None else (),
            )

    async def unlink(self, account: CurrentAccount) -> None:
        async with self.tg_repo.transaction():
            await self._lock_account(account.account_id, account.role)
            key = await self.redis.getdel(active_key(account.account_id))
            if key:
                await self.redis.delete(key)
            if link := await self.tg_repo.for_account(account.account_id):
                await self.tg_repo.enqueue(
                    -1, "unlink_success", datetime.now(UTC), customer_id=account.customer_id,
                    seller_ids=(account.seller_id,) if account.seller_id is not None else (),
                )
                await self.tg_repo.delete_link(link)

    async def claim(self) -> TelegramJob | None:
        async with self.tg_repo.transaction():
            job = await self.tg_repo.claim(datetime.now(UTC))
            if job is None:
                return None
            return TelegramJob(
                notification_id=job.notification_id, chat_id=str(job.chat_id), lease_id=job.lease_id,
                order_id=job.order_id, event=job.event,
            )

    async def report(self, notification_id: int, result: TelegramDeliveryResult) -> None:
        async with self.tg_repo.transaction():
            await self.tg_repo.report(notification_id, result, datetime.now(UTC))

    async def _read_attempt(self, key: str | bytes) -> LinkAttempt | None:
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            attempt = LinkAttempt.model_validate_json(value)
        except ValidationError:
            return None
        return attempt if attempt.expires_at > datetime.now(UTC).timestamp() else None


def get_telegram_service(
    request: Request,
    links: Annotated[TelegramRepository, Depends(get_telegram_repository)],
    accounts: Annotated[AccountRepository, Depends(get_account_repository)],
) -> TelegramService:
    return TelegramService(links, accounts, request.app.state.redis, request.app.state.telegram)
