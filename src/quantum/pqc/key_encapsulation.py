"""CRYSTALS-Kyber Key Encapsulation Mechanism with fallback mock."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from typing import Tuple

try:
    import oqs
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False


@dataclass
class KyberKeyPair:
    public_key: bytes
    private_key: bytes
    algorithm: str = "Kyber768"


@dataclass
class KyberEncapsulation:
    ciphertext: bytes
    shared_secret: bytes


def generate_keypair(algorithm: str = "Kyber768") -> KyberKeyPair:
    if OQS_AVAILABLE:
        kem = oqs.KeyEncapsulation(algorithm)
        public_key = kem.generate_keypair()
        private_key = kem.export_secret_key()
        return KyberKeyPair(public_key=public_key, private_key=private_key, algorithm=algorithm)

    seed = os.urandom(32)
    public_key = hashlib.sha512(seed + b"pub").digest() + os.urandom(1184 - 64)
    private_key = hashlib.sha512(seed + b"priv").digest() + os.urandom(2400 - 64)
    return KyberKeyPair(public_key=public_key, private_key=private_key, algorithm=algorithm)


def encapsulate(public_key: bytes, algorithm: str = "Kyber768") -> KyberEncapsulation:
    if OQS_AVAILABLE:
        kem = oqs.KeyEncapsulation(algorithm)
        ciphertext, shared_secret = kem.encap_secret(public_key)
        return KyberEncapsulation(ciphertext=ciphertext, shared_secret=shared_secret)

    randomness = os.urandom(32)
    ciphertext = hashlib.sha256(public_key[:64] + randomness).digest() + os.urandom(1088 - 32)
    shared_secret = hashlib.sha256(ciphertext[:32] + randomness + b"ss").digest()
    return KyberEncapsulation(ciphertext=ciphertext, shared_secret=shared_secret)


def decapsulate(ciphertext: bytes, private_key: bytes, algorithm: str = "Kyber768") -> bytes:
    if OQS_AVAILABLE:
        kem = oqs.KeyEncapsulation(algorithm)
        kem.import_secret_key(private_key)
        shared_secret = kem.decap_secret(ciphertext)
        return shared_secret

    shared_secret = hashlib.sha256(ciphertext[:32] + private_key[:32] + b"ss").digest()
    return shared_secret
