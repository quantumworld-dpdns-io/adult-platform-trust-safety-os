"""Zero-knowledge identity verification without revealing PII."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


CURVE_ORDER = 2**256 - 189
PRIME_P = 2**256 - 2**32 - 977
GENERATOR_G = 2


@dataclass
class IdentityProof:
    commitment: int
    challenge: int
    response: int
    proof_type: str
    metadata: Dict[str, str]


@dataclass
class IdentityCommitment:
    commitment_hash: bytes
    public_key: int
    identity_commitment: int


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


def _compute_identity_commitment(pii_data: Dict[str, str], salt: bytes) -> int:
    hasher = hashlib.sha512()
    for key in sorted(pii_data.keys()):
        hasher.update(key.encode())
        hasher.update(pii_data[key].encode())
    hasher.update(salt)
    return int.from_bytes(hasher.digest()[:32], "big") % CURVE_ORDER


def generate_keypair() -> Tuple[int, int]:
    private_key = secrets.randbelow(CURVE_ORDER - 1) + 1
    public_key = _mod_pow(GENERATOR_G, private_key, PRIME_P)
    return private_key, public_key


def create_identity_commitment(
    private_key: int,
    public_key: int,
    pii_data: Dict[str, str],
    salt: bytes | None = None,
) -> IdentityCommitment:
    if salt is None:
        salt = secrets.token_bytes(32)

    identity_commitment = _compute_identity_commitment(pii_data, salt)
    commitment_hash = hashlib.sha256(
        identity_commitment.to_bytes(32, "big") + public_key.to_bytes(32, "big")
    ).digest()

    return IdentityCommitment(
        commitment_hash=commitment_hash,
        public_key=public_key,
        identity_commitment=identity_commitment,
    )


def prove_identity_without_pii(
    private_key: int,
    public_key: int,
    identity_commitment: IdentityCommitment,
    challenge_seed: bytes | None = None,
) -> IdentityProof:
    if challenge_seed is None:
        challenge_seed = secrets.token_bytes(32)

    nonce = secrets.randbelow(CURVE_ORDER - 1) + 1
    commitment = _mod_pow(GENERATOR_G, nonce, PRIME_P)

    challenge = _hash_to_int(
        commitment, public_key, identity_commitment.commitment_hash, challenge_seed
    )
    response = (nonce - challenge * private_key) % CURVE_ORDER

    return IdentityProof(
        commitment=commitment,
        challenge=challenge,
        response=response,
        proof_type="identity",
        metadata={
            "commitment_hash": identity_commitment.commitment_hash.hex(),
            "public_key": str(public_key),
        },
    )


def verify_identity_proof(
    proof: IdentityProof,
    identity_commitment: IdentityCommitment,
) -> bool:
    public_key = int(proof.metadata.get("public_key", 0))
    commitment_hash = bytes.fromhex(proof.metadata.get("commitment_hash", ""))

    if commitment_hash != identity_commitment.commitment_hash:
        return False

    challenge = _hash_to_int(
        proof.commitment, public_key, commitment_hash, proof.response.to_bytes(32, "big")
    )

    if challenge != proof.challenge:
        return False

    lhs = _mod_pow(GENERATOR_G, proof.response, PRIME_P)
    rhs_factor = _mod_pow(public_key, proof.challenge, PRIME_P)
    rhs = (proof.commitment * rhs_factor) % PRIME_P

    return lhs == rhs


def prove_membership_in_group(
    private_key: int,
    public_key: int,
    group_members: List[int],
    group_id: str,
) -> IdentityProof:
    nonce = secrets.randbelow(CURVE_ORDER - 1) + 1
    commitment = _mod_pow(GENERATOR_G, nonce, PRIME_P)

    group_set_hash = hashlib.sha256(
        "".join(str(m) for m in sorted(group_members)).encode()
    ).digest()

    challenge = _hash_to_int(commitment, public_key, group_set_hash, group_id.encode())
    response = (nonce - challenge * private_key) % CURVE_ORDER

    is_member = public_key in group_members

    return IdentityProof(
        commitment=commitment,
        challenge=challenge,
        response=response,
        proof_type="group_membership",
        metadata={
            "group_id": group_id,
            "is_member": str(is_member),
            "public_key": str(public_key),
        },
    )
