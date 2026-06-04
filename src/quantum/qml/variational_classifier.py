"""Variational Quantum Classifier (VQC) for trust and safety classification."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit import ParameterVector
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

import numpy as np


@dataclass
class VQCResult:
    predictions: List[int]
    probabilities: List[List[float]]
    accuracy: float
    trained: bool
    num_params: int = 0
    loss_history: List[float] = field(default_factory=list)


class VariationalQuantumClassifier:
    def __init__(
        self,
        num_features: int = 4,
        num_qubits: int = 4,
        num_layers: int = 2,
        learning_rate: float = 0.1,
    ):
        self.num_features = num_features
        self.num_qubits = min(num_qubits, num_features)
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.params: Optional[np.ndarray] = None
        self.trained = False
        self.loss_history: List[float] = []

    def _build_feature_map(self, qc: QuantumCircuit, qr: QuantumRegister, features: List[float]) -> None:
        for i in range(self.num_qubits):
            qc.ry(features[i % len(features)], qr[i])

    def _build_variational_layer(
        self, qc: QuantumCircuit, qr: QuantumRegister, params: np.ndarray, layer_idx: int
    ) -> int:
        param_offset = layer_idx * self.num_qubits * 2
        for i in range(self.num_qubits):
            idx = param_offset + i
            if idx < len(params):
                qc.ry(params[idx], qr[i])
        for i in range(self.num_qubits - 1):
            qc.cx(qr[i], qr[i + 1])
        for i in range(self.num_qubits):
            idx = param_offset + self.num_qubits + i
            if idx < len(params):
                qc.rz(params[idx], qr[i])
        return param_offset + self.num_qubits * 2

    def build_circuit(
        self, features: List[float], params: np.ndarray
    ) -> "QuantumCircuit":
        if not QISKIT_AVAILABLE:
            raise ImportError("qiskit is required")

        qr = QuantumRegister(self.num_qubits, "q")
        cr = ClassicalRegister(1, "c")
        qc = QuantumCircuit(qr, cr)

        self._build_feature_map(qc, qr, features)

        for layer_idx in range(self.num_layers):
            self._build_variational_layer(qc, qr, params, layer_idx)

        qc.measure(0, 0)
        return qc

    def _compute_loss(
        self, X: np.ndarray, y: np.ndarray, params: np.ndarray
    ) -> float:
        if not QISKIT_AVAILABLE:
            return float(np.mean(np.random.random(len(y))))

        backend = AerSimulator()
        total_loss = 0.0

        for i in range(len(X)):
            qc = self.build_circuit(X[i].tolist(), params)
            result = backend.run(qc, shots=100).result()
            counts = result.get_counts()

            p_one = counts.get("1", 0) / 100.0
            target = float(y[i])
            total_loss += (p_one - target) ** 2

        return total_loss / len(X)

    def train(
        self, X: np.ndarray, y: np.ndarray, epochs: int = 50
    ) -> List[float]:
        num_params = self.num_qubits * 2 * self.num_layers
        self.params = np.random.uniform(0, 2 * np.pi, num_params)
        self.loss_history = []

        for epoch in range(epochs):
            loss = self._compute_loss(X, y, self.params)
            self.loss_history.append(loss)

            gradient = np.zeros_like(self.params)
            epsilon = 0.01
            for i in range(len(self.params)):
                params_plus = self.params.copy()
                params_plus[i] += epsilon
                params_minus = self.params.copy()
                params_minus[i] -= epsilon
                loss_plus = self._compute_loss(X, y, params_plus)
                loss_minus = self._compute_loss(X, y, params_minus)
                gradient[i] = (loss_plus - loss_minus) / (2 * epsilon)

            self.params -= self.learning_rate * gradient

        self.trained = True
        return self.loss_history

    def predict(self, X: np.ndarray) -> VQCResult:
        if self.params is None:
            raise RuntimeError("Model not trained")

        predictions = []
        probabilities = []

        if QISKIT_AVAILABLE:
            backend = AerSimulator()
            for i in range(len(X)):
                qc = self.build_circuit(X[i].tolist(), self.params)
                result = backend.run(qc, shots=100).result()
                counts = result.get_counts()
                p_one = counts.get("1", 0) / 100.0
                p_zero = 1.0 - p_one
                predictions.append(1 if p_one > 0.5 else 0)
                probabilities.append([p_zero, p_one])
        else:
            for i in range(len(X)):
                predictions.append(int(np.random.random() > 0.5))
                probabilities.append([0.5, 0.5])

        return VQCResult(
            predictions=predictions,
            probabilities=probabilities,
            accuracy=0.0,
            trained=self.trained,
            num_params=len(self.params),
            loss_history=self.loss_history,
        )

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> float:
        result = self.predict(X)
        correct = sum(1 for p, t in zip(result.predictions, y) if p == int(t))
        return correct / len(y) if len(y) > 0 else 0.0

    def get_accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        return self.evaluate(X, y)
