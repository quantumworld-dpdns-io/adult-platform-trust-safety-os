"""Real-time content scanner for live streams and WebSocket feeds."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import structlog

from src.moderation.classifier import ContentClassifier, ContentClassification
from src.moderation.policy import PolicyEngine

logger = structlog.get_logger(__name__)

DecisionCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class RealtimeScanner:
    """Scan content in real-time as it arrives via WebSocket or streaming APIs.

    Coordinates the classifier, policy engine, and a pluggable callback to
    broadcast decisions to connected clients.
    """

    def __init__(
        self,
        *,
        classifier: ContentClassifier | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        self._classifier = classifier or ContentClassifier()
        self._policy = policy_engine or PolicyEngine()
        self._callbacks: list[DecisionCallback] = []
        self._scan_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._running = False

    def register_callback(self, callback: DecisionCallback) -> None:
        """Register a callback invoked when a scan decision is made."""
        self._callbacks.append(callback)

    async def scan_content_stream(
        self,
        content_stream: Any,
    ) -> list[dict[str, Any]]:
        """Consume an async iterable of content chunks and scan each."""
        results: list[dict[str, Any]] = []

        async for chunk in content_stream:
            decision = await self._scan_single(chunk)
            results.append(decision)
            await self.broadcast_decision(decision)

        return results

    async def process_websocket_message(
        self,
        message: str | bytes,
        *,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a single WebSocket message containing content to scan."""
        if isinstance(message, bytes):
            message = message.decode("utf-8")

        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            return {
                "scan_id": str(uuid.uuid4()),
                "status": "error",
                "error": "invalid_json",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        content_type = payload.get("content_type", "TEXT")
        raw_content = payload.get("content", "")
        metadata = payload.get("metadata", {})

        scan_input = {
            "content_type": content_type,
            "content": raw_content,
            "metadata": metadata,
            "client_id": client_id,
            "message_id": payload.get("message_id"),
        }

        decision = await self._scan_single(scan_input)
        await self.broadcast_decision(decision)
        return decision

    async def broadcast_decision(self, decision: dict[str, Any]) -> None:
        """Send a scan decision to all registered callbacks."""
        for callback in self._callbacks:
            try:
                await callback(decision.get("scan_id", ""), decision)
            except Exception:  # noqa: BLE001
                logger.exception("broadcast_callback_error", scan_id=decision.get("scan_id"))

    async def start_processing(self) -> None:
        """Start the background processing loop."""
        self._running = True
        while self._running:
            try:
                item = await asyncio.wait_for(self._scan_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            decision = await self._scan_single(item)
            await self.broadcast_decision(decision)

    def stop_processing(self) -> None:
        """Signal the background loop to stop."""
        self._running = False

    async def _scan_single(self, item: dict[str, Any]) -> dict[str, Any]:
        """Classify a single content item and apply policy rules."""
        scan_id = str(uuid.uuid4())
        content_type = item.get("content_type", "TEXT")
        raw_content = item.get("content", "")
        metadata = item.get("metadata", {})
        client_id = item.get("client_id")
        message_id = item.get("message_id")

        classification = self._classify_content(content_type, raw_content, item)
        policy_result = self._policy.evaluate_content(classification)

        decision = {
            "scan_id": scan_id,
            "content_type": content_type,
            "action": policy_result["action"],
            "classification": {
                "labels": classification.labels,
                "scores": classification.scores,
                "confidence": classification.confidence,
            },
            "violations": policy_result["violations"],
            "thresholds_met": policy_result["thresholds_met"],
            "client_id": client_id,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            "content_scanned",
            scan_id=scan_id,
            content_type=content_type,
            action=decision["action"],
            labels=classification.labels,
        )
        return decision

    def _classify_content(
        self,
        content_type: str,
        raw_content: str,
        item: dict[str, Any],
    ) -> ContentClassification:
        """Route content to the appropriate classifier method."""
        match content_type.upper():
            case "TEXT":
                return self._classifier.classify_text(raw_content)
            case "IMAGE":
                image_bytes = raw_content.encode() if isinstance(raw_content, str) else raw_content
                return self._classifier.classify_image(
                    image_bytes, filename=item.get("metadata", {}).get("filename", "")
                )
            case "VIDEO":
                video_bytes = raw_content.encode() if isinstance(raw_content, str) else raw_content
                return self._classifier.classify_video(
                    video_bytes, filename=item.get("metadata", {}).get("filename", "")
                )
            case "AUDIO":
                audio_bytes = raw_content.encode() if isinstance(raw_content, str) else raw_content
                return self._classifier.classify_audio(
                    audio_bytes, filename=item.get("metadata", {}).get("filename", "")
                )
            case "LIVE_STREAM":
                return self._classifier.classify_text(raw_content)
            case _:
                return self._classifier.classify_text(raw_content)
