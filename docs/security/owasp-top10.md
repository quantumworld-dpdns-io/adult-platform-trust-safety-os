# OWASP Top 10 Compliance Guide

## A01: Broken Access Control

**Risk**: Unauthorized actions beyond intended permissions.

**Implementation**:
- RBAC enforced at middleware layer (`src/auth/rbac.py`)
- Every endpoint declares required roles via decorators
- Resource-level ownership checks before mutation
- Admin actions require elevated MFA verification

```python
# Example: moderator-only endpoint
@router.post("/moderation/{content_id}/approve")
async def approve_content(
    content_id: UUID,
    current_user: User = Depends(require_role("moderator")),
):
    ...
```

**Testing**: Unit tests verify role enforcement; integration tests validate cross-role access denial.

## A02: Cryptographic Failures

**Risk**: Weak algorithms, exposed keys, insufficient encryption.

**Implementation**:
- TLS 1.3 mandatory (no fallback to 1.2)
- Hybrid PQC: classical + post-quantum algorithms combined
- AES-256-GCM for all data at rest
- Key rotation every 90 days via AWS KMS
- Argon2id for password hashing (memory-hard)
- No hardcoded secrets; environment-based configuration
- `detect-secrets` in pre-commit hooks

**Monitoring**: Alert on algorithm downgrade attempts, key age > 90 days.

## A03: Injection

**Risk**: SQL, NoSQL, OS, LDAP injection via untrusted input.

**Implementation**:
- SQLAlchemy ORM with parameterized queries (no raw SQL in application code)
- Pydantic models validate all input before processing
- Structlog sanitizes log output (no user data in log templates)
- Docker container runs as non-root user

```python
# Safe: ORM prevents injection
stmt = select(Content).where(Content.id == content_id)
```

**Testing**: Bandit scans for SQL injection patterns; fuzz testing on API endpoints.

## A04: Insecure Design

**Risk**: Flaws in architecture or design patterns.

**Implementation**:
- Threat modeling per component (see [security-model.md](../architecture/security-model.md))
- ADR process for architectural decisions
- Separation of concerns: auth, moderation, audit are independent modules
- Circuit breakers on external service calls
- Graceful degradation when quantum modules unavailable

## A05: Security Misconfiguration

**Risk**: Default credentials, unnecessary features, verbose errors.

**Implementation**:
- Docker images based on minimal base images (Alpine)
- Health checks on all services
- No debug mode in production
- Structured error responses (no stack traces exposed)
- Infrastructure as Code (Terraform) ensures consistent configuration

```yaml
# docker-compose.yml: no default passwords in production
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD}  # from .env
```

**Testing**: `pip-audit` for dependency vulnerabilities; `bandit` for code issues.

## A06: Vulnerable and Outdated Components

**Risk**: Known CVEs in dependencies.

**Implementation**:
- `pip-audit` runs in CI on every PR
- `dependabot` configured for automated updates
- `pyproject.toml` pins minimum versions with compatible releases
- Quantum dependencies (qiskit) are optional and isolated
- Monthly dependency review cadence

## A07: Identification and Authentication Failures

**Risk**: Brute force, credential stuffing, session hijacking.

**Implementation**:
- Argon2id password hashing (not bcrypt, not PBKDF2)
- Rate limiting: 5 failed login attempts per 15 minutes per IP
- Account lockout after 10 failed attempts (configurable)
- JWT tokens with short expiry (15 min access, 7 day refresh)
- Session invalidation on password change
- MFA required for admin and moderator roles

## A08: Software and Data Integrity Failures

**Risk**: Unauthorized code changes, supply chain attacks, tampered data.

**Implementation**:
- Merkle-chained audit logs (tamper-evident)
- PQC digital signatures on log batches
- Content integrity hashing (BLAKE3)
- Signed Docker images in CI/CD
- Pre-commit hooks: `ruff`, `bandit`, `detect-secrets`
- Branch protection on main (required reviews, status checks)

## A09: Security Logging and Monitoring Failures

**Risk**: Undetected breaches, insufficient forensic data.

**Implementation**:
- OpenTelemetry traces on every request
- Prometheus metrics for security-relevant events
- Structured logging with correlation IDs
- Anomaly detection on audit patterns (`src/audit/anomaly.py`)
- Alerting on: failed auth spikes, privilege escalation attempts, data exfiltration patterns
- CloudWatch + Grafana dashboards

## A10: Server-Side Request Forgery (SSRF)

**Risk**: Server makes requests to unintended internal/external resources.

**Implementation**:
- Input validation on all URL parameters
- Allowlist of permitted external domains
- Network segmentation: application cannot reach metadata endpoints
- Egress filtering in Kubernetes network policies
- DNS resolution validation before outbound requests

## Verification
- `bandit` static analysis in CI (`pyproject.toml` configured)
- `pytest` security markers for security-focused tests
- Annual penetration testing (manual + automated)
- Bug bounty program (planned)
