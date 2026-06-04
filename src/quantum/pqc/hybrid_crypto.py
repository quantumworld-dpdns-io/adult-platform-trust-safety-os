"""Hybrid classical + post-quantum cryptography."""

from __future__ import annotations

import hashlib
import hmac
import os
import struct
from dataclasses import dataclass
from typing import Tuple

from .key_encapsulation import (
    KyberEncapsulation,
    KyberKeyPair,
    decapsulate,
    encapsulate,
    generate_keypair,
)
from .digital_signature import (
    DilithiumKeyPair,
    DilithiumSignature,
    generate_keypair as dilithium_generate_keypair,
    sign as dilithium_sign,
    verify as dilithium_verify,
)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False


@dataclass
class HybridKeyPair:
    classical_private_key: bytes
    classical_public_key: bytes
    pqc_private_key: bytes
    pqc_public_key: bytes


@dataclass
class HybridEncapsulation:
    classical_ciphertext: bytes
    pqc_ciphertext: bytes
    shared_secret: bytes


@dataclass
class HybridSignature:
    classical_signature: bytes
    pqc_signature: bytes
    message: bytes


def hybrid_encrypt(
    plaintext: bytes,
    recipient_public_key: HybridKeyPair,
    associated_data: bytes = b"",
) -> HybridEncapsulation:
    if not AES_AVAILABLE:
        raise ImportError("cryptography package is required")

    kyber_ep = encapsulate(recipient_public_key.pqc_public_key)
    aes_key = hashlib.sha256(kyber_shared_secret(kyber_ep)).digest()
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

    return HybridEncapsulation(
        classical_ciphertext=nonce + ciphertext,
        pqc_ciphertext=kyber_ep.ciphertext,
        shared_secret=kyber_ep.shared_secret,
    )


def hybrid_decrypt(
    encapsulation: HybridEncapsulation,
    recipient_private_key: HybridKeyPair,
    associated_data: bytes = b"",
) -> bytes:
    if not AES_AVAILABLE:
        raise ImportError("cryptography package is required")

    shared_secret = decapsulate(
        encapsulation.pqc_ciphertext,
        recipient_private_key.pqc_private_key,
    )
    aes_key = hashlib.sha256(shared_secret).digest()
    nonce = encapsulation.classical_ciphertext[:12]
    ciphertext = encapsulation.classical_ciphertext[12:]
    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)


def hybrid_sign(
    message: bytes,
    sender_private_key: HybridKeyPair,
) -> HybridSignature:
    pqc_sig = dilithium_sign(message, sender_private_key.pqc_private_key)

    if ED25519_AVAILABLE:
        ed_private = Ed25519PrivateKey.from_private_bytes(sender_private_key.classical_private_key[:32])
        classical_sig = ed_private.sign(message)
    else:
        classical_sig = hmac.new(
            sender_private_key.classical_private_key[:32], message, hashlib.sha512
        ).digest()

    return HybridSignature(
        classical_signature=classical_sig,
        pqc_signature=pqc_sig.signature,
        message=message,
    )


def hybrid_verify(
    hybrid_sig: HybridSignature,
    sender_public_key: HybridKeyPair,
) -> bool:
    pqc_valid = dilithium_verify(
        hybrid_sig.message,
        hybrid_sig.pqc_signature,
        sender_public_key.pqc_public_key,
    )

    if not pqc_valid:
        return False

    if ED25519_AVAILABLE:
        try:
            ed_public = Ed25519PublicKey.from_public_bytes(sender_public_key.classical_public_key[:32])
            ed_public.verify(hybrid_sig.classical_signature, hybrid_sig.message)
            classical_valid = True
        except Exception:
            classical_valid = False
    else:
        expected = hmac.new(
            sender_public_key.classical_public_key[:32],
            hybrid_sig.message,
            hashlib.sha512,
        ).digest()
        classical_valid = hmac.compare_digest(hybrid_sig.classical_signature, expected)

    return classical_valid


def kyber_shared_secret(ep: KyberEncapsulation) -> bytes:
    return ep.shared_secret
