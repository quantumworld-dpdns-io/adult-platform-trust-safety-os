# Quantum Computing Overview

## Modules

| Module | Directory | Purpose |
|--------|-----------|---------|
| PQC | `src/quantum/pqc/` | Post-quantum cryptography (Kyber, Dilithium, hybrid) |
| ZKP | `src/quantum/zkp/` | Zero-knowledge proofs (age, consent, identity) |
| Circuits | `src/quantum/circuits/` | QRNG, QKD (BB84), superdense coding, teleportation |
| QML | `src/quantum/qml/` | Quantum ML: kernels, variational classifiers, QAOA |
| Audit | `src/quantum/audit/` | Quantum-secured audit chain and PQC signing |
| Beacon | `src/quantum/beacon/` | Verifiable random functions and quantum random beacon |
| CUDA-Q | `src/quantum/cudaq/` | CUDA-Q runtime integration (GPU-accelerated quantum) |

## Quick Links
- [PQC Migration Guide](../security/pqc-migration.md)
- [ZKP Implementation Guide](../security/zkp-guide.md)
- [Quantum Integration Architecture](../architecture/quantum-integration.md)

## Getting Started
```python
# QRNG
from src.quantum.circuits.qrng import generate_random_bytes
random_bytes = generate_random_bytes(32)

# PQC Key Encapsulation
from src.quantum.pqc.key_encapsulation import generate_keypair, encapsulate
kp = generate_keypair()
enc = encapsulate(kp.public_key)

# ZKP Age Proof
from src.quantum.zkp.age_proof import generate_keypair, prove_age_over, verify_age_proof
pk, pub = generate_keypair()
proof = prove_age_over(hash_birth_date, pk, pub, hash_current_date, 18)
valid = verify_age_proof(proof, pub)
```

## Fallback Behavior
All quantum modules gracefully degrade when Qiskit or liboqs are unavailable:
- QRNG falls back to Python `secrets` module
- PQC uses mock implementations that match API signatures
- ZKP uses pure Python modular arithmetic (no external dependencies)
