# Deployment Guide

## Prerequisites
- AWS CLI configured with appropriate IAM role
- Terraform >= 1.5
- Docker >= 24.0
- kubectl configured for target EKS cluster
- Helm >= 3.12

## Local Development

```bash
# Start all services
docker compose up -d

# Run migrations
docker compose exec app alembic upgrade head

# Verify health
curl http://localhost:8000/health
```

## Docker Build

```bash
# Build production image
docker build -t trust-safety:latest .

# Multi-stage build targets
docker build --target builder -t trust-safety:builder .
docker build --target production -t trust-safety:production .
```

## Kubernetes Deployment

### Namespace
```bash
kubectl create namespace trust-safety
```

### Secrets
```bash
kubectl create secret generic trust-safety-secrets \
  --from-literal=DB_PASSWORD="${DB_PASSWORD}" \
  --from-literal=JWT_PRIVATE_KEY="${JWT_PRIVATE_KEY}" \
  --from-literal=JWT_PUBLIC_KEY="${JWT_PUBLIC_KEY}" \
  --from-literal=REDIS_URL="${REDIS_URL}" \
  -n trust-safety
```

### Deploy with Helm
```bash
cd deploy/helm
helm install trust-safety . \
  --namespace trust-safety \
  --values values-production.yaml \
  --set image.tag=$(git rev-parse --short HEAD)
```

### Verify Deployment
```bash
kubectl get pods -n trust-safety
kubectl logs -f deployment/trust-safety -n trust-safety
```

## Terraform Deployment (AWS)

```bash
cd deploy/terraform

# Initialize
terraform init

# Plan
terraform plan -var-file="production.tfvars"

# Apply
terraform apply -var-file="production.tfvars"
```

### What Terraform Provisions
- EKS cluster with managed node groups
- RDS PostgreSQL 16 (Multi-AZ)
- ElastiCache Redis 7 (cluster mode)
- S3 buckets for media and backups
- CloudFront distribution
- WAFv2 web ACL
- IAM roles and policies
- VPC with public/private subnets

## Cloud Provider Notes

### AWS (Primary)
- Region: `us-east-1` (configurable)
- EKS: Kubernetes 1.29
- RDS: db.r6g.large, Multi-AZ, encrypted
- ElastiCache: cache.r6g.large, encryption at rest

### Supported Providers (Terraform Modules)
- AWS (EKS, RDS, ElastiCache, S3, CloudFront, WAF)
- Scaleway, Exoscale, Arvancloud, Zeabur, VNG Cloud, Selectel, Northflank

## Environment Variables

| Variable | Description | Required |
|----------|------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_PRIVATE_KEY_PATH` | Path to Ed25519 private key | Yes |
| `JWT_PUBLIC_KEY_PATH` | Path to Ed25519 public key | Yes |
| `MINIO_ENDPOINT` | Object storage endpoint | Yes |
| `OLLAMA_BASE_URL` | Ollama LLM endpoint | Optional |
| `QDRANT_URL` | Qdrant vector store URL | Optional |
| `LOG_LEVEL` | Logging level (INFO/DEBUG) | Optional |
| `AUDIT_BATCH_SIZE` | Audit log batch size | Optional |

## Rollback
```bash
# Kubernetes
helm rollback trust-safety 0 -n trust-safety

# Terraform
terraform apply -target=module.eks -var-file="production.tfvars"
```
