# ADR-003: Security Model

## Status
Accepted

## Context
The platform handles sensitive adult content data requiring the highest security standards. The threat model includes quantum adversaries, malicious insiders, and state-level attackers. Regulatory compliance (GDPR, CCPA, SOC 2) mandates specific security controls.

## Decision

### Defense in Depth (6 Layers)
1. **Perimeter**: AWS WAF + CloudFront for DDoS protection, rate limiting, geo-filtering
2. **Transport**: TLS 1.3 with hybrid ECDH + Kyber768 key exchange
3. **Application**: JWT with hybrid PQC signatures, RBAC, MFA, input validation
4. **Data**: AES-256-GCM encryption at rest, column-level PII encryption
5. **Audit**: Merkle-chained tamper-evident logs with PQC signatures
6. **Quantum**: Full PQC migration path, ZKP for privacy-preserving verification

### Authentication
- **Passwords**: Argon2id (memory-hard, 64MB, 3 iterations, parallelism 4)
- **Tokens**: JWT with Ed25519 + CRYSTALS-Dilithium3 hybrid signatures
- **MFA**: TOTP-based (RFC 6238)
- **Sessions**: Redis-backed with 15-minute access token, 7-day refresh token

### Authorization
- **Model**: Role-based access control (RBAC)
- **Roles**: `admin`, `moderator`, `reviewer`, `user`
- **Principle**: Least privilege; admin actions require MFA re-verification

### Encryption Strategy
- **At Rest**: AES-256-GCM for PII columns, RDS TDE, S3 SSE-KMS
- **In Transit**: TLS 1.3 mandatory, HSTS with 1-year max-age
- **Application**: Hybrid PQC encryption for sensitive payloads

### Audit Trail
- **Format**: Merkle-chained append-only events
- **Integrity**: PQC digital signatures on log batches
- **Retention**: 7 years with automated compliance export
- **Anomaly Detection**: Pattern analysis on access and modification events

## Alternatives Considered

### Attribute-Based Access Control (ABAC)
- **Rejected**: RBAC simpler to implement and audit; ABAC overhead not justified for current role complexity

### Client-side encryption
- **Rejected**: Server needs to process content for moderation; client-side encryption would prevent analysis

### No PQC during transition
- **Rejected**: "Harvest now, decrypt later" attacks make early PQC adoption critical

## Consequences
- **Positive**: Comprehensive protection against current and future threats
- **Negative**: Increased complexity, larger keys, higher latency for crypto operations
- **Compliance**: Aligns with GDPR Art. 25 (privacy by design), Art. 32 (encryption), SOC 2 CC6.1
