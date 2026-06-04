"""Tests for hashing utilities: SHA-256, BLAKE3, Argon2, HMAC."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from src.utils.hashing import HashUtils


def test_sha256_bytes():
    result = HashUtils.sha256_hash(b"hello")
    assert isinstance(result, str)
    assert len(result) == 64
    expected = hashlib.sha256(b"hello").hexdigest()
    assert result == expected


def test_sha256_string():
    result = HashUtils.sha256_hash("hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert result == expected


def test_sha256_empty():
    result = HashUtils.sha256_hash(b"")
    expected = hashlib.sha256(b"").hexdigest()
    assert result == expected


def test_blake3_hash():
    result = HashUtils.blake3_hash(b"test data")
    assert isinstance(result, str)
    assert len(result) == 64


def test_blake3_string():
    result = HashUtils.blake3_hash("test data")
    assert isinstance(result, str)


def test_blake3_empty():
    result = HashUtils.blake3_hash(b"")
    assert isinstance(result, str)
    assert len(result) == 64


def test_blake3_deterministic():
    a = HashUtils.blake3_hash(b"deterministic")
    b = HashUtils.blake3_hash(b"deterministic")
    assert a == b


def test_argon2_hash():
    result = HashUtils.argon2_hash("password123")
    assert isinstance(result, str)
    assert result.startswith("$argon2")


def test_argon2_verify_correct():
    h = HashUtils.argon2_hash("correct_password")
    assert HashUtils.argon2_verify(h, "correct_password") is True


def test_argon2_verify_wrong():
    h = HashUtils.argon2_hash("correct_password")
    assert HashUtils.argon2_verify(h, "wrong_password") is False


def test_argon2_verify_empty():
    h = HashUtils.argon2_hash("password")
    assert HashUtils.argon2_verify(h, "") is False


def test_argon2_custom_params():
    h = HashUtils.argon2_hash(
        "test",
        time_cost=2,
        memory_cost=32768,
        parallelism=2,
        hash_len=16,
        salt_len=8,
    )
    assert isinstance(h, str)
    assert HashUtils.argon2_verify(h, "test") is True


def test_compute_hmac_sha256():
    result = HashUtils.compute_hmac("secret", "message")
    assert isinstance(result, str)
    assert len(result) == 64


def test_compute_hmac_deterministic():
    a = HashUtils.compute_hmac("key", "data")
    b = HashUtils.compute_hmac("key", "data")
    assert a == b


def test_compute_hmac_different_keys():
    a = HashUtils.compute_hmac("key1", "message")
    b = HashUtils.compute_hmac("key2", "message")
    assert a != b


def test_compute_hmac_bytes():
    result = HashUtils.compute_hmac(b"secret", b"message")
    assert isinstance(result, str)
    expected = hmac.new(b"secret", b"message", hashlib.sha256).hexdigest()
    assert result == expected


def test_compute_hmac_sha512():
    result = HashUtils.compute_hmac("key", "message", algorithm="sha512")
    assert isinstance(result, str)
    assert len(result) == 128


def test_compute_hmac_invalid_algorithm():
    with pytest.raises(ValueError, match="Unsupported hash algorithm"):
        HashUtils.compute_hmac("key", "message", algorithm="invalid")


def test_compute_merkle_leaf():
    data = b"test leaf data"
    leaf = HashUtils.compute_merkle_leaf(data)
    assert len(leaf) == 32
    first = hashlib.sha256(data).digest()
    expected = hashlib.sha256(first).digest()
    assert leaf == expected


def test_compute_merkle_leaf_deterministic():
    a = HashUtils.compute_merkle_leaf(b"data")
    b = HashUtils.compute_merkle_leaf(b"data")
    assert a == b


def test_compute_merkle_leaf_different():
    a = HashUtils.compute_merkle_leaf(b"data1")
    b = HashUtils.compute_merkle_leaf(b"data2")
    assert a != b
