"""Superdense coding circuit implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


@dataclass
class SuperdenseResult:
    message_bits: Tuple[int, int]
    decoded_bits: Tuple[int, int]
    success: bool


def create_superdense_circuit() -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    qr = QuantumRegister(2, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr)
    qc.h(qr[0])
    qc.cx(qr[0], qr[1])
    return qc


def encode_classical_bits(
    bit0: int,
    bit1: int,
    bell_pair: "QuantumCircuit | None" = None,
) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    if bell_pair is None:
        bell_pair = create_superdense_circuit()

    qc = bell_pair.copy()
    qr = qc.qubits[:2]

    if bit1 == 1 and bit0 == 1:
        qc.x(qr[0])
        qc.z(qr[0])
    elif bit1 == 1:
        qc.x(qr[0])
    elif bit0 == 1:
        qc.z(qr[0])

    qc.cx(qr[0], qr[1])
    qc.h(qr[0])

    cr = ClassicalRegister(2, "result")
    qc.add_register(cr)
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])

    return qc


def decode_superdense(
    bit0: int,
    bit1: int,
) -> SuperdenseResult:
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    qc = encode_classical_bits(bit0, bit1)
    backend = AerSimulator()
    result = backend.run(qc, shots=1, memory=True).result()
    counts = result.get_counts()
    bitstring = list(counts.keys())[0]
    decoded = (int(bitstring[1]), int(bitstring[0]))
    return SuperdenseResult(
        message_bits=(bit0, bit1),
        decoded_bits=decoded,
        success=decoded == (bit0, bit1),
    )


def verify_superdense(num_trials: int = 100) -> float:
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    successes = 0
    for _ in range(num_trials):
        import random
        b0, b1 = random.randint(0, 1), random.randint(0, 1)
        result = decode_superdense(b0, b1)
        if result.success:
            successes += 1
    return successes / num_trials
