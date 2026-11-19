from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from redis.exceptions import RedisError

from app.core.telegram import TelegramSettings
from app.exceptions import AuthenticationFailed, PermissionDenied
from app.schemas.auth import CurrentAccount
from app.schemas.telegram import (
    TelegramConfirmation,
    TelegramDeliveryResult,
    TelegramJob,
    TelegramRedemption,
    TelegramRedemptionResult,
    TelegramStart,
    TelegramStatus,
)
from app.service.auth import AuthenticatedAccount
from app.service.telegram import TelegramService, get_telegram_service

router = APIRouter(prefix="/telegram", tags=["telegram"])


def require_marketplace_account(account: AuthenticatedAccount) -> CurrentAccount:
    if account.role not in {"customer", "seller"}:
        raise PermissionDenied("A customer or seller account is required.")
    return account


def require_settings(request: Request) -> TelegramSettings:
    if request.app.state.telegram is None:
        raise HTTPException(status_code=503, detail="Telegram integration is disabled.")
    return request.app.state.telegram


def require_bot(
    settings: Annotated[TelegramSettings, Depends(require_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> TelegramSettings:
    scheme, _, credential = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not compare_digest(credential.encode(), settings.service_token.encode()):
        raise AuthenticationFailed("Invalid bot credentials.")
    return settings


async def telegram_service(service: Annotated[TelegramService, Depends(get_telegram_service)]):
    try:
        yield service
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Telegram linking is temporarily unavailable.") from exc


MarketplaceAccount = Annotated[CurrentAccount, Depends(require_marketplace_account)]
Service = Annotated[TelegramService, Depends(telegram_service)]
EnabledSettings = Annotated[TelegramSettings, Depends(require_settings)]
BotSettings = Annotated[TelegramSettings, Depends(require_bot)]


@router.get("/link", response_model=TelegramStatus)
async def link_status(account: MarketplaceAccount, service: Service):
    return await service.status(account.account_id)


@router.post("/link/start", response_model=TelegramStart)
async def start_link(account: MarketplaceAccount, service: Service, settings: EnabledSettings, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return TelegramStart(url=await service.start(account, settings))


@router.post("/link/confirm", status_code=204, dependencies=[Depends(require_settings)])
async def confirm_link(account: MarketplaceAccount, service: Service, data: TelegramConfirmation):
    await service.confirm(account, data.code)


@router.delete("/link", status_code=204)
async def unlink(account: MarketplaceAccount, service: Service):
    await service.unlink(account)


@router.post("/bot/redeem", response_model=TelegramRedemptionResult)
async def redeem(data: TelegramRedemption, settings: BotSettings, service: Service, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return TelegramRedemptionResult(code=await service.redeem(data.envelope, settings))


@router.post("/bot/jobs/claim", response_model=TelegramJob | None, dependencies=[Depends(require_bot)])
async def claim(service: Service):
    return await service.claim()


@router.post("/bot/jobs/{notification_id}/result", status_code=204, dependencies=[Depends(require_bot)])
async def report(notification_id: int, result: TelegramDeliveryResult, service: Service):
    await service.report(notification_id, result)
