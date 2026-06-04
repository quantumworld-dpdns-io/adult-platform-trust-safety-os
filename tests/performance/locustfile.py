"""Locust load tests for the trust and safety API."""

from __future__ import annotations

import random
import uuid

from locust import HttpUser, between, task


class TrustSafetyUser(HttpUser):
    wait_time = between(0.5, 2.0)
    host = "http://localhost:8000"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.content_ids = []

    def on_start(self):
        email = f"loadtest_{uuid.uuid4().hex[:8]}@example.com"
        username = f"loadtest_{uuid.uuid4().hex[:8]}"
        resp = self.client.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "password": "secureP@ss123",
        })
        if resp.status_code == 201:
            body = resp.json()
            self.access_token = body["access_token"]
            self.refresh_token = body["refresh_token"]
            headers = {"Authorization": f"Bearer {self.access_token}"}
            me = self.client.get("/api/v1/users/me", headers=headers)
            if me.status_code == 200:
                self.user_id = me.json()["id"]

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    @task(5)
    def login(self):
        email = f"loadtest_{uuid.uuid4().hex[:8]}@example.com"
        self.client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "wrongpassword",
        }, name="/api/v1/auth/login [fail]")

    @task(3)
    def submit_content(self):
        if not self.access_token:
            return
        resp = self.client.post(
            "/api/v1/content",
            json={
                "content_type": "TEXT",
                "raw_content": f"Load test content {uuid.uuid4().hex[:8]}",
            },
            headers=self._auth_headers(),
            name="/api/v1/content [create]",
        )
        if resp.status_code == 201:
            self.content_ids.append(resp.json()["id"])

    @task(4)
    def get_content(self):
        if not self.content_ids:
            return
        content_id = random.choice(self.content_ids)
        self.client.get(
            f"/api/v1/content/{content_id}",
            headers=self._auth_headers(),
            name="/api/v1/content [get]",
        )

    @task(2)
    def scan_content(self):
        if not self.content_ids:
            return
        content_id = random.choice(self.content_ids)
        self.client.post(
            f"/api/v1/content/{content_id}/scan",
            headers=self._auth_headers(),
            name="/api/v1/content [scan]",
        )

    @task(2)
    def get_audit_log(self):
        if not self.access_token:
            return
        self.client.get(
            "/api/v1/audit/events",
            headers=self._auth_headers(),
            name="/api/v1/audit/events",
        )

    @task(3)
    def verify_age(self):
        if not self.access_token or not self.user_id:
            return
        self.client.post(
            f"/api/v1/users/{self.user_id}/verify-age",
            json={
                "method": "document",
                "document_type": "passport",
                "document_data": "load-test-doc",
                "issued_country": "US",
            },
            headers=self._auth_headers(),
            name="/api/v1/users [verify-age]",
        )

    @task(1)
    def get_health(self):
        self.client.get("/health/live", name="/health/live")

    @task(1)
    def list_content(self):
        if not self.access_token:
            return
        self.client.get(
            "/api/v1/content",
            headers=self._auth_headers(),
            name="/api/v1/content [list]",
        )
