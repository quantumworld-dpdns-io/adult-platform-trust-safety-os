"""Security tests: audit chain integrity."""

from __future__ import annotations

import hashlib

import pytest

from src.quantum.audit.chain import (
    AuditChain,
    AuditChainEntry,
    GENESIS_HASH,
    append_entry,
    build_chain,
    get_chain_stats,
    verify_chain,
)


pytestmark = [pytest.mark.security]


class TestAuditChainIntegrity:
    def test_empty_chain_valid(self):
        chain = build_chain()
        assert verify_chain(chain) is True

    def test_single_entry_valid(self):
        chain = build_chain()
        entry = append_entry(
            chain,
            entry_id="e1",
            event_type="user.login",
            actor="user-1",
            target="session-1",
            details={"ip": "127.0.0.1"},
        )
        assert entry.previous_hash == GENESIS_HASH
        assert len(entry.entry_hash) == 32
        assert verify_chain(chain) is True

    def test_multiple_entries_valid(self):
        chain = build_chain()
        for i in range(5):
            append_entry(
                chain,
                entry_id=f"e{i}",
                event_type="test.event",
                actor=f"actor-{i}",
                target=f"target-{i}",
                details={"index": i},
            )
        assert verify_chain(chain) is True

    def test_chain_link_integrity(self):
        chain = build_chain()
        e1 = append_entry(chain, "e1", "event", "a", "t", {})
        e2 = append_entry(chain, "e2", "event", "a", "t", {})
        e3 = append_entry(chain, "e3", "event", "a", "t", {})

        assert e2.previous_hash == e1.entry_hash
        assert e3.previous_hash == e2.entry_hash
        assert chain.entries[0].previous_hash == GENESIS_HASH

    def test_tampered_entry_detected(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {"key": "value"})
        append_entry(chain, "e2", "event", "a", "t", {})

        chain.entries[0].details = {"key": "TAMPERED"}
        assert verify_chain(chain) is False

    def test_tampered_hash_detected(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {})
        original_hash = chain.entries[0].entry_hash
        chain.entries[0].entry_hash = b"\\x00" * 32
        assert verify_chain(chain) is False
        chain.entries[0].entry_hash = original_hash

    def test_tampered_previous_hash_detected(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {})
        append_entry(chain, "e2", "event", "a", "t", {})
        chain.entries[1].previous_hash = b"\\xff" * 32
        assert verify_chain(chain) is False

    def test_genesis_hash_correct(self):
        assert GENESIS_HASH == b"\\x00" * 32

    def test_first_entry_references_genesis(self):
        chain = build_chain()
        entry = append_entry(chain, "e1", "event", "a", "t", {})
        assert entry.previous_hash == GENESIS_HASH

    def test_chain_stats_empty(self):
        chain = build_chain()
        stats = get_chain_stats(chain)
        assert stats.num_entries == 0
        assert stats.chain_integrity is True
        assert stats.average_entries_per_second == 0.0

    def test_chain_stats_populated(self):
        chain = build_chain()
        for i in range(10):
            append_entry(chain, f"e{i}", "event", "a", "t", {"i": i})
        stats = get_chain_stats(chain)
        assert stats.num_entries == 10
        assert stats.chain_integrity is True
        assert stats.chain_id == chain.chain_id

    def test_chain_preserves_order(self):
        chain = build_chain()
        actors = ["alice", "bob", "charlie", "diana"]
        for actor in actors:
            append_entry(chain, f"e-{actor}", "login", actor, "session", {})

        chain_actors = [e.actor for e in chain.entries]
        assert chain_actors == actors

    def test_entry_hash_deterministic(self):
        chain = build_chain()
        entry = AuditChainEntry(
            entry_id="e1",
            event_type="test",
            timestamp=1000.0,
            actor="a",
            target="t",
            details={"k": "v"},
            previous_hash=GENESIS_HASH,
        )
        h1 = entry._compute_hash()
        h2 = entry._compute_hash()
        assert h1 == h2

    def test_different_entries_different_hashes(self):
        chain = build_chain()
        e1 = append_entry(chain, "e1", "event", "a", "t", {"key": "value1"})
        e2 = append_entry(chain, "e2", "event", "a", "t", {"key": "value2"})
        assert e1.entry_hash != e2.entry_hash

    def test_custom_chain_id(self):
        chain = build_chain(chain_id="my-custom-chain")
        assert chain.chain_id == "my-custom-chain"

    def test_custom_algorithm(self):
        chain = build_chain(algorithm="SHA-384 + Falcon-512")
        assert chain.algorithm == "SHA-384 + Falcon-512"
