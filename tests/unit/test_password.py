"""Tests for password hashing and strength checking."""

from __future__ import annotations

import pytest

from src.auth.password import check_password_strength, hash_password, verify_password


def test_hash_password():
    hashed = hash_password("SecureP@ssw0rd!")
    assert isinstance(hashed, str)
    assert hashed.startswith("$argon2")


def test_verify_correct_password():
    password = "MyStr0ng!Pass"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_verify_wrong_password():
    password = "MyStr0ng!Pass"
    hashed = hash_password(password)
    assert verify_password("WrongPassword1!", hashed) is False


def test_verify_empty_password():
    hashed = hash_password("RealPassword1!")
    assert verify_password("", hashed) is False


def test_password_strength_strong():
    result = check_password_strength("V3ry$tr0ng!Passwrd")
    assert result["strength"] == "strong"
    assert result["score"] >= 5
    assert "length_12" in result["passed"]
    assert "uppercase" in result["passed"]
    assert "lowercase" in result["passed"]
    assert "digit" in result["passed"]
    assert "special_char" in result["passed"]


def test_password_strength_weak():
    result = check_password_strength("abc")
    assert result["strength"] == "weak"
    assert result["score"] < 3
    assert "too_short" in result["issues"]
    assert "no_uppercase" in result["issues"]
    assert "no_digit" in result["issues"]
    assert "no_special_char" in result["issues"]


def test_password_strength_medium():
    result = check_password_strength("Abc12")
    assert result["strength"] == "medium"
    assert 3 <= result["score"] < 5


def test_password_strength_common_password():
    result = check_password_strength("password")
    assert "common_password" in result["issues"]
    assert result["strength"] == "weak"


def test_password_strength_no_uppercase():
    result = check_password_strength("lowercase1!")
    assert "no_uppercase" in result["issues"]


def test_password_strength_no_lowercase():
    result = check_password_strength("UPPERCASE1!")
    assert "no_lowercase" in result["issues"]


def test_password_strength_no_digit():
    result = check_password_strength("NoDigitsHere!")
    assert "no_digit" in result["issues"]


def test_password_strength_no_special():
    result = check_password_strength("NoSpecialChars1")
    assert "no_special_char" in result["issues"]


def test_password_strength_diversity():
    result = check_password_strength("aaaaaaaaaaaa1!")
    assert "low_diversity" in result["issues"]


def test_password_strength_score_range():
    for pwd in ["a", "Ab1!", "Abc123!@#", "V3ry$tr0ng!Pass", "password"]:
        result = check_password_strength(pwd)
        assert 0 <= result["score"] <= 7
        assert result["strength"] in ("weak", "medium", "strong")
