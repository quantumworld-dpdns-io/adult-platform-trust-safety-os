# Operations Overview

## Infrastructure Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Container Orchestration | EKS (Kubernetes) | Application deployment |
| Primary Database | PostgreSQL 16 (RDS) | Users, content, audit logs |
| Cache / Sessions | Redis 7 (ElastiCache) | Sessions, rate limiting, queues |
| Object Storage | S3 | Media files, backups, exports |
| CDN | CloudFront | Static assets, API acceleration |
| WAF | AWS WAF | Request filtering, rate limiting |
| Monitoring | Prometheus + Grafana | Metrics, dashboards, alerts |
| Logging | OpenTelemetry + CloudWatch | Distributed tracing, logs |

## Documentation Map
| Topic | File |
|-------|------|
| Deployment guide | [deployment.md](deployment.md) |
| Monitoring guide | [monitoring.md](monitoring.md) |
| Operational runbook | [runbook.md](runbook.md) |

## Key Procedures
- **Deploy**: `make deploy` or `terraform apply` in `deploy/terraform/`
- **Scale**: Kubernetes HPA configured for CPU/memory thresholds
- **Backup**: Automated daily RDS snapshots, 30-day retention
- **Rotate**: Keys rotated every 90 days via KMS
- **Monitor**: Grafana dashboards at `grafana.internal:3000`
