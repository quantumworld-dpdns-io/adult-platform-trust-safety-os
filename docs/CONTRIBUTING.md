# Contributing to Adult Platform Trust & Safety OS

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Development Setup

1. **Fork and clone** the repository
2. **Install dependencies**: `pip install -e ".[dev,full]"`
3. **Start services**: `docker compose up -d`
4. **Run migrations**: `alembic upgrade head`
5. **Run tests**: `make test`

## Code Standards

- **Python**: 3.12+, type hints required
- **Formatting**: `ruff format` (double quotes, 4-space indent)
- **Linting**: `ruff check` with all rules enabled
- **Type checking**: `mypy --strict`
- **Security**: `bandit` with zero findings

## Testing Requirements

All changes must include:

- **Unit tests** for new functions/classes
- **Integration tests** for API endpoints
- **Robot Framework tests** for security-relevant changes

Run the full test suite before submitting:
```bash
make test
make test-security
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat: add new content classifier`
- `fix: resolve audit chain verification`
- `security: add OWASP A03 injection tests`
- `docs: update quantum computing guide`

## Pull Request Process

1. Create feature branch from `main`
2. Write tests covering your changes
3. Ensure all CI checks pass
4. Request review from maintainers
5. Squash and merge after approval

## Security

For security vulnerabilities, please see [SECURITY.md](docs/security/README.md) or report privately via GitHub Security Advisories.
