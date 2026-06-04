"""Quantum random beacon for verifiable random values."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


@dataclass
class BeaconValue:
    value: bytes
    round_number: int
    timestamp: float
    previous_hash: bytes
    proof: Dict[str, Any]
    quantum_seed: bool = False


@dataclass
class VRFProof:
    input_hash: bytes
    output: bytes
    proof: bytes
    public_key: bytes


_BEACON_HISTORY: List[BeaconValue] = []


def _quantum_random_bytes(num_bytes: int = 32) -> bytes:
    if QISKIT_AVAILABLE:
        backend = AerSimulator()
        num_qubits = num_bytes * 8
        qr = QuantumRegister(num_qubits, "q")
        cr = ClassicalRegister(num_qubits, "c")
        qc = QuantumCircuit(qr, cr)
        qc.h(range(num_qubits))
        qc.measure(qr, cr)
        result = backend.run(qc, shots=1, memory=True).result()
        bitstring = list(result.get_memory())[0]
        byte_array = bytearray()
        for i in range(0, len(bitstring), 8):
            byte_val = 0
            for j in range(8):
                if i + j < len(bitstring):
                    byte_val = (byte_val << 1) | int(bitstring[i + j])
            byte_array.append(byte_val)
        return bytes(byte_array[:num_bytes])
    return secrets.token_bytes(num_bytes)


def generate_beacon_value(
    round_number: int | None = None,
    previous_hash: bytes | None = None,
) -> BeaconValue:
    if round_number is None:
        round_number = len(_BEACON_HISTORY) + 1

    if previous_hash is None and _BEACON_HISTORY:
        previous_hash = hashlib.sha256(
            _BEACON_HISTORY[-1].value + _BEACON_HISTORY[-1].previous_hash
        ).digest()
    elif previous_hash is None:
        previous_hash = b"\x00" * 32

    quantum_seed = _quantum_random_bytes(32)

    timestamp = time.time()
    hasher = hashlib.sha256()
    hasher.update(quantum_seed)
    hasher.update(previous_hash)
    hasher.update(round_number.to_bytes(8, "big"))
    hasher.update(int(timestamp).to_bytes(8, "big"))
    beacon_hash = hasher.digest()

    proof = {
        "quantum_seed": quantum_seed.hex(),
        "round": round_number,
        "algorithm": "SHA-256",
        "previous_hash": previous_hash.hex(),
    }

    beacon = BeaconValue(
        value=beacon_hash,
        round_number=round_number,
        timestamp=timestamp,
        previous_hash=previous_hash,
        proof=proof,
        quantum_seed=True,
    )

    _BEACON_HISTORY.append(beacon)
    return beacon


def verify_beacon(beacon: BeaconValue) -> bool:
    if beacon.round_number < 1:
        return False

    if beacon.previous_hash != b"\x00" * 32 and beacon.round_number > 1:
        expected_prev_index = beacon.round_number - 2
        if expected_prev_index < len(_BEACON_HISTORY):
            prev_beacon = _BEACON_HISTORY[expected_prev_index]
            expected_prev = hashlib.sha256(
                prev_beacon.value + prev_beacon.previous_hash
            ).digest()
            if beacon.previous_hash != expected_prev:
                return False

    quantum_seed = bytes.fromhex(beacon.proof.get("quantum_seed", ""))
    hasher = hashlib.sha256()
    hasher.update(quantum_seed)
    hasher.update(beacon.previous_hash)
    hasher.update(beacon.round_number.to_bytes(8, "big"))
    hasher.update(int(beacon.timestamp).to_bytes(8, "big"))
    recomputed = hasher.digest()

    return recomputed == beacon.value


def get_beacon_history(
    last_n: int | None = None,
) -> List[BeaconValue]:
    if last_n is None:
        return list(_BEACON_HISTORY)
    return list(_BEACON_HISTORY[-last_n:])


def compute_vrf(
    input_data: bytes,
    secret_key: bytes | None = None,
) -> VRFProof:
    if secret_key is None:
        secret_key = secrets.token_bytes(32)

    input_hash = hashlib.sha256(input_data).digest()

    drbg = hashlib.sha512()
    drbg.update(secret_key)
    drbg.update(input_hash)
    output = drbg.digest()[:32]

    proof_data = hashlib.sha256(output + secret_key + input_hash).digest()

    public_key = hashlib.sha256(secret_key + b"vrf_pub").digest()

    return VRFProof(
        input_hash=input_hash,
        output=output,
        proof=proof_data,
        public_key=public_key,
    )
