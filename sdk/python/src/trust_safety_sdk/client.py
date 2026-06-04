"""SDK client for the Trust & Safety API."""

from __future__ import annotations

import time
from typing import Any

import httpx

from .models import (
    AuditEntry,
    ContentClassification,
    AgeVerification,
    ZKPProof,
)


class TrustSafetyError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


class TrustSafetyClient:
    """Client for the Adult Platform Trust & Safety API."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._build_headers(),
        )
        self._token: str | None = None
        self._token_expiry: float = 0.0

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _auth_headers(self) -> dict[str, str]:
        headers = self._build_headers()
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def authenticate(self, email: str, password: str) -> dict[str, Any]:
        """Authenticate with email/password and store the access token."""
        resp = await self._client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if resp.status_code != 200:
            raise TrustSafetyError(resp.status_code, resp.text)
        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + 900
        return data

    async def register(self, email: str, password: str) -> dict[str, Any]:
        """Register a new user account."""
        resp = await self._client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        if resp.status_code != 201:
            raise TrustSafetyError(resp.status_code, resp.text)
        return resp.json()

    async def scan_content(
        self,
        content_type: str,
        raw_content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ContentClassification:
        """Submit content for moderation and classification."""
        payload: dict[str, Any] = {
            "content_type": content_type,
            "raw_content": raw_content,
        }
        if metadata:
            payload["metadata"] = metadata

        resp = await self._client.post(
            "/api/v1/content",
            json=payload,
            headers=self._auth_headers(),
        )
        if resp.status_code != 201:
            raise TrustSafetyError(resp.status_code, resp.text)
        data = resp.json()
        return ContentClassification(
            content_id=data["id"],
            content_type=data["content_type"],
            status=data["status"],
            moderation_score=data.get("moderation_score"),
            metadata=data.get("metadata"),
        )

    async def verify_age(
        self,
        birth_date_hash: int,
        public_key: int,
        current_date_hash: int,
        minimum_age: int = 18,
    ) -> AgeVerification:
        """Submit a ZKP age proof for verification."""
        resp = await self._client.post(
            "/api/v1/quantum/zkp/age/verify",
            json={
                "birth_date_hash": birth_date_hash,
                "public_key": public_key,
                "current_date_hash": current_date_hash,
                "minimum_age": minimum_age,
            },
            headers=self._auth_headers(),
        )
        if resp.status_code != 200:
            raise TrustSafetyError(resp.status_code, resp.text)
        data = resp.json()
        return AgeVerification(
            valid=data["valid"],
            proof_type=data.get("proof_type", "age_over"),
            minimum_age=minimum_age,
            verified_at=data.get("verified_at"),
        )

    async def get_audit_log(
        self,
        limit: int = 100,
        offset: int = 0,
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> list[AuditEntry]:
        """Retrieve audit log entries."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if actor_id:
            params["actor_id"] = actor_id
        if resource_type:
            params["resource_type"] = resource_type
        if resource_id:
            params["resource_id"] = resource_id

        resp = await self._client.get(
            "/api/v1/audit/events",
            params=params,
            headers=self._auth_headers(),
        )
        if resp.status_code != 200:
            raise TrustSafetyError(resp.status_code, resp.text)
        data = resp.json()
        return [
            AuditEntry(
                id=entry["id"],
                actor_id=entry.get("actor_id"),
                actor_type=entry["actor_type"],
                action=entry["action"],
                resource_type=entry.get("resource_type"),
                resource_id=entry.get("resource_id"),
                timestamp=entry["timestamp"],
                integrity_hash=entry.get("integrity_hash"),
            )
            for entry in data
        ]

    async def verify_zkp(
        self,
        proof_type: str,
        proof_data: dict[str, Any],
        public_key: int,
    ) -> ZKPProof:
        """Verify a zero-knowledge proof."""
        endpoint_map = {
            "age": "/api/v1/quantum/zkp/age/verify",
            "consent": "/api/v1/quantum/zkp/consent/verify",
            "identity": "/api/v1/quantum/zkp/identity/verify",
        }
        endpoint = endpoint_map.get(proof_type)
        if not endpoint:
            raise ValueError(f"Unknown proof type: {proof_type}")

        resp = await self._client.post(
            endpoint,
            json={**proof_data, "public_key": public_key},
            headers=self._auth_headers(),
        )
        if resp.status_code != 200:
            raise TrustSafetyError(resp.status_code, resp.text)
        data = resp.json()
        return ZKPProof(
            valid=data["valid"],
            proof_type=proof_type,
            metadata=data.get("metadata"),
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> TrustSafetyClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
