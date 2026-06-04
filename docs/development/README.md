# Development Setup Guide

## Prerequisites
- Python >= 3.12
- Docker + Docker Compose
- Git
- Make (optional, for convenience targets)

## Quick Start
```bash
git clone https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os.git
cd adult-platform-trust-safety-os

# Install dependencies
pip install -e ".[dev,quantum,ai]"

# Start infrastructure
docker compose up -d postgres redis qdrant minio ollama

# Run migrations
alembic upgrade head

# Start dev server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure
```
src/
  api/          # FastAPI routes and middleware
  auth/         # JWT, RBAC, MFA, OAuth2
  audit/        # Merkle-chained audit logging
  moderation/   # Content moderation pipeline
  quantum/      # PQC, ZKP, QRNG, QKD, QML
  ai/           # Classifiers, RAG, federated learning
  data/         # Database, Redis, Qdrant, MinIO
  config/       # Settings and logging
  cli/          # CLI interface (typer)
tests/
  unit/         # Unit tests
  integration/  # Integration tests
  e2e/          # End-to-end tests
  security/     # Security-focused tests
  quantum/      # Quantum module tests
deploy/
  terraform/    # AWS infrastructure
  kubernetes/   # K8s manifests
  helm/         # Helm charts
  docker/       # Dockerfiles
sdk/
  python/       # Python SDK
  javascript/   # JavaScript SDK
```

## Makefile Targets
```bash
make dev          # Start dev server with auto-reload
make test         # Run all tests
make test-unit    # Run unit tests only
make lint         # Run ruff linter
make typecheck    # Run mypy
make format       # Auto-format code
make security     # Run bandit + detect-secrets
```

## IDE Setup
- VS Code: Use Python extension with ruff and mypy
- PyCharm: Configure Python interpreter from `.venv/`
- Pre-commit hooks: `pre-commit install`

## Environment Variables
Copy `.env.example` to `.env` and configure:
```bash
DATABASE_URL=postgresql+asyncpg://trust_safety:dev@localhost:5432/trust_safety_dev
REDIS_URL=redis://localhost:6379/0
JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem
```

## Architecture Decisions
See [architecture-decisions/](architecture-decisions/) for ADRs documenting key design choices.
