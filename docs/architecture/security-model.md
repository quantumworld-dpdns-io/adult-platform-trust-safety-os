# Security Model

## Threat Model

### Assets Under Protection
- **User PII**: Names, dates of birth, government IDs, email addresses
- **Content Data**: Uploaded media, text, metadata
- **Consent Records**: Legal consent attestations
- **Audit Logs**: Tamper-evident records of all actions
- **Cryptographic Keys**: JWT signing keys, PQC keys, encryption keys
- **Session Tokens**: Active user sessions

### Threat Actors
| Actor | Capability | Motivation |
|-------|-----------|------------|
| External Attacker | Network access, exploit kits | Data theft, platform abuse |
| Quantum Computer Owner | Shor's algorithm, Grover's | Break encryption, forge signatures |
| Malicious Insider | Authenticated access | Data exfiltration, tampering |
| State-level Adversary | Advanced persistent threat | Long-term surveillance |
| Automated Bots | High-volume requests | Content spam, credential stuffing |

### Attack Surfaces
1. **API endpoints** - Injection, auth bypass, mass assignment
2. **Authentication** - Credential stuffing, token theft, session hijacking
3. **Content pipeline** - Malicious uploads, prompt injection, model evasion
4. **Cryptographic layer** - Key compromise, algorithm downgrade, side-channel
5. **Infrastructure** - Container escape, supply chain, misconfiguration

## Defense in Depth

### Layer 1: Perimeter (AWS WAF + CloudFront)
- Geo-restricted access (configurable per jurisdiction)
- Rate limiting: 100 req/min per IP, 1000 req/min per API key
- SQL injection and XSS rule sets
- Bot detection and CAPTCHA challenge
- DDoS protection via AWS Shield

### Layer 2: Transport (TLS 1.3 + PQC Hybrid)
- TLS 1.3 required on all endpoints
- Hybrid key exchange: ECDH P-256 + CRYSTALS-Kyber768
- Certificate pinning for mobile clients
- HSTS with 1-year max-age

### Layer 3: Application (Auth + RBAC + Validation)
- JWT access tokens (RS256 + hybrid PQC signatures)
- Role-based access control: `admin`, `moderator`, `reviewer`, `user`
- Multi-factor authentication (TOTP-based)
- Session management with Redis-backed token store
- Input validation via Pydantic models
- Parameterized queries (SQLAlchemy ORM)

### Layer 4: Data (Encryption at Rest)
- AES-256-GCM for all PII columns
- PostgreSQL TDE (Transparent Data Encryption) on RDS
- Redis AUTH + TLS for cache layer
- S3 SSE-KMS for object storage
- Key rotation every 90 days

### Layer 5: Audit (Tamper-Evident Logs)
- Merkle-chained audit events (`src/audit/merkle.py`)
- PQC digital signatures on log batches
- Append-only audit table with row-level security
- 7-year retention with automated export
- Anomaly detection on audit patterns

### Layer 6: Quantum (Future-Proof)
- NIST FIPS 203 (ML-KEM) for key encapsulation
- NIST FIPS 204 (ML-DSA) for digital signatures
- NIST FIPS 205 (SLH-DSA) for hash-based signatures
- QRNG for cryptographic randomness
- BB84 QKD for symmetric key distribution

## PQC Migration Strategy

### Current State
- Classical algorithms: Ed25519 (signatures), ECDH (key exchange), AES-256-GCM (encryption)
- PQC implementations available in `src/quantum/pqc/` with OQS fallback
- Hybrid mode operational: classical + PQC combined

### Migration Phases
1. **Inventory** (Complete): Catalog all cryptographic assets
2. **Hybrid Deployment** (In Progress): Deploy classical+PQC alongside each other
3. **PQC Primary** (Planned): Switch to PQC-primary, classical as fallback
4. **PQC Only** (Future): Remove classical algorithms after ecosystem maturity

### Algorithm Mapping
| Current | PQC Replacement | NIST Standard | Key Size |
|---------|----------------|---------------|----------|
| RSA-2048 | CRYSTALS-Kyber768 | FIPS 203 (ML-KEM) | 1,184 B pub |
| ECDSA P-256 | CRYSTALS-Dilithium3 | FIPS 204 (ML-DSA) | 1,952 B pub |
| Ed25519 | CRYSTALS-Dilithium3 | FIPS 204 (ML-DSA) | 1,952 B pub |
| ECDH P-256 | CRYSTALS-Kyber768 | FIPS 203 (ML-KEM) | 1,184 B pub |
| AES-128 | AES-256 | N/A | 32 B key |
| SHA-256 | SHA-384 | N/A | 48 B digest |

### Implementation Details
- Hybrid crypto in `src/quantum/pqc/hybrid_crypto.py`
- Key encapsulation in `src/quantum/pqc/key_encapsulation.py`
- Digital signatures in `src/quantum/pqc/digital_signature.py`
- Migration toolkit in `src/quantum/pqc/migration.py`

## ZKP Usage

### Age Verification
- **Protocol**: Schnorr-like proof of knowledge over discrete log
- **Implementation**: `src/quantum/zkp/age_proof.py`
- **Proof types**: `age_over`, `age_under`, `age_range`
- **Properties**: Zero-knowledge (no birth date revealed), non-interactive, non-forgeable
- **Flow**: Prover generates commitment -> challenge -> response; verifier checks algebraic relation

### Consent Verification
- **Protocol**: ZKP of consent state (granted/withdrawn) without revealing consent details
- **Implementation**: `src/quantum/zkp/consent_proof.py`
- **Properties**: Proves consent existence and status without exposing consent record
- **Use case**: Third-party verification of user consent without data sharing

### Identity Verification
- **Protocol**: ZKP of identity commitment membership
- **Implementation**: `src/quantum/zkp/identity_proof.py`
- **Proof types**: `identity`, `group_membership`
- **Properties**: Proves identity without revealing PII; proves group membership without listing members
- **Use case**: Age-gated content access, platform eligibility verification

## Compliance Mapping
| Regulation | Security Control | Implementation |
|-----------|-----------------|----------------|
| GDPR Art. 25 | Data minimization | ZKP age/identity verification |
| GDPR Art. 32 | Encryption | AES-256-GCM at rest, TLS 1.3 in transit |
| GDPR Art. 33 | Breach notification | Audit logging + alerting pipeline |
| CCPA | Right to delete | Retention policies + secure deletion |
| SOC 2 | Access control | RBAC + MFA + session management |
| NIST 800-53 | Audit logging | Merkle-chained tamper-evident logs |
