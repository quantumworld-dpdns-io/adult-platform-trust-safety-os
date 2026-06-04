from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

from src.config.settings import settings

router = APIRouter(tags=["metrics"])

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ACTIVE_USERS = Gauge(
    "active_users_total",
    "Number of currently active users",
)

MODERATION_QUEUE_DEPTH = Gauge(
    "moderation_queue_depth",
    "Current depth of the moderation queue",
    ["status"],
)

CONTENT_SCANNED = Counter(
    "content_scanned_total",
    "Total number of content items scanned",
    ["content_type", "result"],
)

MFA_ENABLED_USERS = Gauge(
    "mfa_enabled_users",
    "Number of users with MFA enabled",
)

AUDIT_EVENTS_TOTAL = Counter(
    "audit_events_total",
    "Total audit events logged",
    ["action", "actor_type"],
)


def _get_registry() -> CollectorRegistry:
    if settings.app_env == "production" and "prometheus_multiproc_dir" in __import__("os").environ:
        return CollectorRegistry()
    return CollectorRegistry()


@router.get("/metrics")
async def metrics() -> Response:
    registry = _get_registry()
    if "prometheus_multiproc_dir" in __import__("os").environ:
        multiprocess.mark_process_dead(0)
    body = generate_latest(registry)
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
