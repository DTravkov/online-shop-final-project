import os
import re
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from secrets import token_bytes

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

START_CONTEXT = b"mint-market:telegram:start:v1"
BOT_CONTEXT = b"mint-market:telegram:redeem:v1"


def encode_urlsafe(value: bytes) -> str:
    return urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def decode_urlsafe(value: str) -> bytes:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("Expected unpadded base64url.")
    raw = urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if encode_urlsafe(raw) != value:
        raise ValueError("Expected canonical base64url.")
    return raw


def seal(key: bytes, value: bytes, context: bytes) -> str:
    nonce = token_bytes(12)
    return encode_urlsafe(nonce + AESGCM(key).encrypt(nonce, value, context))


def unseal(key: bytes, value: str, context: bytes) -> bytes:
    raw = decode_urlsafe(value)
    return AESGCM(key).decrypt(raw[:12], raw[12:], context)


@dataclass(frozen=True)
class TelegramSettings:
    username: str
    start_key: bytes
    bot_key: bytes
    service_token: str

    @classmethod
    def from_env(cls) -> "TelegramSettings | None":
        username = os.getenv("TELEGRAM_BOT_USERNAME", "")
        if not username:
            return None
        start_key = decode_urlsafe(os.getenv("TELEGRAM_START_KEY", ""))
        bot_key = decode_urlsafe(os.getenv("TELEGRAM_BOT_KEY", ""))
        service_token = os.getenv("TELEGRAM_SERVICE_TOKEN", "")
        if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
            raise ValueError("Set TELEGRAM_BOT_USERNAME without the @ prefix.")
        if len(start_key) != 32 or len(bot_key) != 32 or start_key == bot_key:
            raise ValueError("Set two distinct 32-byte base64url Telegram encryption keys.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,}", service_token):
            raise ValueError("Set a random TELEGRAM_SERVICE_TOKEN of at least 32 base64url characters.")
        return cls(username, start_key, bot_key, service_token)
