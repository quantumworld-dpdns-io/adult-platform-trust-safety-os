"""Merkle tree for tamper-evident audit log chaining."""

from __future__ import annotations

import hashlib
from typing import Sequence


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _hash_pair(left: bytes, right: bytes) -> bytes:
    return _sha256(left + right)


class MerkleTree:
    """Incremental Merkle tree backed by SHA-256.

    Leaves are hashed with a domain separator ``0x00``; internal nodes with ``0x01``
    to prevent second-pre-image attacks.
    """

    LEAF_PREFIX = b"\x00"
    NODE_PREFIX = b"\x01"

    def __init__(self) -> None:
        self._leaves: list[bytes] = []
        self._tree: list[list[bytes]] = []

    def _hash_leaf(self, data: bytes) -> bytes:
        return _sha256(self.LEAF_PREFIX + data)

    def _hash_node(self, left: bytes, right: bytes) -> bytes:
        return _sha256(self.NODE_PREFIX + left + right)

    def build_tree(self) -> None:
        """Rebuild the full tree from the current leaf set."""
        if not self._leaves:
            self._tree = []
            return

        current_level = list(self._leaves)
        self._tree = [current_level]

        while len(current_level) > 1:
            next_level: list[bytes] = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                next_level.append(self._hash_node(left, right))
            self._tree.append(next_level)
            current_level = next_level

    def get_root(self) -> bytes | None:
        """Return the current Merkle root, or ``None`` if the tree is empty."""
        if not self._tree:
            return None
        return self._tree[-1][0] if self._tree[-1] else None

    def add_leaf(self, data: bytes) -> int:
        """Append a leaf and return its zero-based index."""
        idx = len(self._leaves)
        self._leaves.append(self._hash_leaf(data))
        return idx

    def get_leaf_count(self) -> int:
        return len(self._leaves)

    def get_tree_height(self) -> int:
        if not self._leaves:
            return 0
        import math

        return math.ceil(math.log2(len(self._leaves))) + 1 if len(self._leaves) > 1 else 1

    def get_proof(self, index: int) -> list[tuple[bytes, str]]:
        """Return the authentication path for ``index`` as ``(hash, 'left'|'right')`` pairs."""
        if index < 0 or index >= len(self._leaves):
            raise IndexError(f"Leaf index {index} out of range")

        if not self._tree:
            self.build_tree()

        proof: list[tuple[bytes, str]] = []
        idx = index

        for level in self._tree[:-1]:
            if idx % 2 == 0:
                sibling = idx + 1 if idx + 1 < len(level) else idx
                proof.append((level[sibling], "right"))
            else:
                sibling = idx - 1
                proof.append((level[sibling], "left"))
            idx //= 2

        return proof

    def verify_proof(
        self, leaf_data: bytes, proof: Sequence[tuple[bytes, str]], expected_root: bytes
    ) -> bool:
        """Verify an authentication path against an expected root."""
        current = self._hash_leaf(leaf_data)

        for sibling_hash, direction in proof:
            if direction == "left":
                current = self._hash_node(sibling_hash, current)
            else:
                current = self._hash_node(current, sibling_hash)

        return current == expected_root
