"""Quantum circuit tests: bell state, GHZ, QFT, Grover."""

from __future__ import annotations

import math

import pytest

from src.quantum.circuits.basics import (
    QISKIT_AVAILABLE,
    create_bell_state,
    create_ghz_state,
    grover_search,
    hadamard_test,
    quantum_fourier_transform,
    quantum_phase_estimation,
)


pytestmark = [pytest.mark.quantum]


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestBellState:
    def test_bell_state_2_qubits(self):
        qc = create_bell_state(2)
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2

    def test_bell_state_has_h_gate(self):
        qc = create_bell_state(2)
        ops = qc.count_ops()
        assert "h" in ops

    def test_bell_state_has_cx_gate(self):
        qc = create_bell_state(2)
        ops = qc.count_ops()
        assert "cx" in ops

    def test_bell_state_3_qubits(self):
        qc = create_bell_state(3)
        assert qc.num_qubits == 3

    def test_bell_state_measurements(self):
        qc = create_bell_state(2)
        ops = qc.count_ops()
        assert "measure" in ops


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestGHZState:
    def test_ghz_3_qubits(self):
        qc = create_ghz_state(3)
        assert qc.num_qubits == 3

    def test_ghz_4_qubits(self):
        qc = create_ghz_state(4)
        assert qc.num_qubits == 4

    def test_ghz_has_h_gate(self):
        qc = create_ghz_state(3)
        ops = qc.count_ops()
        assert "h" in ops

    def test_ghz_has_cx_gates(self):
        qc = create_ghz_state(3)
        ops = qc.count_ops()
        assert "cx" in ops

    def test_ghz_measurements(self):
        qc = create_ghz_state(3)
        ops = qc.count_ops()
        assert "measure" in ops


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestQFT:
    def test_qft_2_qubits(self):
        qc = quantum_fourier_transform(2)
        assert qc.num_qubits == 2

    def test_qft_4_qubits(self):
        qc = quantum_fourier_transform(4)
        assert qc.num_qubits == 4

    def test_qft_8_qubits(self):
        qc = quantum_fourier_transform(8)
        assert qc.num_qubits == 8

    def test_qft_has_qubits(self):
        qc = quantum_fourier_transform(3)
        assert qc.num_qubits == 3


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestGroverSearch:
    def test_grover_2_qubits(self):
        qc = grover_search(2, target_state=1)
        assert qc.num_qubits == 2
        assert qc.num_clbits == 2

    def test_grover_3_qubits(self):
        qc = grover_search(3, target_state=5)
        assert qc.num_qubits == 3

    def test_grover_has_measurements(self):
        qc = grover_search(3, target_state=2)
        ops = qc.count_ops()
        assert "measure" in ops

    def test_grover_different_targets(self):
        for target in [0, 1, 2, 3, 4, 5, 6, 7]:
            qc = grover_search(3, target_state=target)
            assert qc.num_qubits == 3


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestHadamardTest:
    def test_hadamard_test_basic(self):
        qc = hadamard_test()
        assert qc.num_qubits >= 1

    def test_hadamard_test_has_measurement(self):
        qc = hadamard_test()
        ops = qc.count_ops()
        assert "measure" in ops


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestQPE:
    def test_qpe_basic(self):
        qc = quantum_phase_estimation(3)
        assert qc.num_qubits == 4

    def test_qpe_more_counting_qubits(self):
        qc = quantum_phase_estimation(5)
        assert qc.num_qubits == 6

    def test_qpe_has_measurements(self):
        qc = quantum_phase_estimation(3)
        ops = qc.count_ops()
        assert "measure" in ops


@pytest.mark.skipif(not QISKIT_AVAILABLE, reason="qiskit not installed")
class TestCircuitExecution:
    def test_bell_state_execution(self):
        from qiskit_aer import AerSimulator

        qc = create_bell_state(2)
        backend = AerSimulator()
        result = backend.run(qc, shots=100).result()
        counts = result.get_counts()
        assert len(counts) > 0
        total_shots = sum(counts.values())
        assert total_shots == 100

    def test_ghz_state_execution(self):
        from qiskit_aer import AerSimulator

        qc = create_ghz_state(3)
        backend = AerSimulator()
        result = backend.run(qc, shots=100).result()
        counts = result.get_counts()
        assert len(counts) > 0

    def test_grover_execution(self):
        from qiskit_aer import AerSimulator

        qc = grover_search(2, target_state=1)
        backend = AerSimulator()
        result = backend.run(qc, shots=100).result()
        counts = result.get_counts()
        assert len(counts) > 0
