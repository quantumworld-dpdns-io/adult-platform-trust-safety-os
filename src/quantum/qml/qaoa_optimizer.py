"""QAOA optimization for combinatorial problems."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit import ParameterVector
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

import numpy as np


@dataclass
class QAOAResult:
    solution: Dict[int, int]
    cost: float
    num_qubits: int
    p_layers: int
    optimal_params: List[float]
    measurement_counts: Dict[str, int]


class QAOAOptimizer:
    def __init__(self, num_qubits: int, p: int = 2):
        self.num_qubits = num_qubits
        self.p = p

    def _build_cost_unitary(
        self, qc: QuantumCircuit, qr: QuantumRegister, gamma: float,
        edges: List[Tuple[int, int, float]]
    ) -> None:
        for i, j, weight in edges:
            if i < self.num_qubits and j < self.num_qubits:
                qc.cx(qr[i], qr[j])
                qc.rz(2 * gamma * weight, qr[j])
                qc.cx(qr[i], qr[j])

    def _build_mixer_unitary(
        self, qc: QuantumCircuit, qr: QuantumRegister, beta: float
    ) -> None:
        for i in range(self.num_qubits):
            qc.rx(2 * beta, qr[i])

    def create_qaoa_circuit(
        self,
        edges: List[Tuple[int, int, float]],
        params: Optional[List[float]] = None,
    ) -> "QuantumCircuit":
        if not QISKIT_AVAILABLE:
            raise ImportError("qiskit is required")

        if params is None:
            params = [0.5] * (2 * self.p)

        qr = QuantumRegister(self.num_qubits, "q")
        cr = ClassicalRegister(self.num_qubits, "c")
        qc = QuantumCircuit(qr, cr)

        qc.h(range(self.num_qubits))

        for layer in range(self.p):
            gamma = params[2 * layer]
            beta = params[2 * layer + 1]
            self._build_cost_unitary(qc, qr, gamma, edges)
            self._build_mixer_unitary(qc, qr, beta)

        qc.measure(range(self.num_qubits), range(self.num_qubits))
        return qc

    def _evaluate_cost(
        self, bitstring: str, edges: List[Tuple[int, int, float]]
    ) -> float:
        assignment = [int(b) for b in bitstring]
        cost = 0.0
        for i, j, weight in edges:
            if assignment[i] != assignment[j]:
                cost += weight
        return cost

    def _compute_expectation(
        self, params: List[float], edges: List[Tuple[int, int, float]], shots: int = 512
    ) -> float:
        qc = self.create_qaoa_circuit(edges, params)
        backend = AerSimulator()
        result = backend.run(qc, shots=shots).result()
        counts = result.get_counts()

        total_cost = 0.0
        total_shots = 0
        for bitstring, count in counts.items():
            cost = self._evaluate_cost(bitstring, edges)
            total_cost += cost * count
            total_shots += count

        return total_cost / total_shots if total_shots > 0 else 0.0

    def optimize(
        self,
        edges: List[Tuple[int, int, float]],
        max_iterations: int = 50,
        learning_rate: float = 0.1,
    ) -> QAOAResult:
        num_params = 2 * self.p
        params = np.random.uniform(0, 2 * math.pi, num_params)
        history = []

        for iteration in range(max_iterations):
            current_cost = self._compute_expectation(params.tolist(), edges)
            history.append(current_cost)

            gradient = np.zeros(num_params)
            epsilon = 0.05
            for i in range(num_params):
                params_plus = params.copy()
                params_plus[i] += epsilon
                params_minus = params.copy()
                params_minus[i] -= epsilon
                cost_plus = self._compute_expectation(params_plus.tolist(), edges)
                cost_minus = self._compute_expectation(params_minus.tolist(), edges)
                gradient[i] = (cost_plus - cost_minus) / (2 * epsilon)

            params += learning_rate * gradient
            params = params % (2 * math.pi)

        qc = self.create_qaoa_circuit(edges, params.tolist())
        backend = AerSimulator()
        result = backend.run(qc, shots=1024).result()
        counts = result.get_counts()

        best_bitstring = max(counts, key=counts.get)
        best_cost = self._evaluate_cost(best_bitstring, edges)

        solution = {i: int(b) for i, b in enumerate(best_bitstring)}

        return QAOAResult(
            solution=solution,
            cost=best_cost,
            num_qubits=self.num_qubits,
            p_layers=self.p,
            optimal_params=params.tolist(),
            measurement_counts=counts,
        )

    def get_optimal_params(self) -> List[float]:
        return [0.5] * (2 * self.p)


def solve_maxcut(
    edges: List[Tuple[int, int]],
    num_qubits: int | None = None,
    p: int = 2,
) -> QAOAResult:
    if num_qubits is None:
        num_qubits = max(max(i, j) for i, j in edges) + 1

    weighted_edges = [(i, j, 1.0) for i, j in edges]
    optimizer = QAOAOptimizer(num_qubits, p)
    return optimizer.optimize(weighted_edges)


def solve_tsp(
    distance_matrix: np.ndarray,
    num_cities: int | None = None,
    p: int = 2,
) -> QAOAResult:
    if num_cities is None:
        num_cities = distance_matrix.shape[0]

    edges: List[Tuple[int, int, float]] = []
    for i in range(num_cities):
        for j in range(i + 1, num_cities):
            if distance_matrix[i, j] > 0:
                edges.append((i, j, float(distance_matrix[i, j])))

    num_qubits = num_cities * num_cities
    optimizer = QAOAOptimizer(num_qubits, p)

    scaled_edges = [(i, j, w * 0.1) for i, j, w in edges]
    return optimizer.optimize(scaled_edges)
