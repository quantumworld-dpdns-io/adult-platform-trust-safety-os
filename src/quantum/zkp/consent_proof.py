"""Zero-knowledge consent verification protocol."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


CURVE_ORDER = 2**256 - 189
PRIME_P = 2**256 - 2**32 - 977
GENERATOR_G = 2


@dataclass
class ConsentProof:
    commitment: int
    challenge: int
    response: int
    consent_type: str
    consent_status: str
    timestamp_hash: bytes
    metadata: Dict[str, str]


@dataclass
class ConsentRecord:
    consent_id: str
    consent_type: str
    granted: bool
    timestamp: int
    consent_hash: bytes


def _mod_pow(base: int, exp: int, mod: int) -> int:
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp >>= 1
        base = (base * base) % mod
    return result


def _hash_to_int(*args) -> int:
    hasher = hashlib.sha256()
    for arg in args:
        if isinstance(arg, int):
            hasher.update(arg.to_bytes(32, "big"))
        elif isinstance(arg, bytes):
            hasher.update(arg)
        else:
            hasher.update(str(arg).encode())
    return int.from_bytes(hasher.digest(), "big") % CURVE_ORDER


def _compute_consent_hash(consent_id: str, consent_type: str, granted: bool, timestamp: int) -> bytes:
    hasher = hashlib.sha256()
    hasher.update(consent_id.encode())
    hasher.update(consent_type.encode())
    hasher.update(b"\x01" if granted else b"\x00")
    hasher.update(timestamp.to_bytes(8, "big"))
    return hasher.digest()


def generate_keypair() -> Tuple[int, int]:
    private_key = secrets.randbelow(CURVE_ORDER - 1) + 1
    public_key = _mod_pow(GENERATOR_G, private_key, PRIME_P)
    return private_key, public_key


def prove_consent_given(
    consent_id: str,
    consent_type: str,
    private_key: int,
    public_key: int,
    timestamp: int,
) -> ConsentProof:
    consent_hash = _compute_consent_hash(consent_id, consent_type, True, timestamp)

    nonce = secrets.randbelow(CURVE_ORDER - 1) + 1
    commitment = _mod_pow(GENERATOR_G, nonce, PRIME_P)

    challenge = _hash_to_int(commitment, public_key, consent_hash, b"consent_given")
    response = (nonce - challenge * private_key) % CURVE_ORDER

    timestamp_hash = hashlib.sha256(timestamp.to_bytes(8, "big")).digest()

    return ConsentProof(
        commitment=commitment,
        challenge=challenge,
        response=response,
        consent_type=consent_type,
        consent_status="granted",
        timestamp_hash=timestamp_hash,
        metadata={
            "consent_id": consent_id,
            "consent_hash": consent_hash.hex(),
        },
    )


def prove_consent_withdrawn(
    consent_id: str,
    consent_type: str,
    private_key: int,
    public_key: int,
    timestamp: int,
) -> ConsentProof:
    consent_hash = _compute_consent_hash(consent_id, consent_type, False, timestamp)

    nonce = secrets.randbelow(CURVE_ORDER - 1) + 1
    commitment = _mod_pow(GENERATOR_G, nonce, PRIME_P)

    challenge = _hash_to_int(commitment, public_key, consent_hash, b"consent_withdrawn")
    response = (nonce + challenge * private_key) % CURVE_ORDER

    timestamp_hash = hashlib.sha256(timestamp.to_bytes(8, "big")).digest()

    return ConsentProof(
        commitment=commitment,
        challenge=challenge,
        response=response,
        consent_type=consent_type,
        consent_status="withdrawn",
        timestamp_hash=timestamp_hash,
        metadata={
            "consent_id": consent_id,
            "consent_hash": consent_hash.hex(),
        },
    )


def verify_consent_proof(
    proof: ConsentProof,
    public_key: int,
) -> bool:
    if proof.consent_status not in ("granted", "withdrawn"):
        return False

    label = b"consent_given" if proof.consent_status == "granted" else b"consent_withdrawn"

    challenge = _hash_to_int(
        proof.commitment, public_key,
        bytes.fromhex(proof.metadata.get("consent_hash", "")),
        label,
    )

    if challenge != proof.challenge:
        return False

    if proof.consent_status == "granted":
        lhs = _mod_pow(GENERATOR_G, proof.response, PRIME_P)
        rhs_factor = _mod_pow(public_key, proof.challenge, PRIME_P)
        rhs = (proof.commitment * rhs_factor) % PRIME_P
    else:
        lhs = _mod_pow(GENERATOR_G, proof.response, PRIME_P)
        rhs_factor = _mod_pow(public_key, proof.challenge, PRIME_P)
        rhs = (proof.commitment * _mod_pow(rhs_factor, CURVE_ORDER - 1, PRIME_P)) % PRIME_P

    return lhs == rhs
