"""WebSocket manager: connection handling, broadcasting, rooms, and user targeting."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class WebSocketConnection:
    def __init__(self, connection_id: str, user_id: str | None = None) -> None:
        self.connection_id = connection_id
        self.user_id = user_id
        self.rooms: set[str] = set()
        self.connected_at = datetime.now(timezone.utc).isoformat()
        self._ws: Any = None
        self._metadata: dict[str, Any] = {}

    async def send(self, message: dict[str, Any]) -> bool:
        if self._ws is None:
            return False
        try:
            await self._ws.send_json(message)
            return True
        except Exception:
            return False


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocketConnection] = {}
        self._user_connections: dict[str, set[str]] = {}
        self._rooms: dict[str, set[str]] = {}

    async def connect(
        self,
        ws: Any,
        user_id: str | None = None,
        rooms: list[str] | None = None,
    ) -> WebSocketConnection:
        connection_id = str(uuid.uuid4())
        conn = WebSocketConnection(connection_id, user_id)
        conn._ws = ws
        conn._metadata = {"connected_at": conn.connected_at}

        self._connections[connection_id] = conn

        if user_id:
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(connection_id)

        for room in rooms or []:
            await self.join_room(connection_id, room)

        logger.info(
            "websocket_connected",
            connection_id=connection_id,
            user_id=user_id,
            rooms=rooms or [],
        )

        return conn

    async def disconnect(self, connection_id: str) -> None:
        conn = self._connections.pop(connection_id, None)
        if conn is None:
            return

        for room in list(conn.rooms):
            await self.leave_room(connection_id, room)

        if conn.user_id and conn.user_id in self._user_connections:
            self._user_connections[conn.user_id].discard(connection_id)
            if not self._user_connections[conn.user_id]:
                del self._user_connections[conn.user_id]

        logger.info("websocket_disconnected", connection_id=connection_id, user_id=conn.user_id)

    async def broadcast(
        self,
        message: dict[str, Any],
        room: str | None = None,
    ) -> dict[str, Any]:
        sent = 0
        failed = 0

        if room:
            conn_ids = self._rooms.get(room, set())
            targets = [self._connections[cid] for cid in conn_ids if cid in self._connections]
        else:
            targets = list(self._connections.values())

        for conn in targets:
            success = await conn.send(message)
            if success:
                sent += 1
            else:
                failed += 1

        return {
            "sent": sent,
            "failed": failed,
            "total_targets": len(targets),
            "room": room,
        }

    async def send_to_user(
        self,
        user_id: str,
        message: dict[str, Any],
    ) -> dict[str, Any]:
        conn_ids = self._user_connections.get(user_id, set())
        sent = 0
        failed = 0

        for conn_id in conn_ids:
            conn = self._connections.get(conn_id)
            if conn:
                success = await conn.send(message)
                if success:
                    sent += 1
                else:
                    failed += 1

        return {
            "user_id": user_id,
            "sent": sent,
            "failed": failed,
            "total_connections": len(conn_ids),
        }

    async def send_to_room(
        self,
        room: str,
        message: dict[str, Any],
        exclude: str | None = None,
    ) -> dict[str, Any]:
        conn_ids = self._rooms.get(room, set())
        sent = 0
        failed = 0

        for conn_id in conn_ids:
            if conn_id == exclude:
                continue
            conn = self._connections.get(conn_id)
            if conn:
                success = await conn.send(message)
                if success:
                    sent += 1
                else:
                    failed += 1

        return {
            "room": room,
            "sent": sent,
            "failed": failed,
        }

    async def join_room(self, connection_id: str, room: str) -> None:
        conn = self._connections.get(connection_id)
        if conn is None:
            return

        conn.rooms.add(room)
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(connection_id)

    async def leave_room(self, connection_id: str, room: str) -> None:
        conn = self._connections.get(connection_id)
        if conn:
            conn.rooms.discard(room)

        if room in self._rooms:
            self._rooms[room].discard(connection_id)
            if not self._rooms[room]:
                del self._rooms[room]

    def get_connections(
        self,
        user_id: str | None = None,
        room: str | None = None,
    ) -> list[dict[str, Any]]:
        if user_id:
            conn_ids = self._user_connections.get(user_id, set())
            connections = [self._connections[cid] for cid in conn_ids if cid in self._connections]
        elif room:
            conn_ids = self._rooms.get(room, set())
            connections = [self._connections[cid] for cid in conn_ids if cid in self._connections]
        else:
            connections = list(self._connections.values())

        return [
            {
                "connection_id": c.connection_id,
                "user_id": c.user_id,
                "rooms": list(c.rooms),
                "connected_at": c.connected_at,
            }
            for c in connections
        ]

    def get_room_members(self, room: str) -> list[str]:
        return [
            self._connections[cid].user_id
            for cid in self._rooms.get(room, set())
            if cid in self._connections and self._connections[cid].user_id
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_connections": len(self._connections),
            "total_users": len(self._user_connections),
            "total_rooms": len(self._rooms),
            "rooms": {room: len(members) for room, members in self._rooms.items()},
        }
