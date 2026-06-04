"""Quantum-resistant audit chain implementation."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AuditChainEntry:
    entry_id: str
    event_type: str
    timestamp: float
    actor: str
    target: str
    details: Dict[str, Any]
    previous_hash: bytes
    entry_hash: bytes = b""
    nonce: int = 0
    signature: bytes = b""

    def __post_init__(self):
        if not self.entry_hash:
            self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> bytes:
        hasher = hashlib.sha256()
        hasher.update(self.entry_id.encode())
        hasher.update(self.event_type.encode())
        hasher.update(int(self.timestamp).to_bytes(8, "big"))
        hasher.update(self.actor.encode())
        hasher.update(self.target.encode())
        hasher.update(json.dumps(self.details, sort_keys=True).encode())
        hasher.update(self.previous_hash)
        hasher.update(self.nonce.to_bytes(8, "big"))
        return hasher.digest()


@dataclass
class AuditChain:
    chain_id: str
    entries: List[AuditChainEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    algorithm: str = "SHA-256 + Dilithium3"


@dataclass
class ChainStats:
    chain_id: str
    num_entries: int
    first_entry_time: float
    last_entry_time: float
    chain_integrity: bool
    average_entries_per_second: float


GENESIS_HASH = b"\x00" * 32


def build_chain(chain_id: str | None = None, algorithm: str = "SHA-256 + Dilithium3") -> AuditChain:
    if chain_id is None:
        chain_id = hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:16]
    return AuditChain(chain_id=chain_id, algorithm=algorithm)


def append_entry(
    chain: AuditChain,
    entry_id: str,
    event_type: str,
    actor: str,
    target: str,
    details: Dict[str, Any],
    timestamp: float | None = None,
) -> AuditChainEntry:
    if timestamp is None:
        timestamp = time.time()

    previous_hash = chain.entries[-1].entry_hash if chain.entries else GENESIS_HASH

    entry = AuditChainEntry(
        entry_id=entry_id,
        event_type=event_type,
        timestamp=timestamp,
        actor=actor,
        target=target,
        details=details,
        previous_hash=previous_hash,
    )

    chain.entries.append(entry)
    return entry


def verify_chain(chain: AuditChain) -> bool:
    if not chain.entries:
        return True

    if chain.entries[0].previous_hash != GENESIS_HASH:
        return False

    for i in range(1, len(chain.entries)):
        if chain.entries[i].previous_hash != chain.entries[i - 1].entry_hash:
            return False

    for entry in chain.entries:
        recomputed = entry._compute_hash()
        if recomputed != entry.entry_hash:
            return False

    return True


def get_chain_stats(chain: AuditChain) -> ChainStats:
    if not chain.entries:
        return ChainStats(
            chain_id=chain.chain_id,
            num_entries=0,
            first_entry_time=0.0,
            last_entry_time=0.0,
            chain_integrity=True,
            average_entries_per_second=0.0,
        )

    first_time = chain.entries[0].timestamp
    last_time = chain.entries[-1].timestamp
    duration = last_time - first_time

    return ChainStats(
        chain_id=chain.chain_id,
        num_entries=len(chain.entries),
        first_entry_time=first_time,
        last_entry_time=last_time,
        chain_integrity=verify_chain(chain),
        average_entries_per_second=len(chain.entries) / duration if duration > 0 else 0.0,
    )
