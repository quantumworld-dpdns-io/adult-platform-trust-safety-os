"""Hashing and integrity utilities."""

from __future__ import annotations

import hashlib
import hmac
import struct

try:
    import blake3 as _blake3
except ImportError:  # pragma: no cover
    _blake3 = None

try:
    import argon2
except ImportError:  # pragma: no cover
    argon2 = None


class HashUtils:
    """SHA-256, BLAKE3, Argon2id, Merkle-leaf, and HMAC helpers."""

    # ── SHA-256 ────────────────────────────────────────────────

    @staticmethod
    def sha256_hash(data: bytes | str) -> str:
        """Return hex-encoded SHA-256 of *data*."""
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    # ── BLAKE3 ─────────────────────────────────────────────────

    @staticmethod
    def blake3_hash(data: bytes | str) -> str:
        """Return hex-encoded BLAKE3 of *data*.

        Raises:
            RuntimeError: If the ``blake3`` package is not installed.
        """
        if _blake3 is None:
            raise RuntimeError("blake3 package is not installed")
        if isinstance(data, str):
            data = data.encode("utf-8")
        return _blake3.blake3(data).hexdigest()

    # ── Argon2id ───────────────────────────────────────────────

    @staticmethod
    def argon2_hash(
        password: bytes | str,
        time_cost: int = 3,
        memory_cost: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> str:
        """Hash a password with Argon2id.

        Args:
            password: Input password.
            time_cost: Number of iterations.
            memory_cost: Memory usage in KiB.
            parallelism: Degree of parallelism.
            hash_len: Length of the hash in bytes.
            salt_len: Length of the random salt in bytes.

        Returns:
            Encoded Argon2id hash string (contains algorithm params + salt + hash).

        Raises:
            RuntimeError: If ``argon2-cffi`` is not installed.
        """
        if argon2 is None:
            raise RuntimeError("argon2-cffi package is not installed")
        if isinstance(password, str):
            password = password.encode("utf-8")
        ph = argon2.PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )
        return ph.hash(password)

    @staticmethod
    def argon2_verify(encoded: str, password: bytes | str) -> bool:
        """Verify a password against an Argon2id encoded hash.

        Args:
            encoded: Argon2id encoded hash string.
            password: Password to verify.

        Returns:
            ``True`` if verification succeeds, ``False`` otherwise.
        """
        if argon2 is None:
            raise RuntimeError("argon2-cffi package is not installed")
        if isinstance(password, str):
            password = password.encode("utf-8")
        ph = argon2.PasswordHasher()
        try:
            ph.verify(encoded, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
        except argon2.exceptions.InvalidHashError:
            return False

    # ── Merkle leaf ────────────────────────────────────────────

    @staticmethod
    def compute_merkle_leaf(data: bytes) -> bytes:
        """Compute a 32-byte Merkle leaf by double-hashing *data*.

        The leaf is ``SHA-256(SHA-256(data))`` following Bitcoin's leaf
        construction convention.
        """
        first = hashlib.sha256(data).digest()
        return hashlib.sha256(first).digest()

    # ── HMAC ───────────────────────────────────────────────────

    @staticmethod
    def compute_hmac(
        key: bytes | str,
        message: bytes | str,
        algorithm: str = "sha256",
    ) -> str:
        """Compute an HMAC and return the hex digest.

        Args:
            key: HMAC key.
            message: Message to authenticate.
            algorithm: Hash algorithm name (``sha256``, ``sha512``, ``sha384``, etc.).

        Returns:
            Hex-encoded HMAC digest.
        """
        if isinstance(key, str):
            key = key.encode("utf-8")
        if isinstance(message, str):
            message = message.encode("utf-8")
        alg = getattr(hashlib, algorithm, None)
        if alg is None:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        return hmac.new(key, message, alg).hexdigest()
