"""Quantum kernel methods for classification."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

import numpy as np


@dataclass
class KernelSVMResult:
    predictions: List[int]
    accuracy: float
    support_vector_indices: List[int]
    alphas: np.ndarray
    bias: float


class QuantumKernel:
    def __init__(self, num_features: int = 4, num_qubits: int = 4):
        self.num_features = num_features
        self.num_qubits = min(num_qubits, num_features)

    def _encode_data(self, qc: QuantumCircuit, qr: QuantumRegister, features: np.ndarray) -> None:
        for i in range(self.num_qubits):
            angle = float(features[i % len(features)]) * math.pi
            qc.ry(angle, qr[i])

    def _swap_test_circuit(
        self, x1: np.ndarray, x2: np.ndarray
    ) -> "QuantumCircuit":
        if not QISKIT_AVAILABLE:
            raise ImportError("qiskit is required")

        qr = QuantumRegister(2 * self.num_qubits + 1, "q")
        cr = ClassicalRegister(1, "c")
        qc = QuantumCircuit(qr, cr)

        qc.h(0)

        for i in range(self.num_qubits):
            angle1 = float(x1[i % len(x1)]) * math.pi
            angle2 = float(x2[i % len(x2)]) * math.pi
            qc.ry(angle1, qr[1 + i])
            qc.ry(angle2, qr[1 + self.num_qubits + i])

        qc.cswap(0, 1, 1 + self.num_qubits)
        for i in range(1, self.num_qubits):
            qc.cswap(0, 1 + i, 1 + self.num_qubits + i)

        qc.h(0)
        qc.measure(0, 0)
        return qc

    def compute_kernel_entry(self, x1: np.ndarray, x2: np.ndarray) -> float:
        if QISKIT_AVAILABLE:
            qc = self._swap_test_circuit(x1, x2)
            backend = AerSimulator()
            result = backend.run(qc, shots=200).result()
            counts = result.get_counts()
            p_zero = counts.get("0", 0) / 200.0
            return 2.0 * p_zero - 1.0
        else:
            dot = np.dot(x1[:self.num_qubits], x2[:self.num_qubits])
            norm1 = np.linalg.norm(x1[:self.num_qubits])
            norm2 = np.linalg.norm(x2[:self.num_qubits])
            if norm1 > 0 and norm2 > 0:
                return float(dot / (norm1 * norm2))
            return 0.0

    def compute_kernel_matrix(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        n1 = len(X1)
        n2 = len(X2)
        K = np.zeros((n1, n2))
        for i in range(n1):
            for j in range(n2):
                K[i, j] = self.compute_kernel_entry(X1[i], X2[j])
        return K

    def train_svm(
        self,
        X: np.ndarray,
        y: np.ndarray,
        C: float = 1.0,
        max_iterations: int = 100,
    ) -> KernelSVMResult:
        n = len(X)
        K = self.compute_kernel_matrix(X, X)

        alphas = np.zeros(n)
        bias = 0.0

        for _ in range(max_iterations):
            for i in range(n):
                decision = np.sum(alphas * y * K[i, :]) + bias
                if y[i] * decision < 1:
                    alphas[i] += 0.01
                    alphas[i] = min(alphas[i], C)
                    bias += 0.01 * y[i]

        support_indices = np.where(alphas > 1e-6)[0].tolist()

        predictions = []
        for i in range(n):
            decision = np.sum(alphas * y * K[i, :]) + bias
            predictions.append(1 if decision >= 0 else -1)

        correct = sum(1 for p, t in zip(predictions, y) if p == int(t))
        accuracy = correct / n if n > 0 else 0.0

        return KernelSVMResult(
            predictions=predictions,
            accuracy=accuracy,
            support_vector_indices=support_indices,
            alphas=alphas,
            bias=bias,
        )

    def predict(self, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> List[int]:
        K_test = self.compute_kernel_matrix(X_test, X_train)
        svm_result = self.train_svm(X_train, y_train)

        predictions = []
        for i in range(len(X_test)):
            decision = np.sum(svm_result.alphas * y_train * K_test[i, :]) + svm_result.bias
            predictions.append(1 if decision >= 0 else -1)
        return predictions
