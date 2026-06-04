"""OAuth2/OIDC integration for Google and Apple providers."""

from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlencode

import httpx

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_USERINFO_URL = "https://appleid.apple.com/auth/userinfo"


class OAuth2Provider(ABC):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str] | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["openid", "email", "profile"]
        self._state: str | None = None

    @abstractmethod
    def authorize(self, state: str | None = None) -> str:
        ...

    @abstractmethod
    async def callback(self, code: str, state: str | None = None) -> dict[str, Any]:
        ...

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...


class GoogleOAuth2Provider(OAuth2Provider):
    @property
    def name(self) -> str:
        return "google"

    def authorize(self, state: str | None = None) -> str:
        self._state = state or secrets.token_urlsafe(32)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": self._state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def callback(self, code: str, state: str | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            data = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            raw = resp.json()
            return {
                "provider": "google",
                "provider_user_id": raw.get("sub", ""),
                "email": raw.get("email", ""),
                "email_verified": raw.get("email_verified", False),
                "name": raw.get("name", ""),
                "picture": raw.get("picture", ""),
                "locale": raw.get("locale", ""),
            }


class AppleOAuth2Provider(OAuth2Provider):
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        key_id: str,
        team_id: str,
        scopes: list[str] | None = None,
    ) -> None:
        super().__init__(client_id, client_secret, redirect_uri, scopes or ["name", "email"])
        self.key_id = key_id
        self.team_id = team_id

    @property
    def name(self) -> str:
        return "apple"

    def _generate_client_secret(self) -> str:
        import time
        import jwt as pyjwt
        now = int(time.time())
        payload = {
            "iss": self.team_id,
            "iat": now,
            "exp": now + 180 * 86400,
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
        }
        return pyjwt.encode(payload, self.client_secret, algorithm="ES256", headers={"kid": self.key_id})

    def authorize(self, state: str | None = None) -> str:
        self._state = state or secrets.token_urlsafe(32)
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code id_token",
            "scope": " ".join(self.scopes),
            "response_mode": "form_post",
            "state": self._state,
        }
        return f"{APPLE_AUTH_URL}?{urlencode(params)}"

    async def callback(self, code: str, state: str | None = None) -> dict[str, Any]:
        client_secret = self._generate_client_secret()
        async with httpx.AsyncClient(timeout=30) as client:
            data = {
                "code": code,
                "client_id": self.client_id,
                "client_secret": client_secret,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
            }
            resp = await client.post(APPLE_TOKEN_URL, data=data)
            resp.raise_for_status()
            return resp.json()

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                APPLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            raw = resp.json()
            return {
                "provider": "apple",
                "provider_user_id": raw.get("sub", ""),
                "email": raw.get("email", ""),
                "email_verified": raw.get("email_verified", False),
                "name": "",
                "picture": "",
            }


def create_provider(
    provider_name: str,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    **kwargs: Any,
) -> OAuth2Provider:
    if provider_name == "google":
        return GoogleOAuth2Provider(client_id, client_secret, redirect_uri)
    elif provider_name == "apple":
        return AppleOAuth2Provider(
            client_id,
            client_secret,
            redirect_uri,
            key_id=kwargs["key_id"],
            team_id=kwargs["team_id"],
        )
    raise ValueError(f"Unsupported OAuth2 provider: {provider_name}")
