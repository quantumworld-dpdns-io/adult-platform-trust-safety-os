# ADR-001: Technology Stack

## Status
Accepted

## Context
The adult-platform-trust-safety-os requires a technology stack that supports:
- High-throughput content moderation
- Real-time WebSocket communication
- Cryptographic operations (PQC, ZKP)
- Async database operations
- Extensible AI/ML pipeline

## Decision

### Backend: Python 3.12+ with FastAPI
- **Rationale**: Native async support, Pydantic validation, OpenAPI auto-generation, large ecosystem
- **Alternatives considered**: Go (better performance, slower development), Node.js (less mature crypto ecosystem)

### ORM: SQLAlchemy 2.0 (async)
- **Rationale**: Mature, well-documented, async support via asyncpg, Pydantic integration
- **Alternatives considered**: Tortoise ORM (less mature), raw SQL (no type safety)

### Database: PostgreSQL 16
- **Rationale**: JSONB support for flexible metadata, row-level security, mature replication
- **Alternatives considered**: CockroachDB (overhead), SQLite (no concurrent writes)

### Cache: Redis 7
- **Rationale**: Session store, rate limiting, pub/sub for WebSocket, battle-tested
- **Alternatives considered**: DragonflyDB (compatible but less ecosystem)

### Authentication: python-jose + argon2
- **Rationale**: JWT with Ed25519 support, argon2id is memory-hard (ASIC-resistant)
- **Alternatives considered**: PyJWT (no Ed25519), bcrypt (not memory-hard)

### Cryptography: cryptography lib + liboqs
- **Rationale**: `cryptography` for classical ops, `liboqs` for PQC with OQS Python bindings
- **Alternatives considered**: pycryptodome (no PQC), pqcrypto (less maintained)

### Quantum: Qiskit + Qiskit Aer
- **Rationale**: Most mature quantum SDK, local simulation, circuit-based model
- **Alternatives considered**: Cirq (Google-centric), PennyLane (ML-focused)

### AI: Ollama + sentence-transformers
- **Rationale**: Local inference (no API dependency), good performance, model variety
- **Alternatives considered**: OpenAI API (cost, privacy), TorchServe (complexity)

### Observability: OpenTelemetry + Prometheus
- **Rationale**: Vendor-neutral tracing, Prometheus for metrics, Grafana for dashboards
- **Alternatives considered**: Datadog (cost), Jaeger (metrics separate)

## Consequences
- **Positive**: Fast development cycle, strong type safety, excellent async support
- **Negative**: Python GIL limits CPU-bound parallelism (mitigated by async I/O and external workers)
- **Risk**: Quantum dependencies are optional and degrade gracefully to classical equivalents
