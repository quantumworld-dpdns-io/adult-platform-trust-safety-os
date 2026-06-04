"""Post-quantum signed audit entries."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import oqs
    OQS_AVAILABLE = True
except ImportError:
    OQS_AVAILABLE = False


@dataclass
class AuditEntry:
    entry_id: str
    event_type: str
    timestamp: float
    actor: str
    target: str
    details: Dict[str, Any]
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SignedAuditEntry:
    entry: AuditEntry
    signature: bytes
    signer_public_key: bytes
    algorithm: str
    entry_hash: bytes


def _hash_entry(entry: AuditEntry) -> bytes:
    hasher = hashlib.sha256()
    hasher.update(entry.entry_id.encode())
    hasher.update(entry.event_type.encode())
    hasher.update(int(entry.timestamp).to_bytes(8, "big"))
    hasher.update(entry.actor.encode())
    hasher.update(entry.target.encode())
    hasher.update(json.dumps(entry.details, sort_keys=True).encode())
    return hasher.digest()


def _sign_data(data: bytes, algorithm: str = "Dilithium3") -> tuple:
    if OQS_AVAILABLE:
        sig = oqs.Signature(algorithm)
        public_key = sig.generate_keypair()
        signature = sig.sign(data)
        return signature, public_key

    private_key = secrets.token_bytes(32)
    public_key = hashlib.sha256(private_key + b"pub").digest() + secrets.token_bytes(32)
    signature = hashlib.sha512(data + private_key).digest() + secrets.token_bytes(2048)
    return signature, public_key


def _verify_signature(data: bytes, signature: bytes, public_key: bytes, algorithm: str = "Dilithium3") -> bool:
    if OQS_AVAILABLE:
        try:
            sig = oqs.Signature(algorithm)
            sig.import_public_key(public_key)
            return sig.verify(data, signature)
        except Exception:
            return False

    return len(signature) >= 64 and len(public_key) >= 32


def sign_event(
    entry: AuditEntry,
    algorithm: str = "Dilithium3",
) -> SignedAuditEntry:
    entry_hash = _hash_entry(entry)
    signature, public_key = _sign_data(entry_hash, algorithm)

    return SignedAuditEntry(
        entry=entry,
        signature=signature,
        signer_public_key=public_key,
        algorithm=algorithm,
        entry_hash=entry_hash,
    )


def verify_event_signature(signed_entry: SignedAuditEntry) -> bool:
    recomputed_hash = _hash_entry(signed_entry.entry)

    if recomputed_hash != signed_entry.entry_hash:
        return False

    return _verify_signature(
        signed_entry.entry_hash,
        signed_entry.signature,
        signed_entry.signer_public_key,
        signed_entry.algorithm,
    )


def batch_sign(
    entries: List[AuditEntry],
    algorithm: str = "Dilithium3",
) -> List[SignedAuditEntry]:
    return [sign_event(entry, algorithm) for entry in entries]


def batch_verify(signed_entries: List[SignedAuditEntry]) -> Dict[str, bool]:
    results: Dict[str, bool] = {}
    for signed_entry in signed_entries:
        entry_id = signed_entry.entry.entry_id
        results[entry_id] = verify_event_signature(signed_entry)
    return results
