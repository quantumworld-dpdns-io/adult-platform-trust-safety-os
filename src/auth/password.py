"""Password hashing and strength checking using argon2-cffi."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from typing import Literal

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, VerificationError

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def check_password_strength(password: str) -> dict[str, Any]:
    result: dict[str, Any] = {"score": 0, "issues": [], "passed": []}

    if len(password) >= 12:
        result["score"] += 2
        result["passed"].append("length_12")
    elif len(password) >= 8:
        result["score"] += 1
        result["passed"].append("length_8")
    else:
        result["issues"].append("too_short")

    if any(c.isupper() for c in password):
        result["score"] += 1
        result["passed"].append("uppercase")
    else:
        result["issues"].append("no_uppercase")

    if any(c.islower() for c in password):
        result["score"] += 1
        result["passed"].append("lowercase")
    else:
        result["issues"].append("no_lowercase")

    if any(c.isdigit() for c in password):
        result["score"] += 1
        result["passed"].append("digit")
    else:
        result["issues"].append("no_digit")

    special = set(string.punctuation)
    if any(c in special for c in password):
        result["score"] += 1
        result["passed"].append("special_char")
    else:
        result["issues"].append("no_special_char")

    if len(set(password)) >= len(password) * 0.7:
        result["score"] += 1
        result["passed"].append("diversity")
    else:
        result["issues"].append("low_diversity")

    common = ["password", "123456", "qwerty", "letmein", "admin", "trust", "safety"]
    if password.lower() in common:
        result["score"] = max(0, result["score"] - 3)
        result["issues"].append("common_password")

    if result["score"] >= 5:
        result["strength"] = "strong"
    elif result["score"] >= 3:
        result["strength"] = "medium"
    else:
        result["strength"] = "weak"

    return result


def rotate_pepper(current_hash: str, new_pepper: str, old_pepper: str) -> str:
    if not verify_password(new_pepper, current_hash):
        raise ValueError("Pepper verification failed")
    return hash_password(new_pepper)
