# 5-Minute Quickstart

## Prerequisites
- Python 3.12+
- Docker + Docker Compose

## Steps

### 1. Clone and Install
```bash
git clone https://github.com/quantumworld-dpdns-io/adult-platform-trust-safety-os.git
cd adult-platform-trust-safety-os
pip install -e ".[dev,quantum]"
```

### 2. Start Infrastructure
```bash
docker compose up -d postgres redis
```

### 3. Run Migrations
```bash
alembic upgrade head
```

### 4. Start the Server
```bash
uvicorn src.api.main:app --reload --port 8000
```

### 5. Verify
```bash
curl http://localhost:8000/health
```

### 6. Try the API
```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123!"}'
```

### 7. Test Quantum Modules
```python
# QRNG
from src.quantum.circuits.qrng import generate_random_bytes
print(generate_random_bytes(16).hex())

# ZKP Age Proof
from src.quantum.zkp.age_proof import generate_keypair, prove_age_over, verify_age_proof
pk, pub = generate_keypair()
proof = prove_age_over(b"hash_birth", pk, pub, b"hash_now", 18)
print(f"Proof valid: {verify_age_proof(proof, pub)}")

# PQC Key Exchange
from src.quantum.pqc.key_encapsulation import generate_keypair, encapsulate
kp = generate_keypair()
enc = encapsulate(kp.public_key)
print(f"Shared secret: {enc.shared_secret.hex()[:32]}...")
```

## What's Next?
- [Architecture Overview](../architecture/README.md)
- [API Documentation](../api/README.md)
- [Security Model](../architecture/security-model.md)
- [Development Guide](../development/README.md)
