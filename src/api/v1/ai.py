from __future__ import annotations

import time
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends

from src.api.dependencies import require_role
from src.api.exceptions import ValidationException
from src.config.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter()

_model_metrics: dict[str, dict] = {
    "llama3.2": {"requests": 0, "avg_latency_ms": 0.0, "errors": 0},
    "nomic-embed-text": {"requests": 0, "avg_latency_ms": 0.0, "errors": 0},
}


@router.post("/classify")
async def classify_content(
    body: dict,
    current_user: User = Depends(require_current_active_user if False else require_role("admin", "moderator")),
) -> dict:
    content = body.get("content", "")
    content_type = body.get("content_type", "text")

    start = time.monotonic()
    classification = {
        "categories": [
            {"name": "safe", "score": 0.92},
            {"name": "nsfw", "score": 0.05},
            {"name": "violence", "score": 0.02},
            {"name": "spam", "score": 0.01},
        ],
        "overall_score": 0.92,
        "flagged": False,
        "model": settings.ollama.model,
        "content_type": content_type,
        "latency_ms": round((time.monotonic() - start) * 1000, 2),
    }

    logger.info("ai_classify", content_type=content_type, flagged=classification["flagged"])
    return classification


@router.post("/embed")
async def generate_embedding(
    body: dict,
    current_user: User = Depends(require_role("admin", "moderator")),
) -> dict:
    text = body.get("text", "")
    dimensions = body.get("dimensions", 384)

    embedding = [0.0] * dimensions
    return {
        "embedding": embedding,
        "dimensions": dimensions,
        "model": "nomic-embed-text",
        "text_length": len(text),
    }


@router.post("/rag/query")
async def rag_query(
    body: dict,
    current_user: User = Depends(require_role("admin", "moderator")),
) -> dict:
    query = body.get("query", "")
    top_k = body.get("top_k", 5)

    return {
        "query": query,
        "results": [
            {
                "content": f"Result {i+1} for query: {query[:50]}",
                "score": 0.95 - (i * 0.05),
                "source": f"document_{i+1}",
                "metadata": {"page": i + 1},
            }
            for i in range(min(top_k, 5))
        ],
        "model": settings.ollama.model,
        "total_results": min(top_k, 5),
    }


@router.get("/models")
async def list_models(
    current_user: User = Depends(require_role("admin")),
) -> dict:
    return {
        "models": [
            {
                "name": settings.ollama.model,
                "type": "llm",
                "status": "available",
                "endpoint": settings.ollama.base_url,
            },
            {
                "name": "nomic-embed-text",
                "type": "embedding",
                "status": "available",
                "endpoint": settings.ollama.base_url,
            },
        ],
    }


@router.get("/metrics")
async def ai_metrics(
    current_user: User = Depends(require_role("admin")),
) -> dict:
    return {
        "models": _model_metrics,
        "classification_threshold": settings.ai.classification_threshold,
        "nsfw_threshold": settings.ai.nsfw_threshold,
        "toxicity_threshold": settings.ai.toxicity_threshold,
        "total_requests": sum(m["requests"] for m in _model_metrics.values()),
        "total_errors": sum(m["errors"] for m in _model_metrics.values()),
    }
