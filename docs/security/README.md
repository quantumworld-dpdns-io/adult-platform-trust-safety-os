# Security Overview

## Principles
- **Zero Trust**: Verify explicitly, least privilege access, assume breach
- **Defense in Depth**: Multiple independent security layers
- **Privacy by Design**: Data minimization, purpose limitation, ZKP for verification
- **Quantum Readiness**: PQC migration path for all cryptographic operations

## Security Controls

### Authentication & Authorization
- JWT tokens with hybrid PQC signatures (Ed25519 + CRYSTALS-Dilithium)
- Argon2id password hashing (memory-hard, side-channel resistant)
- Multi-factor authentication (TOTP)
- Role-based access control: `admin`, `moderator`, `reviewer`, `user`
- Session management with Redis-backed token store
- OAuth2 delegation support

### Encryption
- **In Transit**: TLS 1.3 with hybrid ECDH + Kyber768 key exchange
- **At Rest**: AES-256-GCM for database columns, S3 SSE-KMS for objects
- **Application Layer**: PQC hybrid encryption for sensitive payloads

### Audit & Compliance
- Merkle-chained append-only audit logs (`src/audit/`)
- Tamper-evident with PQC digital signatures
- Anomaly detection on access patterns
- 7-year retention with automated compliance export
- OWASP Top 10 compliance (see [owasp-top10.md](owasp-top10.md))

### Content Security
- Input validation via Pydantic models
- Parameterized queries (SQLAlchemy ORM)
- Content Security Policy headers
- File upload validation (magic bytes, size limits, type checking)

## Documentation Map
| Topic | File |
|-------|------|
| OWASP Top 10 compliance | [owasp-top10.md](owasp-top10.md) |
| PQC migration guide | [pqc-migration.md](pqc-migration.md) |
| ZKP implementation guide | [zkp-guide.md](zkp-guide.md) |
