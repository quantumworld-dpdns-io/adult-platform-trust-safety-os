"""MFA service using TOTP (pyotp) and backup codes."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

import pyotp

from src.config.settings import settings

TOTP_INTERVAL = 30
TOTP_DIGITS = 6
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(
    secret: str,
    *,
    username: str,
    issuer_name: str = "TrustSafetyOS",
) -> str:
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    return totp.provisioning_uri(name=username, issuer_name=issuer_name)


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count: int = BACKUP_CODE_COUNT) -> list[str]:
    codes: list[str] = []
    for _ in range(count):
        raw = secrets.token_hex(BACKUP_CODE_LENGTH // 2)
        formatted = f"{raw[:4]}-{raw[4:]}"
        codes.append(formatted)
    return codes


def hash_backup_codes(codes: list[str]) -> list[str]:
    return [hashlib.sha256(code.encode()).hexdigest() for code in codes]


def verify_backup_code(code: str, hashed_codes: list[str]) -> tuple[bool, list[str]]:
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    if code_hash in hashed_codes:
        remaining = [h for h in hashed_codes if h != code_hash]
        return True, remaining
    return False, hashed_codes


def enable_mfa(
    secret: str,
    verification_code: str,
) -> tuple[bool, str | None]:
    if not verify_totp(secret, verification_code):
        return False, None
    return True, secret


def disable_mfa(
    secret: str,
    verification_code: str,
) -> tuple[bool, str | None]:
    if not verify_totp(secret, verification_code):
        return False, None
    return True, None
