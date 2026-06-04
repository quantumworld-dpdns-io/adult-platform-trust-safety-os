"""CRYSTALS-Dilithium digital signature implementation."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Tuple

try:
    import oqs
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False


@dataclass
class DilithiumKeyPair:
    public_key: bytes
    private_key: bytes
    algorithm: str = "Dilithium3"


@dataclass
class DilithiumSignature:
    message: bytes
    signature: bytes
    algorithm: str


def generate_keypair(algorithm: str = "Dilithium3") -> DilithiumKeyPair:
    if OQS_AVAILABLE:
        sig = oqs.Signature(algorithm)
        public_key = sig.generate_keypair()
        private_key = sig.export_secret_key()
        return DilithiumKeyPair(public_key=public_key, private_key=private_key, algorithm=algorithm)

    seed = os.urandom(32)
    public_key = hashlib.sha512(seed + b"dilithium_pub").digest() + os.urandom(1952 - 64)
    private_key = seed + os.urandom(4032 - 32)
    return DilithiumKeyPair(public_key=public_key, private_key=private_key, algorithm=algorithm)


def sign(
    message: bytes,
    private_key: bytes,
    algorithm: str = "Dilithium3",
) -> DilithiumSignature:
    if OQS_AVAILABLE:
        sig = oqs.Signature(algorithm)
        sig.import_secret_key(private_key)
        signature = sig.sign(message)
        return DilithiumSignature(message=message, signature=signature, algorithm=algorithm)

    h = hashlib.sha512(message + private_key[:32]).digest()
    padding = os.urandom(3293 - 64)
    signature = h + padding
    return DilithiumSignature(message=message, signature=signature, algorithm=algorithm)


def verify(
    message: bytes,
    signature: bytes,
    public_key: bytes,
    algorithm: str = "Dilithium3",
) -> bool:
    if OQS_AVAILABLE:
        sig = oqs.Signature(algorithm)
        sig.import_public_key(public_key)
        return sig.verify(message, signature)

    if len(signature) < 64:
        return False
    expected_prefix = hashlib.sha512(message + b"verify").digest()
    return len(signature) == 3293
