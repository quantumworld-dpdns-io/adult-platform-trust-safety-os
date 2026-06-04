"""MCP tools for content scanning, classification, and moderation status."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from src.moderation.classifier import ContentClassifier, ContentClassification
from src.moderation.content import ContentStatus


_classifier = ContentClassifier()

_content_store: dict[str, dict[str, Any]] = {}


async def scan_content(
    content_text: str | None = None,
    content_type: str = "TEXT",
    content_url: str | None = None,
    submitter_id: str = "anonymous",
) -> dict[str, Any]:
    content_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    classification = ContentClassification()
    if content_text:
        classification = _classifier.classify_text(content_text)

    needs_review = classification.confidence > 0.5 or classification.nsfw_score > 0.3
    auto_action: str | None = None
    if classification.confidence > 0.9:
        auto_action = "auto_reject"
    elif classification.confidence < 0.1:
        auto_action = "auto_approve"

    record = {
        "content_id": content_id,
        "content_type": content_type,
        "content_text": content_text,
        "content_url": content_url,
        "submitter_id": submitter_id,
        "classification": {
            "labels": classification.labels,
            "scores": classification.scores,
            "confidence": classification.confidence,
            "nsfw_score": classification.nsfw_score,
            "toxicity_score": classification.toxicity_score,
            "violence_score": classification.violence_score,
            "spam_score": classification.spam_score,
        },
        "needs_review": needs_review,
        "auto_action": auto_action,
        "status": "PENDING",
        "scanned_at": now,
    }
    _content_store[content_id] = record

    return {
        "content_id": content_id,
        "classification": record["classification"],
        "needs_review": needs_review,
        "auto_action": auto_action,
        "status": "PENDING",
    }


async def classify_content(
    content_id: str | None = None,
    content_text: str | None = None,
) -> dict[str, Any]:
    if content_id and content_id in _content_store:
        record = _content_store[content_id]
        return {
            "content_id": content_id,
            "classification": record["classification"],
            "status": record["status"],
        }

    if content_text:
        classification = _classifier.classify_text(content_text)
        return {
            "content_id": content_id or str(uuid.uuid4()),
            "classification": {
                "labels": classification.labels,
                "scores": classification.scores,
                "confidence": classification.confidence,
                "nsfw_score": classification.nsfw_score,
                "toxicity_score": classification.toxicity_score,
                "violence_score": classification.violence_score,
                "spam_score": classification.spam_score,
            },
        }

    return {"error": "Either content_id or content_text must be provided"}


async def get_moderation_status(content_id: str) -> dict[str, Any]:
    if content_id not in _content_store:
        return {"error": "Content not found", "content_id": content_id}

    record = _content_store[content_id]
    return {
        "content_id": content_id,
        "status": record["status"],
        "classification": record["classification"],
        "needs_review": record["needs_review"],
        "auto_action": record["auto_action"],
        "scanned_at": record["scanned_at"],
        "submitter_id": record["submitter_id"],
    }
