# Testing Guide

## Test Categories

| Category | Marker | Location | Purpose |
|----------|--------|----------|---------|
| Unit | `@pytest.mark.unit` | `tests/unit/` | Isolated function/class tests |
| Integration | `@pytest.mark.integration` | `tests/integration/` | Multi-component interaction |
| E2E | `@pytest.mark.e2e` | `tests/e2e/` | Full user workflows |
| Security | `@pytest.mark.security` | `tests/security/` | Auth, crypto, injection |
| Quantum | `@pytest.mark.quantum` | `tests/quantum/` | PQC, ZKP, QRNG, QKD |
| Performance | `@pytest.mark.performance` | `tests/perf/` | Load, latency, throughput |
| Robot | `@pytest.mark.robot` | `tests/robot/` | Robot Framework UI tests |

## Running Tests

```bash
# All tests
pytest

# By category
pytest -m unit
pytest -m integration
pytest -m quantum
pytest -m security

# With coverage
pytest --cov=src --cov-report=html

# Parallel execution
pytest -n auto

# Specific file
pytest tests/quantum/test_age_proof.py -v
```

## Unit Testing

### Pattern
```python
import pytest
from src.quantum.zkp.age_proof import generate_keypair, prove_age_over, verify_age_proof

@pytest.mark.unit
class TestAgeProof:
    def test_valid_proof_verifies(self):
        pk, pub = generate_keypair()
        proof = prove_age_over(pk, pub, 18)
        assert verify_age_proof(proof, pub) is True

    def test_invalid_proof_rejects(self):
        pk, pub = generate_keypair()
        proof = prove_age_over(pk, pub, 18)
        _, wrong_pub = generate_keypair()
        assert verify_age_proof(proof, wrong_pub) is False
```

### Fixtures
```python
# conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

## Integration Testing

```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
async def test_content_moderation_flow(client: AsyncClient):
    # Submit content
    resp = await client.post("/api/v1/content", json={
        "content_type": "TEXT",
        "raw_content": "Test content",
    })
    assert resp.status_code == 201
    content_id = resp.json()["id"]

    # Check moderation status
    resp = await client.get(f"/api/v1/content/{content_id}")
    assert resp.json()["status"] in ["PENDING", "APPROVED", "REJECTED"]
```

## Robot Framework Testing

### Setup
```bash
pip install robotframework robotframework-requests robotframework-sshlibrary
```

### Example Test
```robotframework
*** Settings ***
Library    RequestsLibrary
Library    Collections

*** Variables ***
${BASE_URL}    http://localhost:8000

*** Test Cases ***
Health Check
    Create Session    api    ${BASE_URL}
    ${resp}=    GET On Session    api    /health
    Should Be Equal As Integers    ${resp.status_code}    200

Content Submission
    Create Session    api    ${BASE_URL}
    ${body}=    Create Dictionary    content_type=TEXT    raw_content=Test
    ${resp}=    POST On Session    api    /api/v1/content    json=${body}
    Should Be Equal As Integers    ${resp.status_code}    201
```

### Run
```bash
robot tests/robot/
```

## Performance Testing

### Load Test (Locust)
```python
from locust import HttpUser, task

class TrustSafetyUser(HttpUser):
    @task
    def health_check(self):
        self.client.get("/health")

    @task(3)
    def submit_content(self):
        self.client.post("/api/v1/content", json={
            "content_type": "TEXT",
            "raw_content": "Performance test content",
        })
```

### Run
```bash
locust -f tests/perf/locustfile.py --host=http://localhost:8000
```

## Security Testing

### Static Analysis
```bash
# Bandit security linter
bandit -r src/ -c pyproject.toml

# Dependency audit
pip-audit

# Secret detection
detect-secrets scan
```

### Crypto Testing
```python
@pytest.mark.security
def test_pqc_signature_resists_tampering():
    from src.quantum.pqc.digital_signature import generate_keypair, sign, verify
    kp = generate_keypair()
    sig = sign(b"message", kp.private_key)
    # Tamper with signature
    tampered = bytearray(sig.signature)
    tampered[0] ^= 0xFF
    assert verify(b"message", bytes(tampered), kp.public_key) is False
```

## Test Configuration

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "security: Security tests",
    "quantum: Quantum computing tests",
    "performance: Performance tests",
    "slow: Slow tests",
    "robot: Robot Framework tests",
]
addopts = "-v --tb=short --strict-markers -x"
```
