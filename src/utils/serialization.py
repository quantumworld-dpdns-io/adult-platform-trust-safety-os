"""Serialization helpers: JSON, MessagePack, and protobuf adapters."""

from __future__ import annotations

import json
from typing import Any

try:
    import msgpack  # type: ignore[import-untyped]
except ImportError:
    msgpack = None  # type: ignore[assignment]

# Protobuf is optional – users wire their own .proto definitions.
try:
    from google.protobuf import json_format  # type: ignore[import-untyped]
    from google.protobuf.message import Message as ProtoMessage  # type: ignore[import-untyped]
except ImportError:
    json_format = None  # type: ignore[assignment]
    ProtoMessage = None  # type: ignore[assignment,misc]


class Serializer:
    """Unified serialization interface for JSON, MessagePack, and Protobuf."""

    # ── JSON ───────────────────────────────────────────────────

    @staticmethod
    def to_json(obj: Any, indent: int | None = None) -> str:
        """Serialize *obj* to a JSON string."""
        return json.dumps(obj, indent=indent, ensure_ascii=False, default=str)

    @staticmethod
    def from_json(raw: str | bytes) -> Any:
        """Deserialize a JSON string (or bytes) back to a Python object."""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    # ── MessagePack ────────────────────────────────────────────

    @staticmethod
    def to_msgpack(obj: Any) -> bytes:
        """Serialize *obj* to MessagePack bytes.

        Raises:
            RuntimeError: If ``msgpack`` is not installed.
        """
        if msgpack is None:
            raise RuntimeError("msgpack package is not installed")
        return msgpack.packb(obj, use_bin_type=True)

    @staticmethod
    def from_msgpack(raw: bytes) -> Any:
        """Deserialize MessagePack bytes back to a Python object.

        Raises:
            RuntimeError: If ``msgpack`` is not installed.
        """
        if msgpack is None:
            raise RuntimeError("msgpack package is not installed")
        return msgpack.unpackb(raw, raw=False)

    # ── Protobuf ───────────────────────────────────────────────

    @staticmethod
    def to_protobuf(message: ProtoMessage) -> bytes:
        """Serialize a protobuf ``Message`` to its binary wire format.

        Raises:
            TypeError: If *message* is not a protobuf Message.
            RuntimeError: If protobuf dependencies are missing.
        """
        if ProtoMessage is None or json_format is None:
            raise RuntimeError("protobuf package is not installed")
        if not isinstance(message, ProtoMessage):
            raise TypeError(f"Expected a protobuf Message, got {type(message).__name__}")
        return message.SerializeToString()

    @staticmethod
    def from_protobuf(data: bytes, message_cls: type) -> Any:
        """Deserialize binary data into a protobuf ``Message`` of *message_cls*.

        Args:
            data: Serialized protobuf bytes.
            message_cls: A protobuf Message class to populate.

        Returns:
            Populated protobuf Message instance.

        Raises:
            TypeError: If *message_cls* is not a valid protobuf Message class.
            RuntimeError: If protobuf dependencies are missing.
        """
        if ProtoMessage is None or json_format is None:
            raise RuntimeError("protobuf package is not installed")
        if not (isinstance(message_cls, type) and issubclass(message_cls, ProtoMessage)):
            raise TypeError(f"message_cls must be a protobuf Message subclass, got {message_cls}")
        msg = message_cls()
        msg.ParseFromString(data)
        return msg
