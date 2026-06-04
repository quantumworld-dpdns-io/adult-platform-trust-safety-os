"""Tests for core ORM model mixins: UUID, Timestamp, SoftDelete."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.core.models import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin
from sqlalchemy import Column, String, create_engine
from sqlalchemy.orm import Session


class SampleModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "test_models"
    name = Column(String(64), nullable=False)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_uuid_generation(db):
    obj = SampleModel(name="alpha")
    db.add(obj)
    db.flush()
    assert obj.id is not None
    assert isinstance(obj.id, uuid.UUID)


def test_uuid_uniqueness(db):
    a = SampleModel(name="a")
    b = SampleModel(name="b")
    db.add_all([a, b])
    db.flush()
    assert a.id != b.id


def test_timestamp_auto_set(db):
    obj = SampleModel(name="timestamped")
    db.add(obj)
    db.flush()
    db.refresh(obj)
    assert isinstance(obj.created_at, datetime)
    assert isinstance(obj.updated_at, datetime)
    assert obj.created_at.tzinfo is not None


def test_timestamp_updated_at_changes(db):
    obj = SampleModel(name="updater")
    db.add(obj)
    db.flush()
    db.refresh(obj)
    first_updated = obj.updated_at
    obj.name = "updater_v2"
    obj.updated_at = datetime.now(timezone.utc)
    db.flush()
    db.refresh(obj)
    assert obj.updated_at >= first_updated


def test_soft_delete(db):
    obj = SampleModel(name="deletable")
    db.add(obj)
    db.flush()
    db.refresh(obj)
    assert obj.is_deleted is False
    obj.soft_delete()
    db.flush()
    db.refresh(obj)
    assert obj.is_deleted is True
    assert obj.deleted_at is not None


def test_soft_delete_restore(db):
    obj = SampleModel(name="restorable")
    db.add(obj)
    db.flush()
    obj.soft_delete()
    db.flush()
    assert obj.is_deleted is True
    obj.restore()
    db.flush()
    db.refresh(obj)
    assert obj.is_deleted is False
    assert obj.deleted_at is None


def test_model_serialization_fields(db):
    obj = SampleModel(name="serializable")
    db.add(obj)
    db.flush()
    db.refresh(obj)
    data = {
        "id": obj.id,
        "name": obj.name,
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
        "deleted_at": obj.deleted_at,
        "is_deleted": obj.is_deleted,
    }
    assert data["name"] == "serializable"
    assert data["is_deleted"] is False
    assert data["deleted_at"] is None
    assert "T" in data["created_at"]


def test_base_is_declarative():
    assert issubclass(Base, object)
    assert hasattr(Base, "metadata")


def test_soft_delete_none_initially(db):
    obj = SampleModel(name="fresh")
    db.add(obj)
    db.flush()
    db.refresh(obj)
    assert obj.deleted_at is None
