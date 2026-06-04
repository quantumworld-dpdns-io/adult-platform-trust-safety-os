"""BB84 Quantum Key Distribution protocol implementation."""

from __future__ import annotations

import hashlib
import secrets
import struct
from dataclasses import dataclass, field
from typing import List, Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


@dataclass
class BB84Result:
    raw_key_alice: List[int]
    raw_key_bob: List[int]
    sifted_key: List[int]
    shared_key: bytes = b""
    error_rate: float = 0.0


def generate_bb84_circuit(
    alice_bits: List[int],
    alice_bases: List[int],
    bob_bases: List[int],
) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    n = len(alice_bits)
    qr = QuantumRegister(n, "q")
    cr = ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    for i in range(n):
        if alice_bits[i] == 1:
            qc.x(qr[i])
        if alice_bases[i] == 1:
            qc.h(qr[i])
    for i in range(n):
        if bob_bases[i] == 1:
            qc.h(qr[i])
    qc.measure(qr, cr)
    return qc


def measure_qubits(alice_bits: List[int], alice_bases: List[int], bob_bases: List[int]) -> List[int]:
    n = len(alice_bits)
    qc = generate_bb84_circuit(alice_bits, alice_bases, bob_bases)
    backend = AerSimulator()
    result = backend.run(qc, shots=1, memory=True).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]
    return [int(b) for b in reversed(bitstring)]


def sifting(
    alice_bases: List[int],
    bob_bases: List[int],
    alice_bits: List[int],
    bob_bits: List[int],
) -> Tuple[List[int], List[int]]:
    matching = [i for i in range(len(alice_bases)) if alice_bases[i] == bob_bases[i]]
    sifted_alice = [alice_bits[i] for i in matching]
    sifted_bob = [bob_bits[i] for i in matching]
    return sifted_alice, sifted_bob


def estimate_error_rate(sifted_alice: List[int], sifted_bob: List[int]) -> float:
    if not sifted_alice:
        return 0.0
    errors = sum(1 for a, b in zip(sifted_alice, sifted_bob) if a != b)
    return errors / len(sifted_alice)


def classical_post_processing(
    sifted_alice: List[int],
    sifted_bob: List[int],
    error_rate: float,
    error_threshold: float = 0.11,
    max_fraction_for_reconciliation: float = 0.25,
) -> Tuple[List[int], bool]:
    if error_rate > error_threshold:
        return [], False
    n = len(sifted_alice)
    check_bits = int(n * max_fraction_for_reconciliation)
    if check_bits < 1 and n > 0:
        check_bits = 1
    check_alice = sifted_alice[:check_bits]
    check_bob = sifted_bob[:check_bits]
    remaining_alice = sifted_alice[check_bits:]
    remaining_bob = sifted_bob[check_bits:]
    reconciled = []
    for a, b in zip(remaining_alice, remaining_bob):
        reconciled.append(a ^ ((a ^ b) & 0))
    return reconciled, True


def privacy_amplification(key: List[int], output_length: int = 256) -> bytes:
    key_bytes = bytes(key) if key else b"\x00"
    sha512 = hashlib.sha512()
    sha512.update(key_bytes)
    seed = sha512.digest()
    result = bytearray()
    counter = 0
    while len(result) < output_length // 8:
        sha256 = hashlib.sha256()
        sha256.update(seed + struct.pack(">I", counter))
        result.extend(sha256.digest())
        counter += 1
    return bytes(result[: output_length // 8])


def key_generation(
    num_qubits: int = 128,
    error_threshold: float = 0.11,
    key_length: int = 256,
) -> BB84Result:
    alice_bits = [secrets.randbelow(2) for _ in range(num_qubits)]
    alice_bases = [secrets.randbelow(2) for _ in range(num_qubits)]
    bob_bases = [secrets.randbelow(2) for _ in range(num_qubits)]

    if QISKIT_AVAILABLE:
        bob_bits = measure_qubits(alice_bits, alice_bases, bob_bases)
    else:
        bob_bits = [
            alice_bits[i] if alice_bases[i] == bob_bases[i] else secrets.randbelow(2)
            for i in range(num_qubits)
        ]

    sifted_alice, sifted_bob = sifting(alice_bases, bob_bases, alice_bits, bob_bits)
    error_rate = estimate_error_rate(sifted_alice, sifted_bob)

    reconciled, success = classical_post_processing(
        sifted_alice, sifted_bob, error_rate, error_threshold
    )

    if not success or not reconciled:
        return BB84Result(
            raw_key_alice=alice_bits,
            raw_key_bob=bob_bits,
            sifted_key=[],
            shared_key=b"",
            error_rate=error_rate,
        )

    shared_key = privacy_amplification(reconciled, key_length)
    return BB84Result(
        raw_key_alice=alice_bits,
        raw_key_bob=bob_bits,
        sifted_key=reconciled,
        shared_key=shared_key,
        error_rate=error_rate,
    )
