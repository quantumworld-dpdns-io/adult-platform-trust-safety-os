# Operational Runbook

## Common Procedures

### Application Restart
```bash
# Kubernetes
kubectl rollout restart deployment/trust-safety -n trust-safety

# Docker Compose
docker compose restart app
```

### Database Migration
```bash
# Run pending migrations
docker compose exec app alembic upgrade head

# Rollback last migration
docker compose exec app alembic downgrade -1
```

### Key Rotation
```bash
# Generate new PQC keypair
python -c "
from src.quantum.pqc.key_encapsulation import generate_keypair
kp = generate_keypair()
print(f'Public key: {kp.public_key.hex()[:32]}...')
"

# Update Kubernetes secrets
kubectl create secret generic trust-safety-keys \
  --from-file=new-key.pem \
  --dry-run=client -o yaml | kubectl apply -f -
```

### Cache Clear
```bash
# Clear rate limiting cache
docker compose exec redis redis-cli FLUSHDB

# Clear specific session prefix
docker compose exec redis redis-cli DEL "session:*"
```

### Audit Log Export
```bash
# Export audit logs for compliance
python -c "
from src.audit.export import export_audit_range
import asyncio
asyncio.run(export_audit_range('2024-01-01', '2024-12-31', format='csv'))
"
```

## Incident Response

### P1: Service Down
1. Check pod status: `kubectl get pods -n trust-safety`
2. Check logs: `kubectl logs deployment/trust-safety -n trust-safety --tail=100`
3. Verify dependencies (DB, Redis): `curl http://localhost:8000/health`
4. If DB down: check RDS console, failover if Multi-AZ
5. Rollback: `helm rollback trust-safety 0 -n trust-safety`

### P2: Elevated Error Rate
1. Check Grafana dashboard for error patterns
2. Identify affected endpoints
3. Check for recent deployments: `helm history trust-safety -n trust-safety`
4. If deployment-related: rollback
5. If traffic-related: adjust rate limits or scale

### P3: Performance Degradation
1. Check database connection pool: `kubectl exec -it redis-cli info clients`
2. Check slow queries in PostgreSQL logs
3. Verify Redis hit rate
4. Scale horizontally if needed: `kubectl scale deployment/trust-safety --replicas=5`

### P4: Security Incident
1. Freeze deployments
2. Review audit logs: `src/audit/logger.py` queries
3. Check for unauthorized access patterns
4. Rotate affected credentials
5. Notify security team
6. Document in incident tracker

## Maintenance Procedures

### Monthly
- Review Grafana dashboards for trends
- Run `pip-audit` for dependency vulnerabilities
- Verify backup integrity
- Review and prune old container images

### Quarterly
- Rotate JWT signing keys
- Rotate PQC keys
- Review RBAC permissions
- Update TLS certificates
- Run `bandit` security scan

### Annually
- Full PQC migration review
- Penetration testing
- Disaster recovery drill
- Architecture review
