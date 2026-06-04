# Post-Quantum Cryptography Migration Guide

## Current Cryptographic State

| Component | Algorithm | Quantum Risk | PQC Replacement |
|-----------|-----------|-------------|-----------------|
| JWT Signatures | Ed25519 | HIGH | CRYSTALS-Dilithium3 |
| JWT Key Exchange | ECDH P-256 | HIGH | CRYSTALS-Kyber768 |
| Database Encryption | AES-256-GCM | LOW | AES-256 (adequate) |
| Password Hashing | Argon2id | LOW | Argon2id (adequate) |
| TLS | ECDHE + AES-256-GCM | HIGH | Hybrid ECDHE + Kyber |
| Audit Signatures | Ed25519 | HIGH | CRYSTALS-Dilithium3 |
| Content Hashing | SHA-256 | LOW | SHA-384 (optional) |
| API Key HMAC | SHA-256 | LOW | SHA-256 (adequate) |

## Migration Approach: Hybrid Mode

During the transition period, the platform uses hybrid cryptography combining classical and post-quantum algorithms. This ensures:
- **Backward compatibility** with classical-only clients
- **Quantum resistance** if PQC algorithms hold their security promises
- **Graceful degradation** if PQC implementations have issues

### Hybrid Signatures
```python
from src.quantum.pqc.hybrid_crypto import hybrid_sign, hybrid_verify

# Both Ed25519 AND Dilithium3 must verify for the signature to be valid
signature = hybrid_sign(message, hybrid_keypair)
is_valid = hybrid_verify(signature, hybrid_keypair)
```

### Hybrid Key Exchange
```python
from src.quantum.pqc.key_encapsulation import generate_keypair, encapsulate

# Kyber768 key encapsulation
kyber_kp = generate_keypair("Kyber768")
encapsulation = encapsulate(kyber_kp.public_key)
shared_secret = encapsulation.shared_secret
```

## Migration Steps

### Phase 1: Inventory (Complete)
1. Run `analyze_current_crypto()` from `src/quantum/pqc/migration.py`
2. Catalog all cryptographic assets and their quantum risk levels
3. Map each algorithm to its NIST PQC replacement

### Phase 2: Hybrid Deployment (In Progress)
1. Deploy hybrid JWT signing (Ed25519 + Dilithium3)
2. Enable hybrid TLS endpoints (ECDHE + Kyber768)
3. Sign audit logs with hybrid signatures
4. Validate with integration tests

### Phase 3: PQC Primary (Planned)
1. Switch to PQC-primary, classical as fallback
2. Monitor performance metrics (key size, latency)
3. Client libraries update to PQC-first

### Phase 4: PQC Only (Future)
1. Remove classical algorithms after ecosystem maturity
2. Require PQC for all connections
3. Archive classical keys for legacy verification

## Key Size Considerations

| Algorithm | Public Key | Private Key | Signature/Ciphertext |
|-----------|-----------|------------|---------------------|
| Ed25519 | 32 B | 32 B | 64 B |
| Dilithium3 | 1,952 B | 4,032 B | 3,293 B |
| ECDH P-256 | 64 B | 32 B | N/A |
| Kyber768 | 1,184 B | 2,400 B | 1,088 B |

**Impact**: PQC keys are 30-60x larger. Plan for increased storage and bandwidth.

## Performance Impact

| Operation | Classical | Hybrid | Overhead |
|-----------|-----------|--------|----------|
| JWT Sign | ~0.1 ms | ~0.3 ms | 3x |
| JWT Verify | ~0.1 ms | ~0.3 ms | 3x |
| TLS Handshake | ~5 ms | ~7 ms | 1.4x |
| Audit Log Sign | ~0.1 ms | ~0.3 ms | 3x |

## Testing
```bash
# Run PQC unit tests
pytest tests/ -m quantum -v

# Run migration validation
python -c "from src.quantum.pqc.migration import generate_migration_plan; print('OK')"
```

## References
- NIST FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism (ML-KEM)
- NIST FIPS 204: Module-Lattice-Based Digital Signature (ML-DSA)
- NIST FIPS 205: Stateless Hash-Based Digital Signature (SLH-DSA)
- [migration.py](../../src/quantum/pqc/migration.py) - Automated migration toolkit
