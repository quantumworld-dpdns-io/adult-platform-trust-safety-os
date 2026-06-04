# Quantum Computing Integration

## Overview

The platform integrates quantum computing across five domains: cryptographic security (PQC), zero-knowledge proofs (ZKP), quantum random number generation (QRNG), quantum key distribution (QKD), and quantum machine learning (QML).

## Qiskit Integration

### Setup
```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit_aer import AerSimulator
```

### Capabilities
- Quantum circuit simulation via Qiskit Aer (local backend)
- QRNG generation using Hadamard gate superposition
- BB84 QKD protocol simulation
- QML feature maps and variational classifiers

### Limitations
- Simulation only (no physical quantum hardware required)
- Classical fallback when Qiskit is unavailable
- All quantum modules degrade gracefully to classical equivalents

## Post-Quantum Cryptography (PQC)

### NIST Standards Compliance
| Standard | Algorithm | Usage | Module |
|----------|-----------|-------|--------|
| FIPS 203 (ML-KEM) | CRYSTALS-Kyber768 | Key encapsulation | `src/quantum/pqc/key_encapsulation.py` |
| FIPS 204 (ML-DSA) | CRYSTALS-Dilithium3 | Digital signatures | `src/quantum/pqc/digital_signature.py` |
| FIPS 205 (SLH-DSA) | SPHINCS+ | Hash-based signatures (backup) | Planned |

### Hybrid Approach
```python
from src.quantum.pqc.hybrid_crypto import hybrid_sign, hybrid_verify

# Sign with classical + PQC
sig = hybrid_sign(message, hybrid_keypair)

# Verify requires both classical AND PQC to pass
valid = hybrid_verify(sig, hybrid_keypair)
```

### Migration Toolkit
`src/quantum/pqc/migration.py` provides:
- `analyze_current_crypto()` - Risk assessment of existing algorithms
- `generate_migration_plan()` - Task-based migration roadmap
- `get_pqc_recommendations()` - Per-algorithm replacement guidance
- `migration_checklist()` - Step-by-step migration verification

## Zero-Knowledge Proofs (ZKP)

### Age Verification
**File**: `src/quantum/zkp/age_proof.py`

```python
from src.quantum.zkp.age_proof import (
    generate_keypair,
    prove_age_over,
    verify_age_proof,
)

# Setup
private_key, public_key = generate_keypair()

# Prove age >= 18 without revealing birth date
proof = prove_age_over(
    birth_date_hash=hash_birth_date(date_of_birth),
    private_key=private_key,
    public_key=public_key,
    current_date_hash=hash_current_date(),
    minimum_age=18,
)

# Verify (server-side, no PII needed)
valid = verify_age_proof(proof, public_key)
```

**Proof types**:
- `age_over`: Proves `age >= minimum_age`
- `age_under`: Proves `age <= maximum_age`
- `age_range`: Proves `min_age <= age <= max_age` (combined proof)

### Consent Verification
**File**: `src/quantum/zkp/consent_proof.py`

```python
from src.quantum.zkp.consent_proof import (
    prove_consent_given,
    verify_consent_proof,
)

proof = prove_consent_given(
    consent_id="c123",
    consent_type="data_processing",
    private_key=key,
    public_key=pub,
    timestamp=int(time.time()),
)

valid = verify_consent_proof(proof, pub)
```

### Identity Verification
**File**: `src/quantum/zkp/identity_proof.py`

```python
from src.quantum.zkp.identity_proof import (
    create_identity_commitment,
    prove_identity_without_pii,
    verify_identity_proof,
)

commitment = create_identity_commitment(
    private_key=key,
    public_key=pub,
    pii_data={"name": "...", "ssn": "..."},
    salt=secret_salt,
)

proof = prove_identity_without_pii(key, pub, commitment)
valid = verify_identity_proof(proof, commitment)
```

## Quantum Random Number Generation (QRNG)

**File**: `src/quantum/circuits/qrng.py`

```python
from src.quantum.circuits.qrng import (
    generate_random_bytes,
    generate_random_bits,
    nist_sp_800_90b_tests,
)

# Generate 32 quantum-random bytes
random_bytes = generate_random_bytes(32)

# NIST entropy validation
bits = generate_random_bits(4096)
results = nist_sp_800_90b_tests(bits)
```

**Properties**:
- Hadamard gate creates uniform superposition
- Measurement collapses to truly random bits
- Falls back to `secrets` module when Qiskit unavailable
- NIST SP 800-90B min-entropy testing

## Quantum Key Distribution (QKD)

**File**: `src/quantum/circuits/qkd.py`

```python
from src.quantum.circuits.qkd import key_generation

result = key_generation(
    num_qubits=128,
    error_threshold=0.11,
    key_length=256,
)

if result.shared_key:
    # Use result.shared_key for symmetric encryption
    pass
```

**BB84 Protocol Steps**:
1. Alice prepares qubits in random bases (rectilinear/diagonal)
2. Bob measures in random bases
3. Classical sifting: keep only matching-basis bits
4. Error estimation: check if eavesdropper present
5. Privacy amplification: derive final key via SHA-256

## Quantum ML (QML)

**Directory**: `src/quantum/qml/`

| Module | Purpose |
|--------|---------|
| `feature_map.py` | Data encoding into quantum states |
| `quantum_kernel.py` | Quantum kernel estimation |
| `variational_classifier.py` | Parameterized quantum circuit classifier |
| `qaoa_optimizer.py` | QAOA for combinatorial optimization |

## Architecture Decision
See [ADR-002](../development/architecture-decisions/002-quantum-integration.md) for the decision record on quantum integration.
