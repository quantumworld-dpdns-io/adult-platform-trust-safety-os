"""Tests for Merkle tree: build, root, proof generation, and verification."""

from __future__ import annotations

import hashlib

import pytest

from src.audit.merkle import MerkleTree, _sha256


def test_build_tree_empty():
    tree = MerkleTree()
    tree.build_tree()
    assert tree.get_root() is None


def test_build_tree_single_leaf():
    tree = MerkleTree()
    tree.add_leaf(b"leaf-0")
    tree.build_tree()
    root = tree.get_root()
    assert root is not None
    assert len(root) == 32


def test_build_tree_two_leaves():
    tree = MerkleTree()
    tree.add_leaf(b"leaf-0")
    tree.add_leaf(b"leaf-1")
    tree.build_tree()
    root = tree.get_root()
    assert root is not None
    assert tree.get_tree_height() >= 2


def test_get_root_empty_tree():
    tree = MerkleTree()
    assert tree.get_root() is None


def test_get_root_after_build():
    tree = MerkleTree()
    tree.add_leaf(b"data-0")
    tree.add_leaf(b"data-1")
    tree.add_leaf(b"data-2")
    tree.build_tree()
    root = tree.get_root()
    assert root is not None
    assert isinstance(root, bytes)


def test_proof_generation():
    tree = MerkleTree()
    for i in range(4):
        tree.add_leaf(f"leaf-{i}".encode())
    tree.build_tree()
    proof = tree.get_proof(0)
    assert isinstance(proof, list)
    assert len(proof) > 0
    for sibling_hash, direction in proof:
        assert isinstance(sibling_hash, bytes)
        assert direction in ("left", "right")


def test_proof_generation_invalid_index():
    tree = MerkleTree()
    tree.add_leaf(b"only-leaf")
    tree.build_tree()
    with pytest.raises(IndexError):
        tree.get_proof(5)


def test_verify_proof():
    tree = MerkleTree()
    leaves = [f"leaf-{i}".encode() for i in range(4)]
    for leaf in leaves:
        tree.add_leaf(leaf)
    tree.build_tree()
    root = tree.get_root()
    proof = tree.get_proof(0)
    assert tree.verify_proof(leaves[0], proof, root) is True


def test_verify_proof_tampered_leaf():
    tree = MerkleTree()
    leaves = [f"leaf-{i}".encode() for i in range(4)]
    for leaf in leaves:
        tree.add_leaf(leaf)
    tree.build_tree()
    root = tree.get_root()
    proof = tree.get_proof(0)
    assert tree.verify_proof(b"TAMPERED", proof, root) is False


def test_verify_proof_wrong_root():
    tree = MerkleTree()
    leaves = [f"leaf-{i}".encode() for i in range(4)]
    for leaf in leaves:
        tree.add_leaf(leaf)
    tree.build_tree()
    proof = tree.get_proof(0)
    fake_root = hashlib.sha256(b"fake").digest()
    assert tree.verify_proof(leaves[0], proof, fake_root) is False


def test_proof_verification_round_trip():
    tree = MerkleTree()
    leaves = [f"data-{i}".encode() for i in range(8)]
    for leaf in leaves:
        tree.add_leaf(leaf)
    tree.build_tree()
    root = tree.get_root()
    for i in range(8):
        proof = tree.get_proof(i)
        assert tree.verify_proof(leaves[i], proof, root) is True


def test_leaf_count():
    tree = MerkleTree()
    assert tree.get_leaf_count() == 0
    tree.add_leaf(b"a")
    assert tree.get_leaf_count() == 1
    tree.add_leaf(b"b")
    tree.add_leaf(b"c")
    assert tree.get_leaf_count() == 3


def test_tree_height():
    tree = MerkleTree()
    assert tree.get_tree_height() == 0
    tree.add_leaf(b"a")
    assert tree.get_tree_height() == 1
    tree.add_leaf(b"b")
    tree.build_tree()
    assert tree.get_tree_height() == 2
    tree.add_leaf(b"c")
    tree.add_leaf(b"d")
    tree.build_tree()
    assert tree.get_tree_height() >= 3


def test_sha256_hash():
    result = _sha256(b"test data")
    assert len(result) == 32
    assert isinstance(result, bytes)


def test_domain_separator_leaves():
    t1 = MerkleTree()
    t1.add_leaf(b"data")
    h1 = t1._hash_leaf(b"data")
    h2 = hashlib.sha256(MerkleTree.LEAF_PREFIX + b"data").digest()
    assert h1 == h2
