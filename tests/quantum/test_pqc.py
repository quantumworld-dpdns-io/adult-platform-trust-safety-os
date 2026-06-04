"""PQC tests: Kyber key encapsulation, Dilithium digital signature."""

from __future__ import annotations

import pytest

from src.quantum.pqc.key_encapsulation import (
    KyberEncapsulation,
    KyberKeyPair,
    decapsulate,
    encapsulate,
    generate_keypair,
)
from src.quantum.pqc.digital_signature import (
    DilithiumKeyPair,
    DilithiumSignature,
    generate_keypair as generate_dilithium_keypair,
    sign,
    verify,
)


pytestmark = [pytest.mark.quantum]


class TestKyberKeyEncapsulation:
    def test_generate_keypair(self):
        kp = generate_keypair()
        assert isinstance(kp, KyberKeyPair)
        assert len(kp.public_key) > 0
        assert len(kp.private_key) > 0
        assert kp.algorithm == "Kyber768"

    def test_generate_keypair_custom_algorithm(self):
        kp = generate_keypair(algorithm="Kyber768")
        assert kp.algorithm == "Kyber768"

    def test_encapsulate(self):
        kp = generate_keypair()
        enc = encapsulate(kp.public_key)
        assert isinstance(enc, KyberEncapsulation)
        assert len(enc.ciphertext) > 0
        assert len(enc.shared_secret) > 0

    def test_decapsulate(self):
        kp = generate_keypair()
        enc = encapsulate(kp.public_key)
        ss = decapsulate(enc.ciphertext, kp.private_key)
        assert len(ss) > 0

    def test_encapsulate_different_ciphertexts(self):
        kp = generate_keypair()
        enc1 = encapsulate(kp.public_key)
        enc2 = encapsulate(kp.public_key)
        assert enc1.ciphertext != enc2.ciphertext

    def test_shared_secret_nonzero(self):
        kp = generate_keypair()
        enc = encapsulate(kp.public_key)
        assert enc.shared_secret != b"\x00" * len(enc.shared_secret)

    def test_keypair_sizes(self):
        kp = generate_keypair()
        assert len(kp.public_key) >= 64
        assert len(kp.private_key) >= 64


class TestDilithiumSignature:
    def test_generate_keypair(self):
        kp = generate_dilithium_keypair()
        assert isinstance(kp, DilithiumKeyPair)
        assert len(kp.public_key) > 0
        assert len(kp.private_key) > 0
        assert kp.algorithm == "Dilithium3"

    def test_sign(self):
        kp = generate_dilithium_keypair()
        message = b"test message for signing"
        sig = sign(message, kp.private_key)
        assert isinstance(sig, DilithiumSignature)
        assert sig.message == message
        assert len(sig.signature) > 0

    def test_verify_valid(self):
        kp = generate_dilithium_keypair()
        message = b"verify this message"
        sig = sign(message, kp.private_key)
        assert verify(message, sig.signature, kp.public_key) is True

    def test_verify_wrong_message(self):
        kp = generate_dilithium_keypair()
        message = b"original message"
        sig = sign(message, kp.private_key)
        assert verify(b"wrong message", sig.signature, kp.public_key) is False

    def test_verify_wrong_public_key(self):
        kp1 = generate_dilithium_keypair()
        kp2 = generate_dilithium_keypair()
        message = b"test message"
        sig = sign(message, kp1.private_key)
        assert verify(message, sig.signature, kp2.public_key) is False

    def test_verify_tampered_signature(self):
        kp = generate_dilithium_keypair()
        message = b"test message"
        sig = sign(message, kp.private_key)
        tampered = bytearray(sig.signature)
        tampered[0] ^= 0xFF
        assert verify(message, bytes(tampered), kp.public_key) is False

    def test_sign_deterministic_same_key(self):
        kp = generate_dilithium_keypair()
        message = b"deterministic test"
        sig1 = sign(message, kp.private_key)
        sig2 = sign(message, kp.private_key)
        assert sig1.signature == sig2.signature

    def test_different_messages_different_signatures(self):
        kp = generate_dilithium_keypair()
        sig1 = sign(b"message 1", kp.private_key)
        sig2 = sign(b"message 2", kp.private_key)
        assert sig1.signature != sig2.signature

    def test_verify_empty_signature(self):
        kp = generate_dilithium_keypair()
        assert verify(b"test", b"", kp.public_key) is False
