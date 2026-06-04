"""Fundamental quantum circuits for trust and safety operations."""

from __future__ import annotations

import math

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit.library import QFT
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


def create_bell_state(num_qubits: int = 2) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required: pip install qiskit qiskit-aer")
    qc = QuantumCircuit(num_qubits, num_qubits)
    qc.h(0)
    for i in range(1, num_qubits):
        qc.cx(0, i)
    qc.measure(range(num_qubits), range(num_qubits))
    return qc


def create_ghz_state(num_qubits: int = 3) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required: pip install qiskit qiskit-aer")
    qc = QuantumCircuit(num_qubits, num_qubits)
    qc.h(0)
    for i in range(num_qubits - 1):
        qc.cx(i, i + 1)
    qc.measure(range(num_qubits), range(num_qubits))
    return qc


def quantum_fourier_transform(num_qubits: int = 4) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required: pip install qiskit qiskit-aer")
    qr = QuantumRegister(num_qubits, "q")
    qc = QuantumCircuit(qr)
    qc.append(QFT(num_qubits, do_swaps=True), qr)
    return qc


def hadamard_test(
    unitary_gate_name: str = "h",
    num_qubits: int = 1,
) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required: pip install qiskit qiskit-aer")
    qr = QuantumRegister(num_qubits + 1, "q")
    cr = ClassicalRegister(1, "c")
    qc = QuantumCircuit(qr, cr)
    qc.h(0)
    qc.cp(math.pi / 4, 0, 1)
    qc.h(0)
    qc.measure(0, 0)
    return qc


def grover_search(num_qubits: int = 3, target_state: int = 5) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required: pip install qiskit qiskit-aer")
    qc = QuantumCircuit(num_qubits, num_qubits)
    qc.h(range(num_qubits))

    num_iterations = max(1, int(math.pi / 4 * math.sqrt(2**num_qubits)))
    for _ in range(num_iterations):
        binary = format(target_state, f"0{num_qubits}b")
        for i, bit in enumerate(reversed(binary)):
            if bit == "0":
                qc.x(i)
        if num_qubits == 1:
            qc.h(0)
            qc.z(0)
            qc.h(0)
        else:
            qc.h(num_qubits - 1)
            qc.mcx(list(range(num_qubits - 1)), num_qubits - 1)
            qc.h(num_qubits - 1)
        for i, bit in enumerate(reversed(binary)):
            if bit == "0":
                qc.x(i)
        qc.h(range(num_qubits))
        qc.x(range(num_qubits))
        if num_qubits == 1:
            qc.h(0)
            qc.z(0)
            qc.h(0)
        else:
            qc.h(num_qubits - 1)
            qc.mcx(list(range(num_qubits - 1)), num_qubits - 1)
            qc.h(num_qubits - 1)
        qc.x(range(num_qubits))
        qc.h(range(num_qubits))

    qc.measure(range(num_qubits), range(num_qubits))
    return qc


def quantum_phase_estimation(
    num_counting_qubits: int = 3,
    target_gate_name: str = "t",
) -> "QuantumCircuit":
    if not QISKIT_AVAILABLE:
        raise ImportError("qiskit is required: pip install qiskit qiskit-aer")
    n = num_counting_qubits
    qc = QuantumCircuit(n + 1, n)
    qc.h(range(n))
    qc.x(n)
    for i in range(n):
        qc.cp(math.pi / (2 ** (n - i)), i, n)
    qc.append(QFT(n, do_swaps=True).inverse(), range(n))
    qc.measure(range(n), range(n))
    return qc
