"""QRNG tests: random bit generation, NIST tests, entropy."""

from __future__ import annotations

import math
import secrets
from collections import Counter

import pytest

from src.quantum.circuits.qrng import (
    QISKIT_AVAILABLE,
    QRNGTestResult,
    generate_random_bits,
    generate_random_bytes,
    generate_random_float,
    generate_random_int,
    min_entropy_test,
    nist_sp_800_90b_tests,
)


pytestmark = [pytest.mark.quantum]


class TestRandomBitGeneration:
    def test_generate_random_bits_count(self):
        bits = generate_random_bits(256)
        assert len(bits) == 256

    def test_generate_random_bits_values(self):
        bits = generate_random_bits(100)
        for b in bits:
            assert b in (0, 1)

    def test_generate_random_bits_different_each_time(self):
        bits1 = generate_random_bits(128)
        bits2 = generate_random_bits(128)
        assert bits1 != bits2

    def test_generate_random_bits_small(self):
        bits = generate_random_bits(8)
        assert len(bits) == 8

    def test_generate_random_bits_large(self):
        bits = generate_random_bits(4096)
        assert len(bits) == 4096


class TestRandomBytes:
    def test_generate_random_bytes_count(self):
        data = generate_random_bytes(32)
        assert len(data) == 32

    def test_generate_random_bytes_type(self):
        data = generate_random_bytes(16)
        assert isinstance(data, bytes)

    def test_generate_random_bytes_different(self):
        d1 = generate_random_bytes(32)
        d2 = generate_random_bytes(32)
        assert d1 != d2

    def test_generate_random_bytes_large(self):
        data = generate_random_bytes(256)
        assert len(data) == 256


class TestRandomInt:
    def test_random_int_in_range(self):
        for _ in range(100):
            val = generate_random_int(0, 100)
            assert 0 <= val <= 100

    def test_random_int_large_range(self):
        val = generate_random_int(0, 2**32 - 1)
        assert 0 <= val < 2**32

    def test_random_int_different(self):
        vals = {generate_random_int(0, 1000) for _ in range(50)}
        assert len(vals) > 1


class TestRandomFloat:
    def test_random_float_in_range(self):
        for _ in range(100):
            val = generate_random_float(0.0, 1.0)
            assert 0.0 <= val <= 1.0

    def test_random_float_custom_range(self):
        for _ in range(100):
            val = generate_random_float(5.0, 10.0)
            assert 5.0 <= val <= 10.0

    def test_random_float_different(self):
        vals = {generate_random_float() for _ in range(50)}
        assert len(vals) > 1


class TestNISTTests:
    def test_nist_insufficient_data(self):
        results = nist_sp_800_90b_tests([0, 1, 0, 1], block_size=128)
        assert len(results) == 1
        assert results[0].test_name == "insufficient_data"
        assert results[0].passed is False

    def test_nist_valid_data(self):
        bits = [secrets.randbelow(2) for _ in range(1024)]
        results = nist_sp_800_90b_tests(bits, block_size=128)
        assert len(results) >= 1
        for result in results:
            assert isinstance(result, QRNGTestResult)
            assert result.test_name in ("min_entropy", "sha256_entropy")

    def test_nist_min_entropy(self):
        bits = [secrets.randbelow(2) for _ in range(512)]
        results = nist_sp_800_90b_tests(bits, block_size=128)
        min_ent = [r for r in results if r.test_name == "min_entropy"]
        assert len(min_ent) == 1
        assert min_ent[0].p_value > 0

    def test_nist_deterministic_input(self):
        bits = [0] * 512
        results = nist_sp_800_90b_tests(bits, block_size=128)
        min_ent = [r for r in results if r.test_name == "min_entropy"]
        assert len(min_ent) == 1
        assert min_ent[0].passed is False


class TestMinEntropy:
    def test_min_entropy_random(self):
        bits = [secrets.randbelow(2) for _ in range(1000)]
        result = min_entropy_test(bits)
        assert isinstance(result, QRNGTestResult)
        assert result.test_name == "min_entropy"
        assert result.p_value > 0

    def test_min_entropy_uniform(self):
        bits = [0, 1] * 500
        result = min_entropy_test(bits)
        assert result.passed is True
        assert result.p_value >= 0.99

    def test_min_entropy_skewed(self):
        bits = [0] * 900 + [1] * 100
        result = min_entropy_test(bits)
        assert result.p_value < 1.0

    def test_min_entropy_empty(self):
        result = min_entropy_test([])
        assert result.passed is False
        assert result.p_value == 0.0

    def test_min_entropy_single_value(self):
        result = min_entropy_test([0] * 100)
        assert result.passed is False

    def test_min_entropy_result_structure(self):
        result = min_entropy_test([0, 1, 0, 1, 0, 1])
        assert hasattr(result, "test_name")
        assert hasattr(result, "passed")
        assert hasattr(result, "p_value")
        assert hasattr(result, "detail")
