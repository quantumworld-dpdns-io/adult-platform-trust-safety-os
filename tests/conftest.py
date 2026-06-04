"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import uuid
from unittest.mock import Mock

import fakeredis.aioredis
import pytest


@pytest.fixture
def app():
    from src.api.app import create_app
    return create_app()


@pytest.fixture
async def async_client(app):
    import httpx
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
async def db_session():
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def redis_client():
    server = fakeredis.aioredis.FakeServer()
    client = fakeredis.aioredis.FakeRedis(server=server)
    yield client


@pytest.fixture
def mock_ollama():
    client = Mock()
    client.chat.return_value = {
        "message": {"content": "safe"},
        "done": True,
    }
    return client


@pytest.fixture
def test_user():
    from tests.factories import UserFactory
    return UserFactory()


@pytest.fixture
def test_content():
    from tests.factories import ContentFactory
    return ContentFactory()


@pytest.fixture
def test_audit_event():
    from tests.factories import AuditEventFactory
    return AuditEventFactory()


@pytest.fixture
def sample_jwt_token():
    from tests.helpers import generate_test_jwt
    return generate_test_jwt(subject="test-user-id", roles=["user"])


@pytest.fixture
def sample_api_key():
    return "tsk_test_api_key_" + uuid.uuid4().hex
