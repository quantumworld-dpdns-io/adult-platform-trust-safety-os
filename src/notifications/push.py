"""Push notifications: send, bulk send, device registration and unregistration."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_push_log: list[dict[str, Any]] = []
_device_registry: dict[str, dict[str, Any]] = {}


class PushNotifier:
    def __init__(self) -> None:
        self._log = _push_log
        self._devices = _device_registry

    async def send_push(
        self,
        user_id: str,
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        priority: str = "normal",
        badge: int | None = None,
        sound: str = "default",
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        user_devices = [
            d for d in self._devices.values()
            if d["user_id"] == user_id and d["is_active"]
        ]

        if not user_devices:
            return {
                "message_id": message_id,
                "status": "no_devices",
                "sent_count": 0,
            }

        sent_count = 0
        for device in user_devices:
            record = {
                "message_id": str(uuid.uuid4()),
                "parent_message_id": message_id,
                "device_id": device["device_id"],
                "user_id": user_id,
                "platform": device["platform"],
                "title": title,
                "body": body,
                "data": data or {},
                "priority": priority,
                "status": "sent",
                "sent_at": now,
            }
            self._log.append(record)
            sent_count += 1

        logger.info("push_sent", user_id=user_id, devices=sent_count, title=title)

        return {
            "message_id": message_id,
            "status": "sent",
            "sent_count": sent_count,
            "total_devices": len(user_devices),
        }

    async def send_bulk(
        self,
        user_ids: list[str],
        title: str,
        body: str,
        data: dict[str, Any] | None = None,
        priority: str = "normal",
    ) -> dict[str, Any]:
        results = []
        total_sent = 0

        for user_id in user_ids:
            result = await self.send_push(
                user_id=user_id,
                title=title,
                body=body,
                data=data,
                priority=priority,
            )
            results.append({"user_id": user_id, **result})
            total_sent += result.get("sent_count", 0)

        return {
            "total_sent": total_sent,
            "total_users": len(user_ids),
            "results": results,
        }

    async def register_device(
        self,
        user_id: str,
        device_token: str,
        platform: str = "ios",
        app_version: str | None = None,
    ) -> dict[str, Any]:
        device_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        existing = None
        for d in self._devices.values():
            if d["device_token"] == device_token:
                existing = d
                break

        if existing:
            existing["user_id"] = user_id
            existing["platform"] = platform
            existing["app_version"] = app_version
            existing["is_active"] = True
            existing["updated_at"] = now

            return {
                "device_id": existing["device_id"],
                "status": "updated",
                "platform": platform,
            }

        record = {
            "device_id": device_id,
            "user_id": user_id,
            "device_token": device_token,
            "platform": platform,
            "app_version": app_version,
            "is_active": True,
            "registered_at": now,
            "updated_at": now,
        }
        self._devices[device_id] = record

        logger.info("device_registered", user_id=user_id, platform=platform, device_id=device_id)

        return {
            "device_id": device_id,
            "status": "registered",
            "platform": platform,
        }

    async def unregister_device(
        self,
        device_id: str,
    ) -> dict[str, Any]:
        if device_id not in self._devices:
            return {"error": "Device not found", "device_id": device_id}

        device = self._devices[device_id]
        device["is_active"] = False
        device["updated_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "device_id": device_id,
            "status": "unregistered",
        }

    def get_user_devices(self, user_id: str) -> list[dict[str, Any]]:
        return [
            {k: v for k, v in d.items() if k != "device_token"}
            for d in self._devices.values()
            if d["user_id"] == user_id
        ]

    def get_stats(self) -> dict[str, Any]:
        active_devices = sum(1 for d in self._devices.values() if d["is_active"])
        return {
            "total_devices": len(self._devices),
            "active_devices": active_devices,
            "total_sent": len(self._log),
        }
