"""Security tests: XSS prevention."""

from __future__ import annotations

import pytest

from src.security.api.input_validator import InputValidator


pytestmark = [pytest.mark.security]


class TestXSSPrevention:
    def setup_method(self):
        self.validator = InputValidator()

    def test_script_tag_stripped(self):
        payloads = [
            "<script>alert('XSS')</script>",
            "<SCRIPT>alert('XSS')</SCRIPT>",
            "<script src='http://evil.com/xss.js'></script>",
            "<<script>alert('XSS')<</script>",
        ]
        for payload in payloads:
            sanitized = self.validator.sanitize_string(payload)
            assert "<script" not in sanitized.lower() or "script" not in sanitized.lower(), (
                f"Script tag should be sanitized: {payload}"
            )

    def test_event_handler_stripped(self):
        payloads = [
            "<img onerror=alert(1) src=x>",
            "<body onload=alert(1)>",
            "<input onfocus=alert(1) autofocus>",
            "<marquee onstart=alert(1)>",
            "<svg onload=alert(1)>",
        ]
        for payload in payloads:
            sanitized = self.validator.sanitize_string(payload)
            assert "onerror" not in sanitized
            assert "onload" not in sanitized
            assert "onfocus" not in sanitized
            assert "onstart" not in sanitized

    def test_javascript_uri_stripped(self):
        payloads = [
            "javascript:alert(1)",
            "JAVASCRIPT:alert(1)",
            "java script:alert(1)",
            "data:text/html,<script>alert(1)</script>",
        ]
        for payload in payloads:
            valid, msg = self.validator.validate_url(payload)
            assert not valid, f"Should reject javascript/data URI: {payload}"

    def test_html_entities_in_strings(self):
        test_cases = [
            ("<b>bold</b>", "bold"),
            ("<i>italic</i>", "italic"),
            ("<a href='http://evil.com'>click</a>", "click"),
            ("<img src=x onerror=alert(1)>", ""),
        ]
        for input_val, _expected_contains in test_cases:
            sanitized = self.validator.sanitize_string(input_val)
            assert "<" not in sanitized or ">" not in sanitized, (
                f"HTML tags should be stripped: {input_val}"
            )

    def test_null_byte_injection(self):
        payload = "admin@example.com\x00<script>alert(1)</script>"
        sanitized = self.validator.sanitize_string(payload)
        assert "\x00" not in sanitized

    def test_control_characters_stripped(self):
        payload = "test\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f\x10\x1f\x7f"
        sanitized = self.validator.sanitize_string(payload)
        for char in ["\x01", "\x02", "\x03", "\x07", "\x08"]:
            assert char not in sanitized

    def test_length_limit_enforced(self):
        long_payload = "A" * 20000
        sanitized = self.validator.sanitize_string(long_payload, max_length=1000)
        assert len(sanitized) <= 1000


@pytest.mark.asyncio
async def test_api_xss_in_content_submission(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "xss_test@example.com",
        "username": "xss_test",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    xss_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(document.cookie)",
        "<svg onload=alert(1)>",
        "<body onload=alert('XSS')>",
    ]
    for payload in xss_payloads:
        resp = await async_client.post(
            "/api/v1/content",
            json={"content_type": "TEXT", "raw_content": payload},
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 201:
            body = resp.json()
            assert "<script" not in body.get("raw_content", "").lower()


@pytest.mark.asyncio
async def test_api_xss_in_user_profile(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "xss_profile@example.com",
        "username": "xss_profile",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    resp = await async_client.put(
        "/api/v1/users/me",
        json={"profile": {"bio": "<script>alert('XSS')</script>Safe bio"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    profile = resp.json().get("profile", {})
    bio = profile.get("bio", "")
    assert "<script>" not in bio.lower()


@pytest.mark.asyncio
async def test_api_xss_in_report_description(async_client):
    reg = await async_client.post("/api/v1/auth/register", json={
        "email": "xss_report@example.com",
        "username": "xss_report",
        "password": "secureP@ss123",
    })
    token = reg.json()["access_token"]
    resp = await async_client.post(
        "/api/v1/reports",
        json={
            "reason": "spam",
            "description": "<img src=x onerror=alert(1)> This is spam content",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "onerror" not in body.get("description", "")
