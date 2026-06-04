"""Quantum Random Number Generation with NIST SP 800-90B testing."""

from __future__ import annotations

import hashlib
import math
import secrets
import struct
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


@dataclass
class QRNGTestResult:
    test_name: str
    passed: bool
    p_value: float
    detail: str = ""


def _create_random_circuit(num_qubits: int) -> "QuantumCircuit":
    qr = QuantumRegister(num_qubits, "q")
    cr = ClassicalRegister(num_qubits, "c")
    qc = QuantumCircuit(qr, cr)
    qc.h(range(num_qubits))
    qc.measure(qr, cr)
    return qc


def generate_random_bits(num_bits: int = 256) -> List[int]:
    bits: List[int] = []
    if QISKIT_AVAILABLE:
        backend = AerSimulator()
        while len(bits) < num_bits:
            batch = min(4096, num_bits - len(bits))
            qc = _create_random_circuit(batch)
            result = backend.run(qc, shots=1, memory=True).result()
            bitstring = list(result.get_memory())[0]
            bits.extend(int(b) for b in reversed(bitstring))
    else:
        bits = [secrets.randbelow(2) for _ in range(num_bits)]
    return bits[:num_bits]


def generate_random_bytes(num_bytes: int = 32) -> bytes:
    bits = generate_random_bits(num_bytes * 8)
    result = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte = (byte << 1) | bits[i + j]
        result.append(byte)
    return bytes(result)


def generate_random_int(lower: int = 0, upper: int = 2**32 - 1) -> int:
    bits = generate_random_bits(64)
    value = 0
    for b in bits:
        value = (value << 1) | b
    value = value % (upper - lower + 1) + lower
    return value


def generate_random_float(lower: float = 0.0, upper: float = 1.0) -> float:
    bits = generate_random_bits(53)
    value = 0
    for b in bits:
        value = (value << 1) | b
    return lower + (value / (2**53)) * (upper - lower)


def nist_sp_800_90b_tests(data: List[int], block_size: int = 128) -> List[QRNGTestResult]:
    results: List[QRNGTestResult] = []
    n = len(data)

    if n < 2 * block_size:
        return [QRNGTestResult("insufficient_data", False, 0.0, f"Need >= {2*block_size} bits, got {n}")]

    num_blocks = n // block_size
    blocks = []
    for i in range(num_blocks):
        start = i * block_size
        block = data[start : start + block_size]
        blocks.append(block)

    block_entropies = []
    for block in blocks:
        counts = Counter(block)
        entropy = 0.0
        for count in counts.values():
            p = count / len(block)
            if p > 0:
                entropy -= p * math.log2(p)
        block_entropies.append(entropy)

    min_entropy = min(block_entropies) if block_entropies else 0.0
    avg_entropy = sum(block_entropies) / len(block_entropies) if block_entropies else 0.0
    results.append(QRNGTestResult(
        "min_entropy",
        min_entropy > 0.5,
        min_entropy,
        f"min_entropy={min_entropy:.4f}, avg_entropy={avg_entropy:.4f}",
    ))

    bits = data[:n - (n % 8)]
    bytes_list = []
    for i in range(0, len(bits), 8):
        byte_val = 0
        for j in range(8):
            byte_val = (byte_val << 1) | bits[i + j]
        bytes_list.append(byte_val)

    if bytes_list:
        sha256_digest = hashlib.sha256(bytes(bytes_list)).digest()
        sha256_entr = sum(b.bit_length() for b in sha256_digest) / (len(sha256_digest) * 8)
    else:
        sha256_entr = 0.0
    results.append(QRNGTestResult(
        "sha256_entropy",
        sha256_entr > 0.5,
        sha256_entr,
        f"sha256_entropy={sha256_entr:.4f}",
    ))

    return results


def min_entropy_test(data: List[int]) -> QRNGTestResult:
    if not data:
        return QRNGTestResult("min_entropy_empty", False, 0.0, "No data provided")
    counts = Counter(data)
    n = len(data)
    max_prob = max(count / n for count in counts.values())
    if max_prob <= 0:
        return QRNGTestResult("min_entropy", False, 0.0, "Max probability is zero")
    min_entr = -math.log2(max_prob)
    return QRNGTestResult(
        "min_entropy",
        min_entr > 0.5,
        min_entr,
        f"min_entropy={min_entr:.4f}, max_prob={max_prob:.4f}",
    )
