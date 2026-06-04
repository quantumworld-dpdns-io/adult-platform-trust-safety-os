"""Zero-knowledge age verification using Schnorr-like protocols."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Tuple


CURVE_ORDER = 2**256 - 189
PRIME_P = 2**256 - 2**32 - 977
GENERATOR_G = 2


@dataclass
class AgeProof:
    commitment: int
    challenge: int
    response: int
    proof_type: str
    metadata: dict


@dataclass
class AgeProofPublicInputs:
    public_key: int
    minimum_age: int | None = None
    maximum_age: int | None = None
    proof_type: str = ""


def _mod_pow(base: int, exp: int, mod: int) -> int:
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp = exp >> 1
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


def generate_keypair() -> Tuple[int, int]:
    private_key = secrets.randbelow(CURVE_ORDER - 1) + 1
    public_key = _mod_pow(GENERATOR_G, private_key, PRIME_P)
    return private_key, public_key


def prove_age_over(
    birth_date_hash: int,
    private_key: int,
    public_key: int,
    current_date_hash: int,
    minimum_age: int = 18,
) -> AgeProof:
    nonce = secrets.randbelow(CURVE_ORDER - 1) + 1
    commitment = _mod_pow(GENERATOR_G, nonce, PRIME_P)

    challenge = _hash_to_int(
        commitment, public_key, birth_date_hash, current_date_hash, minimum_age
    )

    response = (nonce - challenge * private_key) % CURVE_ORDER

    return AgeProof(
        commitment=commitment,
        challenge=challenge,
        response=response,
        proof_type="age_over",
        metadata={
            "minimum_age": minimum_age,
            "birth_date_hash": birth_date_hash,
            "current_date_hash": current_date_hash,
        },
    )


def prove_age_under(
    birth_date_hash: int,
    private_key: int,
    public_key: int,
    current_date_hash: int,
    maximum_age: int = 18,
) -> AgeProof:
    nonce = secrets.randbelow(CURVE_ORDER - 1) + 1
    commitment = _mod_pow(GENERATOR_G, nonce, PRIME_P)

    challenge = _hash_to_int(
        commitment, public_key, birth_date_hash, current_date_hash, maximum_age
    )

    response = (nonce + challenge * private_key) % CURVE_ORDER

    return AgeProof(
        commitment=commitment,
        challenge=challenge,
        response=response,
        proof_type="age_under",
        metadata={
            "maximum_age": maximum_age,
            "birth_date_hash": birth_date_hash,
            "current_date_hash": current_date_hash,
        },
    )


def prove_age_range(
    birth_date_hash: int,
    private_key: int,
    public_key: int,
    current_date_hash: int,
    min_age: int = 18,
    max_age: int = 65,
) -> AgeProof:
    proof_over = prove_age_over(
        birth_date_hash, private_key, public_key, current_date_hash, min_age
    )
    proof_under = prove_age_under(
        birth_date_hash, private_key, public_key, current_date_hash, max_age
    )

    combined_commitment = (proof_over.commitment * proof_under.commitment) % PRIME_P
    combined_challenge = _hash_to_int(combined_commitment, proof_over.challenge, proof_under.challenge)
    combined_response = (proof_over.response + proof_under.response) % CURVE_ORDER

    return AgeProof(
        commitment=combined_commitment,
        challenge=combined_challenge,
        response=combined_response,
        proof_type="age_range",
        metadata={
            "min_age": min_age,
            "max_age": max_age,
            "birth_date_hash": birth_date_hash,
            "current_date_hash": current_date_hash,
        },
    )


def verify_age_proof(
    proof: AgeProof,
    public_key: int,
) -> bool:
    challenge = _hash_to_int(
        proof.commitment, public_key, proof.metadata.get("birth_date_hash", 0),
        proof.metadata.get("current_date_hash", 0),
        proof.metadata.get("minimum_age", proof.metadata.get("maximum_age", 0)),
    )

    if challenge != proof.challenge:
        return False

    lhs = _mod_pow(GENERATOR_G, proof.response, PRIME_P)
    rhs_factor = _mod_pow(public_key, proof.challenge, PRIME_P)
    rhs = (proof.commitment * rhs_factor) % PRIME_P

    return lhs == rhs
