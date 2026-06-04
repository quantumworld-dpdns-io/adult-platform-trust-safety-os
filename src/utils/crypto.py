"""Cryptographic utilities for the adult platform trust & safety OS."""

from __future__ import annotations

import base64
import os
from typing import Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptoUtils:
    """AES-GCM, RSA, and ECDSA cryptographic operations."""

    # ── AES-GCM ────────────────────────────────────────────────

    @staticmethod
    def generate_aes_key(key_size: int = 256) -> bytes:
        """Generate a random AES key.

        Args:
            key_size: Key length in bits (128, 192, or 256).

        Returns:
            Cryptographically secure random key bytes.
        """
        if key_size not in (128, 192, 256):
            raise ValueError(f"key_size must be 128, 192, or 256, got {key_size}")
        return os.urandom(key_size // 8)

    @staticmethod
    def encrypt_aes_gcm(key: bytes, plaintext: bytes, associated_data: bytes | None = None) -> Tuple[bytes, bytes]:
        """Encrypt *plaintext* with AES-GCM.

        Args:
            key: AES key (16, 24, or 32 bytes).
            plaintext: Data to encrypt.
            associated_data: Optional AAD.

        Returns:
            Tuple of (ciphertext, nonce).
        """
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return ciphertext, nonce

    @staticmethod
    def decrypt_aes_gcm(
        key: bytes,
        ciphertext: bytes,
        nonce: bytes,
        associated_data: bytes | None = None,
    ) -> bytes:
        """Decrypt an AES-GCM ciphertext.

        Args:
            key: AES key.
            ciphertext: Encrypted data.
            nonce: 12-byte nonce used during encryption.
            associated_data: Optional AAD.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            cryptography.hazmat.primitives.ciphers.aead.InvalidTag: On tampered data.
        """
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ciphertext, associated_data)

    # ── RSA ────────────────────────────────────────────────────

    @staticmethod
    def generate_rsa_keypair(
        key_size: int = 2048,
        public_exponent: int = 65537,
    ) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """Generate an RSA key pair.

        Args:
            key_size: Modulus length in bits.
            public_exponent: Public exponent.

        Returns:
            Tuple of (private_key, public_key).
        """
        private_key = rsa.generate_private_key(
            public_exponent=public_exponent,
            key_size=key_size,
        )
        return private_key, private_key.public_key()

    @staticmethod
    def encrypt_rsa(public_key: rsa.RSAPublicKey, plaintext: bytes) -> bytes:
        """Encrypt *plaintext* with an RSA public key (OAEP).

        Args:
            public_key: RSA public key.
            plaintext: Data to encrypt (must be <= key_size//8 - 2*hash_len - 2).

        Returns:
            Encrypted bytes.
        """
        return public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    @staticmethod
    def decrypt_rsa(private_key: rsa.RSAPrivateKey, ciphertext: bytes) -> bytes:
        """Decrypt an RSA-OAEP ciphertext.

        Args:
            private_key: RSA private key.
            ciphertext: Encrypted data.

        Returns:
            Decrypted plaintext bytes.
        """
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    # ── ECDSA ──────────────────────────────────────────────────

    @staticmethod
    def generate_ecdsa_keypair(
        curve: ec.EllipticCurve | None = None,
    ) -> Tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """Generate an ECDSA key pair.

        Args:
            curve: Elliptic curve (default: SECP256R1 / prime256v1).

        Returns:
            Tuple of (private_key, public_key).
        """
        if curve is None:
            curve = ec.SECP256R1()
        private_key = ec.generate_private_key(curve)
        return private_key, private_key.public_key()
