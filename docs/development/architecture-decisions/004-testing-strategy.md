# ADR-004: Testing Strategy

## Status
Accepted

## Context
A trust and safety platform requires rigorous testing across multiple dimensions: functional correctness, security, performance, and quantum module validity. The testing strategy must cover unit tests, integration tests, end-to-end tests, security tests, and quantum-specific validation.

## Decision

### Test Pyramid
```
         /  E2E  \          <- Few, slow, high confidence
        /----------\
       / Integration \      <- Moderate, test component interaction
      /----------------\
     /     Unit Tests     \  <- Many, fast, isolated
    /----------------------\
```

### Categories and Markers
| Category | Marker | Framework | Purpose |
|----------|--------|-----------|---------|
| Unit | `@pytest.mark.unit` | pytest | Isolated function tests |
| Integration | `@pytest.mark.integration` | pytest + httpx | API + database tests |
| E2E | `@pytest.mark.e2e` | pytest + httpx | Full user workflows |
| Security | `@pytest.mark.security` | pytest + bandit | Auth, crypto, injection |
| Quantum | `@pytest.mark.quantum` | pytest | PQC, ZKP, QRNG correctness |
| Performance | `@pytest.mark.performance` | locust | Load and latency |
| Robot | `@pytest.mark.robot` | Robot Framework | UI/browser tests |

### Tooling
- **pytest** with asyncio mode for async test support
- **pytest-cov** for coverage reporting (target: 80%)
- **ruff** for linting (replaces flake8, isort, black)
- **mypy** with strict mode for type checking
- **bandit** for security static analysis
- **detect-secrets** for secret detection in code
- **pip-audit** for dependency vulnerability scanning
- **Robot Framework** for keyword-driven UI testing
- **Locust** for load testing

### Quantum Testing
- ZKP proofs tested for completeness (honest prover convinces), soundness (cheater rejected), and zero-knowledge property
- PQC operations tested against known test vectors from NIST
- QRNG tested with NIST SP 800-90B entropy tests
- All quantum modules tested with both Qiskit and classical fallback

### Coverage Requirements
- Overall: >= 80%
- Security modules: >= 90%
- Quantum modules: >= 85%

## Alternatives Considered

### Hypothesis (property-based testing)
- **Partially adopted**: Good for ZKP and crypto testing but not used project-wide due to test generation overhead

### Selenium for E2E
- **Rejected**: Robot Framework with RequestsLibrary sufficient for API-focused testing; browser tests out of scope for backend platform

### Mocking quantum hardware
- **Rejected**: Qiskit Aer provides sufficient simulation; mocking would not validate actual quantum circuit behavior

## Consequences
- **Positive**: Comprehensive coverage, automated security scanning, quantum validation
- **Negative**: Test suite takes ~5 minutes for full run; quantum tests require Qiskit dependency
- **Mitigation**: Parallel execution via pytest-xdist; quantum tests are optional marker
