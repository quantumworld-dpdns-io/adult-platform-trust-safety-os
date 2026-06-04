# Monitoring Guide

## Stack
- **Metrics**: Prometheus + prometheus-client
- **Dashboards**: Grafana
- **Traces**: OpenTelemetry SDK + OTLP exporter
- **Logs**: structlog + CloudWatch
- **Alerts**: Prometheus Alertmanager

## Prometheus Metrics

### Application Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
REQUEST_COUNT = Counter("http_requests_total", "Total requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["method", "endpoint"])

# Moderation metrics
MODERATION_DECISIONS = Counter("moderation_decisions_total", "Decisions", ["action", "content_type"])
MODERATION_LATENCY = Histogram("moderation_latency_seconds", "Moderation processing time")

# Audit metrics
AUDIT_EVENTS = Counter("audit_events_total", "Audit events logged", ["action", "actor_type"])
AUDIT_BATCH_SIZE = Histogram("audit_batch_size", "Batch size on flush")

# Quantum metrics
PQC_OPERATIONS = Counter("pqc_operations_total", "PQC operations", ["algorithm", "operation"])
ZKP_PROOFS = Counter("zkp_proofs_total", "ZKP proofs", ["proof_type", "result"])
```

### Infrastructure Metrics
```python
ACTIVE_SESSIONS = Gauge("active_sessions", "Active user sessions")
DB_POOL_SIZE = Gauge("db_pool_size", "Database connection pool size")
DB_POOL_CHECKED_OUT = Gauge("db_pool_checked_out", "Connections in use")
REDIS_MEMORY_USED = Gauge("redis_memory_used_bytes", "Redis memory usage")
```

## Grafana Dashboards

### Dashboard: Trust & Safety Overview
- Request rate and latency (p50, p95, p99)
- Moderation decision distribution
- Error rate by endpoint
- Active sessions gauge

### Dashboard: Security
- Failed authentication attempts
- Rate limiting triggers
- PQC operation counts
- ZKP proof verification rates

### Dashboard: Infrastructure
- Database connection pool utilization
- Redis memory and hit rate
- Kubernetes pod CPU/memory
- S3 storage growth

## SLOs (Service Level Objectives)

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Availability | 99.9% | Uptime excluding planned maintenance |
| API Latency (p95) | < 200ms | HTTP response time |
| Moderation Latency | < 5s | Content classification time |
| Audit Log Integrity | 100% | Merkle chain verification |
| ZKP Verification | < 50ms | Proof verification time |

## Alerting Rules

### Critical (Page immediately)
- API error rate > 5% for 5 minutes
- Database connection pool exhaustion
- Audit log write failures
- PQC signature verification failures

### Warning (Notify team)
- API latency p95 > 500ms for 10 minutes
- Redis memory usage > 80%
- Failed authentication rate spike
- Certificate expiry < 30 days

### Info (Dashboard only)
- Deployment completed
- Key rotation completed
- Migration task completed

## Log Structure
```python
import structlog

logger = structlog.get_logger(__name__)

# Structured log with correlation
logger.info(
    "content_moderated",
    content_id=str(content_id),
    decision="approved",
    score=0.12,
    latency_ms=340,
    correlation_id=correlation_id,
)
```

## Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("moderation.classify") as span:
    span.set_attribute("content.type", content_type.value)
    result = await classifier.classify(content)
    span.set_attribute("moderation.score", result.score)
```
