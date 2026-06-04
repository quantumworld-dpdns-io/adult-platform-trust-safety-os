"""Quantum audit chain tests."""

from __future__ import annotations

import time

import pytest

from src.quantum.audit.chain import (
    AuditChain,
    AuditChainEntry,
    GENESIS_HASH,
    ChainStats,
    append_entry,
    build_chain,
    get_chain_stats,
    verify_chain,
)


pytestmark = [pytest.mark.quantum]


class TestAuditChainBuild:
    def test_build_default_chain(self):
        chain = build_chain()
        assert isinstance(chain, AuditChain)
        assert chain.chain_id is not None
        assert len(chain.chain_id) == 16
        assert chain.algorithm == "SHA-256 + Dilithium3"
        assert chain.entries == []

    def test_build_custom_chain_id(self):
        chain = build_chain(chain_id="my-chain-123")
        assert chain.chain_id == "my-chain-123"

    def test_build_custom_algorithm(self):
        chain = build_chain(algorithm="Kyber + Dilithium5")
        assert chain.algorithm == "Kyber + Dilithium5"

    def test_build_unique_chain_ids(self):
        c1 = build_chain()
        c2 = build_chain()
        assert c1.chain_id != c2.chain_id


class TestAuditChainAppend:
    def test_append_single_entry(self):
        chain = build_chain()
        entry = append_entry(chain, "e1", "user.login", "user-1", "session-1", {"ip": "1.2.3.4"})
        assert entry.entry_id == "e1"
        assert entry.event_type == "user.login"
        assert entry.actor == "user-1"
        assert entry.target == "session-1"
        assert entry.previous_hash == GENESIS_HASH
        assert len(chain.entries) == 1

    def test_append_multiple_entries(self):
        chain = build_chain()
        for i in range(10):
            append_entry(chain, f"e{i}", f"event.{i}", f"actor-{i}", f"target-{i}", {"i": i})
        assert len(chain.entries) == 10

    def test_append_links_entries(self):
        chain = build_chain()
        e1 = append_entry(chain, "e1", "event", "a", "t", {})
        e2 = append_entry(chain, "e2", "event", "a", "t", {})
        e3 = append_entry(chain, "e3", "event", "a", "t", {})
        assert e2.previous_hash == e1.entry_hash
        assert e3.previous_hash == e2.entry_hash

    def test_append_with_custom_timestamp(self):
        chain = build_chain()
        ts = 1700000000.0
        entry = append_entry(chain, "e1", "event", "a", "t", {}, timestamp=ts)
        assert entry.timestamp == ts

    def test_entry_auto_computes_hash(self):
        chain = build_chain()
        entry = append_entry(chain, "e1", "event", "a", "t", {"key": "value"})
        assert len(entry.entry_hash) == 32
        assert entry.entry_hash != b""

    def test_genesis_hash_constant(self):
        assert GENESIS_HASH == b"\x00" * 32


class TestAuditChainVerify:
    def test_verify_empty_chain(self):
        chain = build_chain()
        assert verify_chain(chain) is True

    def test_verify_valid_chain(self):
        chain = build_chain()
        for i in range(5):
            append_entry(chain, f"e{i}", "event", "a", "t", {"i": i})
        assert verify_chain(chain) is True

    def test_verify_tampered_details(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {"key": "original"})
        chain.entries[0].details = {"key": "tampered"}
        assert verify_chain(chain) is False

    def test_verify_tampered_hash(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {})
        chain.entries[0].entry_hash = b"\xff" * 32
        assert verify_chain(chain) is False

    def test_verify_tampered_previous_hash(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {})
        append_entry(chain, "e2", "event", "a", "t", {})
        chain.entries[1].previous_hash = b"\xff" * 32
        assert verify_chain(chain) is False

    def test_verify_tampered_event_type(self):
        chain = build_chain()
        append_entry(chain, "e1", "user.login", "a", "t", {})
        chain.entries[0].event_type = "user.logout"
        assert verify_chain(chain) is False

    def test_verify_tampered_actor(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "alice", "t", {})
        chain.entries[0].actor = "eve"
        assert verify_chain(chain) is False

    def test_verify_after_each_append(self):
        chain = build_chain()
        for i in range(20):
            append_entry(chain, f"e{i}", f"event.{i}", f"actor-{i}", f"target-{i}", {"i": i})
            assert verify_chain(chain) is True


class TestAuditChainStats:
    def test_stats_empty_chain(self):
        chain = build_chain()
        stats = get_chain_stats(chain)
        assert isinstance(stats, ChainStats)
        assert stats.num_entries == 0
        assert stats.chain_integrity is True
        assert stats.average_entries_per_second == 0.0

    def test_stats_populated_chain(self):
        chain = build_chain()
        for i in range(10):
            append_entry(chain, f"e{i}", "event", "a", "t", {"i": i})
        stats = get_chain_stats(chain)
        assert stats.num_entries == 10
        assert stats.chain_integrity is True
        assert stats.chain_id == chain.chain_id
        assert stats.first_entry_time > 0
        assert stats.last_entry_time > 0

    def test_stats_tampered_chain(self):
        chain = build_chain()
        append_entry(chain, "e1", "event", "a", "t", {})
        append_entry(chain, "e2", "event", "a", "t", {})
        chain.entries[0].details = {"tampered": True}
        stats = get_chain_stats(chain)
        assert stats.chain_integrity is False

    def test_stats_average_rate(self):
        chain = build_chain()
        now = time.time()
        for i in range(5):
            append_entry(chain, f"e{i}", "event", "a", "t", {}, timestamp=now + i)
        stats = get_chain_stats(chain)
        assert stats.average_entries_per_second > 0


class TestAuditChainEntry:
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
        e1 = append_entry(chain, "e1", "event", "a", "t", {"key": "val1"})
        e2 = append_entry(chain, "e2", "event", "a", "t", {"key": "val2"})
        assert e1.entry_hash != e2.entry_hash

    def test_entry_post_init_computes_hash(self):
        chain = build_chain()
        entry = AuditChainEntry(
            entry_id="e1",
            event_type="test",
            timestamp=1000.0,
            actor="a",
            target="t",
            details={},
            previous_hash=GENESIS_HASH,
        )
        assert len(entry.entry_hash) == 32

    def test_entry_fields_preserved(self):
        chain = build_chain()
        entry = append_entry(
            chain,
            entry_id="unique-id",
            event_type="content.approved",
            actor="moderator-1",
            target="content-42",
            details={"reason": "safe"},
        )
        assert entry.entry_id == "unique-id"
        assert entry.event_type == "content.approved"
        assert entry.actor == "moderator-1"
        assert entry.target == "content-42"
        assert entry.details == {"reason": "safe"}
