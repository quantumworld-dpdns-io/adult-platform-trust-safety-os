"""Security tests: SQL/NoSQL injection prevention."""

from __future__ import annotations

import pytest

from src.security.api.input_validator import InputValidator


pytestmark = [pytest.mark.security]


class TestSQLInjectionPrevention:
    def setup_method(self):
        self.validator = InputValidator()

    def test_sql_injection_in_email(self):
        payloads = [
            "admin@example.com'; DROP TABLE users; --",
            "test@example.com' OR '1'='1",
            "user@test.com\"; INSERT INTO users VALUES('hacker','pass'); --",
            "a' UNION SELECT * FROM users --",
            "admin'/*",
            "test'; DELETE FROM users WHERE 1=1; --",
        ]
        for payload in payloads:
            valid, msg = self.validator.validate_email(payload)
            assert not valid, f"Should reject SQL injection in email: {payload}"

    def test_sql_injection_in_string_fields(self):
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "Robert'); DROP TABLE students;--",
            "admin'--",
            "' UNION SELECT password FROM users--",
            "1; UPDATE users SET role='admin' WHERE id=1",
        ]
        for payload in payloads:
            sanitized = self.validator.sanitize_string(payload, max_length=100)
            assert "DROP TABLE" not in sanitized
            assert "DELETE FROM" not in sanitized
            assert "UPDATE users" not in sanitized
            assert "UNION SELECT" not in sanitized

    def test_nosql_injection_in_json(self):
        payloads = [
            '{"$gt": ""}',
            '{"$ne": null}',
            '{"$regex": ".*"}',
            '{"email": {"$ne": ""}}',
            '{"$where": "function() { return true; }"}',
        ]
        for payload in payloads:
            valid, result = self.validator.validate_json(payload)
            assert valid, f"Should parse JSON payload: {payload}"
            assert isinstance(result, dict)

    def test_injection_in_url(self):
        payloads = [
            "http://evil.com/'; DROP TABLE users; --",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "http://test.com/../../../etc/passwd",
        ]
        for payload in payloads:
            valid, msg = self.validator.validate_url(payload)
            assert not valid, f"Should reject malicious URL: {payload}"

    def test_injection_in_phone(self):
        payloads = [
            "1'; DROP TABLE users; --",
            "+1-555-123-4567' OR '1'='1",
            "1234567890; DELETE FROM users",
        ]
        for payload in payloads:
            valid, msg = self.validator.validate_phone(payload)
            assert not valid, f"Should reject injection in phone: {payload}"

    def test_injection_in_uuid(self):
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "00000000-0000-0000-0000-000000000000'; --",
        ]
        for payload in payloads:
            valid, msg = self.validator.validate_uuid(payload)
            assert not valid, f"Should reject injection in UUID: {payload}"


@pytest.mark.asyncio
async def test_api_sql_injection_in_register(async_client):
    payloads = [
        {"email": "test@example.com'; DROP TABLE users; --", "username": "test", "password": "secureP@ss123"},
        {"email": "test@test.com", "username": "admin'--", "password": "secureP@ss123"},
        {"email": "test@test.com", "username": "test", "password": "secureP@ss123'; DROP TABLE users; --"},
    ]
    for payload in payloads:
        resp = await async_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code in (401, 422), f"Should reject SQL injection: {payload}"


@pytest.mark.asyncio
async def test_api_sql_injection_in_login(async_client):
    resp = await async_client.post("/api/v1/auth/login", json={
        "email": "admin' OR '1'='1@example.com",
        "password": "' OR '1'='1",
    })
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_api_nosql_injection_in_content(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "nosql@example.com",
        "username": "nosql",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    resp = await async_client.post(
        "/api/v1/content",
        json={
            "content_type": "TEXT",
            "raw_content": '{"$ne": null}',
            "metadata": {"$where": "function() { return true; }"},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (201, 422)
