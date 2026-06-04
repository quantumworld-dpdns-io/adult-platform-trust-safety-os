"""Verifiable Random Function (VRF) implementation."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Tuple


CURVE_ORDER = 2**256 - 189
PRIME_P = 2**256 - 2**32 - 977
GENERATOR_G = 2


@dataclass
class VRFKeypair:
    private_key: int
    public_key: int


@dataclass
class VRFEvaluation:
    input_hash: bytes
    output: bytes
    proof: bytes


def _mod_pow(base: int, exp: int, mod: int) -> int:
    result = 1
    base = base % mod
    while exp > 0:
        if exp % 2 == 1:
            result = (result * base) % mod
        exp >>= 1
        base = (base * base) % mod
    return result


def _hash_to_bytes(*args) -> bytes:
    hasher = hashlib.sha256()
    for arg in args:
        if isinstance(arg, int):
            hasher.update(arg.to_bytes(32, "big"))
        elif isinstance(arg, bytes):
            hasher.update(arg)
        else:
            hasher.update(str(arg).encode())
    return hasher.digest()


def generate_vrf_keypair() -> VRFKeypair:
    private_key = secrets.randbelow(CURVE_ORDER - 1) + 1
    public_key = _mod_pow(GENERATOR_G, private_key, PRIME_P)
    return VRFKeypair(private_key=private_key, public_key=public_key)


def evaluate_vrf(
    input_data: bytes,
    keypair: VRFKeypair,
) -> VRFEvaluation:
    input_hash = hashlib.sha256(input_data).digest()
    input_int = int.from_bytes(input_hash, "big") % CURVE_ORDER

    k = secrets.randbelow(CURVE_ORDER - 1) + 1
    gamma = _mod_pow(GENERATOR_G, k, PRIME_P)

    c_hash = hashlib.sha256()
    c_hash.update(input_hash)
    c_hash.update(gamma.to_bytes(32, "big"))
    c_hash.update(keypair.public_key.to_bytes(32, "big"))
    c = int.from_bytes(c_hash.digest(), "big") % CURVE_ORDER

    s = (k - c * keypair.private_key) % CURVE_ORDER

    drbg = hashlib.sha512()
    drbg.update(input_hash)
    drbg.update(gamma.to_bytes(32, "big"))
    drbg.update(c.to_bytes(32, "big"))
    drbg.update(s.to_bytes(32, "big"))
    output = drbg.digest()[:32]

    proof = gamma.to_bytes(32, "big") + c.to_bytes(32, "big") + s.to_bytes(32, "big")

    return VRFEvaluation(
        input_hash=input_hash,
        output=output,
        proof=proof,
    )


def verify_vrf_proof(
    input_data: bytes,
    evaluation: VRFEvaluation,
    public_key: int,
) -> bool:
    input_hash = hashlib.sha256(input_data).digest()

    if evaluation.input_hash != input_hash:
        return False

    if len(evaluation.proof) != 96:
        return False

    gamma = int.from_bytes(evaluation.proof[:32], "big")
    c = int.from_bytes(evaluation.proof[32:64], "big")
    s = int.from_bytes(evaluation.proof[64:96], "big")

    c_prime_hash = hashlib.sha256()
    c_prime_hash.update(input_hash)
    c_prime_hash.update(gamma.to_bytes(32, "big"))
    c_prime_hash.update(public_key.to_bytes(32, "big"))
    c_prime = int.from_bytes(c_prime_hash.digest(), "big") % CURVE_ORDER

    if c_prime != c:
        return False

    lhs = _mod_pow(GENERATOR_G, s, PRIME_P)
    rhs = (_mod_pow(public_key, c, PRIME_P) * gamma) % PRIME_P

    if lhs != rhs:
        return False

    drbg = hashlib.sha512()
    drbg.update(input_hash)
    drbg.update(gamma.to_bytes(32, "big"))
    drbg.update(c.to_bytes(32, "big"))
    drbg.update(s.to_bytes(32, "big"))
    expected_output = drbg.digest()[:32]

    return evaluation.output == expected_output
