# ADR-002: Quantum Computing Integration

## Status
Accepted

## Context
The platform needs to be quantum-resistant and leverage quantum computing for enhanced security. Quantum computers running Shor's algorithm will break RSA, ECDSA, ECDH, and Ed25519. The platform must migrate to post-quantum algorithms before large-scale quantum computers become available.

## Decision

### Post-Quantum Cryptography (PQC)
- Use **CRYSTALS-Kyber768** (NIST FIPS 203 / ML-KEM) for key encapsulation
- Use **CRYSTALS-Dilithium3** (NIST FIPS 204 / ML-DSA) for digital signatures
- Implement **hybrid mode**: classical + PQC combined for backward compatibility
- Use **liboqs** as the PQC backend with graceful fallback to mock implementations

### Zero-Knowledge Proofs (ZKP)
- Implement Schnorr-like protocols for:
  - Age verification (prove `age >= min` without revealing birth date)
  - Consent verification (prove consent status without revealing details)
  - Identity verification (prove membership without revealing PII)
- Pure Python implementation using modular arithmetic (no trusted setup required)

### Quantum Random Number Generation (QRNG)
- Use Qiskit Aer simulator for quantum randomness
- Hadamard gate on n qubits produces 2^n random bits
- NIST SP 800-90B entropy testing for validation
- Classical CSPRNG fallback when Qiskit unavailable

### Quantum Key Distribution (QKD)
- BB84 protocol simulation for symmetric key generation
- Sifting, error estimation, privacy amplification
- Useful for key distribution in high-security contexts

### Quantum Machine Learning (QML)
- Quantum kernel methods for content classification enhancement
- Variational classifiers for pattern recognition
- QAOA for optimization problems in moderation routing
- All QML features are optional and experimental

## Alternatives Considered

### liboqs-only (no Qiskit)
- **Rejected**: Need Qiskit for QRNG, QKD, and QML circuits
- liboqs provides only KEM and signature operations

### Trusted setup ZK-SNARKs
- **Rejected**: Trusted setup is a single point of failure; Schnorr-like protocols are trustless
- Trade-off: larger proofs but no setup ceremony

### Hardware QRNG
- **Rejected**: Cost and availability; simulation sufficient for platform needs
- Can upgrade to hardware QRNG later without code changes

## Consequences
- **Positive**: Quantum-resistant encryption, privacy-preserving verification, future-proof architecture
- **Negative**: Larger key sizes (30-60x), slightly higher latency for hybrid operations
- **Mitigation**: Graceful fallback to classical when PQC unavailable; performance monitoring
