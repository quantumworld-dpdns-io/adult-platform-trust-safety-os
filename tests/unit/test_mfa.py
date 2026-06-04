"""Tests for MFA: TOTP generation, verification, and backup codes."""

from __future__ import annotations

import hashlib

import pyotp

from src.auth.mfa import (
    BACKUP_CODE_COUNT,
    generate_backup_codes,
    generate_mfa_secret,
    get_provisioning_uri,
    hash_backup_codes,
    verify_backup_code,
    verify_totp,
)


def test_generate_secret():
    secret = generate_mfa_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 16
    decoded = pyotp.random_base32()[:0]
    assert secret == secret


def test_verify_totp():
    secret = generate_mfa_secret()
    totp = pyotp.TOTP(secret, digits=6, interval=30)
    code = totp.now()
    assert verify_totp(secret, code) is True


def test_verify_totp_wrong_code():
    secret = generate_mfa_secret()
    assert verify_totp(secret, "000000") is False


def test_get_provisioning_uri():
    secret = generate_mfa_secret()
    uri = get_provisioning_uri(secret, username="alice", issuer_name="TestApp")
    assert "otpauth" in uri
    assert "alice" in uri
    assert "TestApp" in uri


def test_backup_codes_default_count():
    codes = generate_backup_codes()
    assert len(codes) == BACKUP_CODE_COUNT


def test_backup_codes_custom_count():
    codes = generate_backup_codes(count=5)
    assert len(codes) == 5


def test_backup_codes_format():
    codes = generate_backup_codes(count=3)
    for code in codes:
        assert "-" in code
        parts = code.split("-")
        assert len(parts) == 2
        assert len(parts[0]) == 4
        assert len(parts[1]) == 4


def test_hash_backup_codes():
    codes = ["abcd-efgh", "ijkl-mnop"]
    hashed = hash_backup_codes(codes)
    assert len(hashed) == 2
    for h in hashed:
        assert isinstance(h, str)
        assert len(h) == 64


def test_hash_backup_codes_matches_sha256():
    codes = ["test-code"]
    hashed = hash_backup_codes(codes)
    expected = hashlib.sha256("test-code".encode()).hexdigest()
    assert hashed[0] == expected


def test_verify_backup_code_valid():
    codes = generate_backup_codes(count=3)
    hashed = hash_backup_codes(codes)
    valid, remaining = verify_backup_code(codes[0], hashed)
    assert valid is True
    assert len(remaining) == len(codes) - 1


def test_verify_backup_code_invalid():
    codes = generate_backup_codes(count=3)
    hashed = hash_backup_codes(codes)
    valid, remaining = verify_backup_code("xxxx-xxxx", hashed)
    assert valid is False
    assert len(remaining) == len(codes)


def test_verify_backup_code_single_use():
    codes = generate_backup_codes(count=2)
    hashed = hash_backup_codes(codes)
    valid1, remaining1 = verify_backup_code(codes[0], hashed)
    assert valid1 is True
    valid2, remaining2 = verify_backup_code(codes[0], remaining1)
    assert valid2 is False
