# Adult Platform Trust & Safety OS

> Moderation backend combining age verification, consent checks, tamper-evident audit logs, quantum-resistant cryptography, and AI-powered content classification.

[![CI](https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os/actions/workflows/ci.yml/badge.svg)](https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os/actions/workflows/ci.yml)
[![Security](https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os/actions/workflows/security.yml/badge.svg)](https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os/actions/workflows/security.yml)
[![Robot Framework](https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os/actions/workflows/robot-framework.yml/badge.svg)](https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os/actions/workflows/robot-framework.yml)
[![codecov](https://codecov.io/gh/quantumworld-dpdns-io/adult-platform-trust-safety-os/graph/badge.svg)](https://codecov.io/gh/quantumworld-dpdns-io/adult-platform-trust-safety-os)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### Core
- **Age Verification** — Document OCR, liveness detection, ZK age proofs
- **Consent Management** — Granular consent with GDPR/CCPA/COPPA compliance
- **Content Moderation** — Multi-modal AI classification (text, image, video, audio)
- **Tamper-Evident Audit Logs** — Merkle tree integrity, chain verification

### Quantum Computing
- **Post-Quantum Cryptography** — CRYSTALS-Kyber KEM, CRYSTALS-Dilithium signatures
- **Zero-Knowledge Proofs** — Age/consent verification without revealing PII
- **Quantum Random Numbers** — NIST SP 800-90B compliant QRNG
- **Quantum Key Distribution** — BB84 protocol implementation
- **Quantum ML** — Variational classifiers, QAOA optimization

### AI/ML
- **Local LLM** — Ollama/llama.cpp integration
- **RAG Pipeline** — Qdrant + embeddings for retrieval-augmented generation
- **Multi-Agent** — LangGraph/CrewAI orchestration
- **Federated Learning** — Flower framework for privacy-preserving training

### Security
- **OWASP Top 10** — Comprehensive protection with Robot Framework tests
- **eBPF Security** — Cilium Tetragon runtime monitoring
- **WASM Plugins** — Sandboxed plugin execution
- **API Security** — Rate limiting, input validation, request signing

### Infrastructure
- **REST API** — FastAPI with OpenAPI documentation
- **CLI** — Typer-based command line interface
- **WebSocket** — Real-time content scanning
- **MCP Server** — Model Context Protocol integration

## Quick Start

```bash
# Clone the repository
git clone https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os.git
cd adult-platform-trust-safety-os

# Start services
docker compose up -d

# Install dependencies
pip install -e ".[dev,full]"

# Run migrations
alembic upgrade head

# Start the server
uvicorn src.api.app:create_app --factory --reload
```

The API is now available at `http://localhost:8000` with docs at `http://localhost:8000/docs`.

## Development

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run OWASP security tests
make test-security

# Lint and format
make lint
make format

# Type checking
make typecheck

# Build Docker image
make docker
```

## Testing

### Unit Tests
```bash
pytest tests/unit -v
```

### Integration Tests
```bash
docker compose up -d
pytest tests/integration -v
```

### Robot Framework Security Tests
```bash
cd tests/robot
robot run_owasp.robot        # OWASP Top 10
robot run_functional.robot    # Functional security
robot run_api_security.robot  # API security
robot run_all.robot           # All security tests
```

### Performance Tests
```bash
locust -f tests/performance/locustfile.py --host http://localhost:8000
```

## Architecture

```
src/
├── api/          # FastAPI REST API + MCP server
├── auth/         # JWT, OAuth2, MFA, RBAC, session management
├── audit/        # Merkle tree audit logs, compliance reporting
├── moderation/   # Content classification, policy engine, queue
├── quantum/      # Qiskit, PQC, ZKP, QRNG, QKD, QML
├── ai/           # Ollama, RAG, classifiers, agents, federated learning
├── data/         # PostgreSQL, Redis, Qdrant, MinIO, DuckDB
├── security/     # OWASP protection, encryption, eBPF, rate limiting
├── web/          # WASM runtime, plugin system
├── commerce/     # Age-gated commerce, fraud detection
├── compliance/   # GDPR, CCPA, COPPA, DSA, SOC2
├── cli/          # Typer CLI
├── config/       # Settings, logging
└── utils/        # Crypto, hashing, serialization
```

## CI/CD

| Pipeline | Trigger | Description |
|----------|---------|-------------|
| CI | Push/PR to main | Lint, typecheck, unit tests, integration tests |
| Security | Push/PR to main | SAST, dependency audit, container scan, Snyk |
| Robot Framework | Push/PR to main | OWASP Top 10, functional, API security tests |
| E2E | Push/PR to main | Full system end-to-end tests |
| Release | Tag push (v*) | Build, sign, publish to PyPI/DockerHub/GHCR |
| Deploy Staging | Push to main | Deploy to K8s staging |
| Performance | Weekly | Load testing, regression detection |

## Technology Stack

- **Language**: Python 3.12+
- **API**: FastAPI + Uvicorn
- **Database**: PostgreSQL (asyncpg) + SQLAlchemy 2.0
- **Cache**: Redis / DragonflyDB
- **Vector DB**: Qdrant
- **Object Storage**: MinIO / S3
- **AI Runtime**: Ollama + llama.cpp
- **Quantum**: Qiskit + CUDA-Q
- **PQC**: liboqs (CRYSTALS-Kyber, Dilithium)
- **Testing**: pytest + Robot Framework
- **CI/CD**: GitHub Actions
- **Deploy**: Docker + Kubernetes + Helm + Terraform

## Contributing

Please read [CONTRIBUTING.md](docs/development/README.md) before opening a pull request.

## License

[MIT](LICENSE)
