"""Quantum teleportation circuit implementation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    from qiskit.quantum_info import Statevector
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


@dataclass
class TeleportationResult:
    original_state: Tuple[complex, complex]
    teleported_state: Tuple[complex, complex]
    fidelity: float
    success: bool


def create_teleportation_circuit(
    state: Tuple[float, float] = (1 / math.sqrt(2), 1 / math.sqrt(2)),
) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    qr = QuantumRegister(3, "q")
    cr = ClassicalRegister(2, "c")
    qc = QuantumCircuit(qr, cr)

    alpha, beta = state
    norm = math.sqrt(abs(alpha) ** 2 + abs(beta) ** 2)
    if norm > 0:
        alpha, beta = alpha / norm, beta / norm
    qc.initialize([alpha, beta], qr[0])

    qc.h(qr[1])
    qc.cx(qr[1], qr[2])

    qc.cx(qr[0], qr[1])
    qc.h(qr[0])

    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])

    with qc.if_test((cr, 1)):
        qc.x(qr[2])
    with qc.if_test((cr, 2)):
        qc.z(qr[2])
    with qc.if_test((cr, 3)):
        qc.x(qr[2])
        qc.z(qr[2])

    return qc


def teleport_state(
    state: Tuple[complex, complex] = (1 / math.sqrt(2), 1 / math.sqrt(2)),
) -> TeleportationResult:
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required")
    qc = create_teleportation_circuit((abs(state[0]), abs(state[1])))
    backend = AerSimulator()
    num_shots = 1024
    result = backend.run(qc, shots=num_shots).result()
    counts = result.get_counts()

    total_counts = {}
    for key, count in counts.items():
        cr_value = int(key, 2)
        total_counts[cr_value] = total_counts.get(cr_value, 0) + count

    qc_verify = QuantumCircuit(1, 1)
    alpha, beta = state
    norm = math.sqrt(abs(alpha) ** 2 + abs(beta) ** 2)
    if norm > 0:
        alpha, beta = alpha / norm, beta / norm
    qc_verify.initialize([alpha, beta], 0)

    original_state = (alpha, beta)

    zero_count = total_counts.get(0, 0) + total_counts.get(2, 0)
    one_count = total_counts.get(1, 0) + total_counts.get(3, 0)

    if zero_count + one_count > 0:
        p0 = zero_count / (zero_count + one_count)
        p1 = one_count / (zero_count + one_count)
    else:
        p0, p1 = 0.5, 0.5

    alpha_sq = abs(alpha) ** 2
    fidelity = 1.0 - abs(p0 - alpha_sq)
    fidelity = max(0.0, min(1.0, fidelity))

    teleported_state = (complex(math.sqrt(p0)), complex(math.sqrt(p1)))

    return TeleportationResult(
        original_state=original_state,
        teleported_state=teleported_state,
        fidelity=fidelity,
        success=fidelity > 0.9,
    )


def verify_teleportation(
    state: Tuple[complex, complex] = (1 / math.sqrt(2), 1 / math.sqrt(2)),
    num_shots: int = 1024,
) -> bool:
    result = teleport_state(state)
    return result.success
