"""Quantum feature maps for data encoding."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

try:
    from qiskit import QuantumCircuit, QuantumRegister
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

import numpy as np


@dataclass
class FeatureMapResult:
    circuit: Optional[object]
    num_qubits: int
    feature_map_type: str
    num_parameters: int


class ZZFeatureMap:
    def __init__(self, num_features: int, reps: int = 2, entanglement: str = "linear"):
        self.num_features = num_features
        self.num_qubits = num_features
        self.reps = reps
        self.entanglement = entanglement

    def build_circuit(self, features: np.ndarray) -> "QuantumCircuit":
        if not QISKIT_AVAILABLE:
            raise ImportError("qiskit is required")

        qr = QuantumRegister(self.num_qubits, "q")
        qc = QuantumCircuit(qr)

        for _ in range(self.reps):
            for i in range(self.num_qubits):
                qc.h(qr[i])
                qc.rz(2 * float(features[i % len(features)]), qr[i])

            pairs = self._get_entanglement_pairs()
            for i, j in pairs:
                qc.cx(qr[i], qr[j])
                qc.rz(2 * math.pi * float(features[i % len(features)]) * float(features[j % len(features)]), qr[j])
                qc.cx(qr[i], qr[j])

        return qc

    def _get_entanglement_pairs(self) -> List[tuple]:
        if self.entanglement == "linear":
            return [(i, i + 1) for i in range(self.num_qubits - 1)]
        elif self.entanglement == "circular":
            pairs = [(i, i + 1) for i in range(self.num_qubits - 1)]
            if self.num_qubits > 2:
                pairs.append((self.num_qubits - 1, 0))
            return pairs
        elif self.entanglement == "full":
            pairs = []
            for i in range(self.num_qubits):
                for j in range(i + 1, self.num_qubits):
                    pairs.append((i, j))
            return pairs
        return []


def amplitude_encoding(
    data: np.ndarray,
    num_qubits: int | None = None,
) -> FeatureMapResult:
    if num_qubits is None:
        num_qubits = int(np.ceil(np.log2(max(len(data), 2))))

    norm = np.linalg.norm(data)
    if norm > 0:
        normalized_data = data / norm
    else:
        normalized_data = data

    if QISKIT_AVAILABLE:
        qr = QuantumRegister(num_qubits, "q")
        qc = QuantumCircuit(qr)

        amplitudes = np.zeros(2**num_qubits, dtype=complex)
        amplitudes[: len(normalized_data)] = normalized_data

        qc.initialize(amplitudes, qr)

        return FeatureMapResult(
            circuit=qc,
            num_qubits=num_qubits,
            feature_map_type="amplitude",
            num_parameters=0,
        )

    return FeatureMapResult(
        circuit=None,
        num_qubits=num_qubits,
        feature_map_type="amplitude",
        num_parameters=0,
    )


def angle_encoding(
    features: np.ndarray,
    num_qubits: int | None = None,
    encoding_gate: str = "ry",
) -> FeatureMapResult:
    if num_qubits is None:
        num_qubits = len(features)

    if QISKIT_AVAILABLE:
        qr = QuantumRegister(num_qubits, "q")
        qc = QuantumCircuit(qr)

        for i in range(min(num_qubits, len(features))):
            angle = float(features[i]) * math.pi
            if encoding_gate == "ry":
                qc.ry(angle, qr[i])
            elif encoding_gate == "rz":
                qc.rz(angle, qr[i])
            elif encoding_gate == "rx":
                qc.rx(angle, qr[i])

        return FeatureMapResult(
            circuit=qc,
            num_qubits=num_qubits,
            feature_map_type="angle",
            num_parameters=num_qubits,
        )

    return FeatureMapResult(
        circuit=None,
        num_qubits=num_qubits,
        feature_map_type="angle",
        num_parameters=num_qubits,
    )


def hamiltonian_feature_map(
    features: np.ndarray,
    num_qubits: int | None = None,
    num_layers: int = 2,
) -> FeatureMapResult:
    if num_qubits is None:
        num_qubits = len(features)

    if QISKIT_AVAILABLE:
        qr = QuantumRegister(num_qubits, "q")
        qc = QuantumCircuit(qr)

        for _ in range(num_layers):
            for i in range(min(num_qubits, len(features))):
                qc.ry(float(features[i]) * math.pi, qr[i])

            for i in range(min(num_qubits, len(features)) - 1):
                qc.cx(qr[i], qr[i + 1])
                qc.rz(
                    float(features[i] * features[i + 1]) * math.pi,
                    qr[i + 1],
                )
                qc.cx(qr[i], qr[i + 1])

            if num_qubits > 2:
                qc.cx(qr[num_qubits - 1], qr[0])
                qc.rz(
                    float(features[-1] * features[0]) * math.pi,
                    qr[0],
                )
                qc.cx(qr[num_qubits - 1], qr[0])

        return FeatureMapResult(
            circuit=qc,
            num_qubits=num_qubits,
            feature_map_type="hamiltonian",
            num_parameters=num_qubits * num_layers,
        )

    return FeatureMapResult(
        circuit=None,
        num_qubits=num_qubits,
        feature_map_type="hamiltonian",
        num_parameters=num_qubits * num_layers,
    )
