# System Architecture Overview

## Components Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API Gateway / Load Balancer                        │
│                         (Nginx + CloudFront CDN + WAF)                       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                         FastAPI Application Layer                            │
│  ┌──────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────────────────┐    │
│  │ Auth/    │ │ Content      │ │ Moderation  │ │ Audit & Compliance   │    │
│  │ RBAC/MFA │ │ Classification│ │ Pipeline    │ │ (Merkle-chained)     │    │
│  └────┬─────┘ └──────┬───────┘ └──────┬──────┘ └──────────┬───────────┘    │
│       │              │                │                     │                │
│  ┌────▼──────────────▼────────────────▼─────────────────────▼───────────┐  │
│  │                     Quantum Security Layer                            │  │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐  │  │
│  │  │ PQC     │  │ ZKP      │  │ QRNG    │  │ QKD    │  │ Hybrid   │  │  │
│  │  │ Kyber/  │  │ Age/     │  │ Random  │  │ BB84   │  │ Classical│  │  │
│  │  │Dilithium│  │Consent/ID│  │ Numbers │  │ Keys   │  │ + PQC    │  │  │
│  │  └─────────┘  └──────────┘  └─────────┘  └────────┘  └──────────┘  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                          Data Layer                                          │
│  ┌──────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────────────────┐    │
│  │ PostgreSQL   │ │ Redis      │ │ Qdrant     │ │ MinIO / S3          │    │
│  │ (RDS)        │ │ (Elasti-   │ │ (Vector    │ │ (Object Storage)    │    │
│  │ Users, Audit │ │  Cache)    │ │  Search)   │ │ Media, Backups      │    │
│  └──────────────┘ └────────────┘ └────────────┘ └─────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                         AI / ML Layer                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────────────────────────────┐    │
│  │ Ollama LLM   │ │ Sentence     │ │ Federated Learning (Flower)      │    │
│  │ (Text/Image  │ │ Transformers │ │ Privacy-preserving model training │    │
│  │  Inference)  │ │ (Embeddings) │ │                                   │    │
│  └──────────────┘ └──────────────┘ └───────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Content Moderation Flow
1. User submits content via API endpoint (`POST /api/v1/content`)
2. API gateway validates JWT, enforces rate limits via WAF
3. Auth middleware extracts identity from PQC-hybrid JWT
4. Content classifier (ensemble: text + image) scores content
5. Moderation pipeline decides: auto-approve, flag for review, or reject
6. Audit event logged with Merkle chain integrity hash
7. Real-time WebSocket notifies connected clients of decision
8. If escalated, item enters human review queue

### Age Verification Flow
1. Client requests age verification challenge
2. Server generates ZKP commitment using Schnorr-like protocol
3. Client proves `age >= minimum` without revealing birth date
4. Server verifies proof via `verify_age_proof()` in `src/quantum/zkp/age_proof.py`
5. Verification token issued (short-lived, scoped)
6. Audit event recorded with Merkle root

### Consent Verification Flow
1. Consent record created via `prove_consent_given()`
2. ZKP proof generated without exposing consent details
3. Third parties verify consent status without seeing underlying data
4. Withdrawal handled via `prove_consent_withdrawn()`

## Security Model

### Defense in Depth
- **Perimeter**: AWS WAF + CloudFront geo-filtering + rate limiting
- **Transport**: TLS 1.3 with CRYSTALS-Kyber hybrid key exchange
- **Application**: RBAC + MFA + session management + input validation
- **Data**: AES-256-GCM encryption at rest, column-level encryption for PII
- **Audit**: Merkle-chained tamper-evident logs with PQC digital signatures
- **Quantum**: PQC migration path via NIST FIPS 203/204/205 compliant algorithms

### Cryptographic Stack
| Layer | Classical | Post-Quantum | Hybrid |
|-------|-----------|--------------|--------|
| Key Exchange | ECDH (P-256) | CRYSTALS-Kyber768 | ECDH + Kyber |
| Signatures | Ed25519 | CRYSTALS-Dilithium3 | Ed25519 + Dilithium |
| Encryption | AES-256-GCM | AES-256 (quantum-resistant) | AES-256-GCM |
| Hashing | SHA-256 | SHA-384 | SHA-256 (adequate) |
| Randomness | CSPRNG | QRNG (Qiskit Aer) | QRNG + CSPRNG fallback |

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | >= 3.12 |
| Web Framework | FastAPI | >= 0.115 |
| ORM | SQLAlchemy (async) | >= 2.0 |
| Database | PostgreSQL (asyncpg) | 16 |
| Cache | Redis | 7.x |
| Vector DB | Qdrant | 1.12 |
| Object Storage | MinIO / S3 | - |
| Task Queue | asyncio + structlog | - |
| Auth | python-jose (JWT) + argon2 | - |
| Cryptography | cryptography lib + OQS | - |
| Quantum | Qiskit + Qiskit Aer | >= 1.3 |
| AI/ML | Ollama + sentence-transformers | - |
| Federated | Flower (flwr) | >= 1.14 |
| Observability | OpenTelemetry + Prometheus | - |
| Container | Docker + Kubernetes | - |
| IaC | Terraform (AWS) | - |
| CI/CD | GitHub Actions | - |
