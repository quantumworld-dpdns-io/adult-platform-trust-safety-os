# Zero-Knowledge Proof Implementation Guide

## Overview

Zero-knowledge proofs allow one party (prover) to convince another party (verifier) that a statement is true without revealing any information beyond the validity of the statement itself.

## Age Verification

**Module**: `src/quantum/zkp/age_proof.py`

### Protocol
Schnorr-like proof of knowledge over discrete logarithm. The prover demonstrates knowledge of a private key corresponding to a public key, bound to a specific birth date hash and minimum age.

### Generating a Keypair
```python
from src.quantum.zkp.age_proof import generate_keypair

private_key, public_key = generate_keypair()
```

### Proving Age >= Minimum
```python
from src.quantum.zkp.age_proof import prove_age_over

proof = prove_age_over(
    birth_date_hash=hash_int(birth_date),
    private_key=private_key,
    public_key=public_key,
    current_date_hash=hash_int(current_date),
    minimum_age=18,
)
```

### Proving Age <= Maximum
```python
from src.quantum.zkp.age_proof import prove_age_under

proof = prove_age_under(
    birth_date_hash=hash_int(birth_date),
    private_key=private_key,
    public_key=public_key,
    current_date_hash=hash_int(current_date),
    maximum_age=65,
)
```

### Proving Age Range
```python
from src.quantum.zkp.age_proof import prove_age_range

proof = prove_age_range(
    birth_date_hash=hash_int(birth_date),
    private_key=private_key,
    public_key=public_key,
    current_date_hash=hash_int(current_date),
    min_age=18,
    max_age=65,
)
```

### Verification (Server-Side)
```python
from src.quantum.zkp.age_proof import verify_age_proof

# Server only needs the public key - no PII
is_valid = verify_age_proof(proof, public_key)
```

### Security Properties
- **Zero-knowledge**: Verifier learns nothing about the actual birth date
- **Soundness**: Cannot forge proof without the private key
- **Completeness**: Honest prover always convinces honest verifier
- **Non-transferable**: Proof is bound to the specific challenge (replay-resistant)

## Consent Verification

**Module**: `src/quantum/zkp/consent_proof.py`

### Proving Consent Was Given
```python
from src.quantum.zkp.consent_proof import prove_consent_given

proof = prove_consent_given(
    consent_id="consent-123",
    consent_type="data_processing",
    private_key=private_key,
    public_key=public_key,
    timestamp=int(time.time()),
)
```

### Proving Consent Was Withdrawn
```python
from src.quantum.zkp.consent_proof import prove_consent_withdrawn

proof = prove_consent_withdrawn(
    consent_id="consent-123",
    consent_type="data_processing",
    private_key=private_key,
    public_key=public_key,
    timestamp=int(time.time()),
)
```

### Verification
```python
from src.quantum.zkp.consent_proof import verify_consent_proof

is_valid = verify_consent_proof(proof, public_key)
```

## Identity Verification

**Module**: `src/quantum/zkp/identity_proof.py`

### Creating an Identity Commitment
```python
from src.quantum.zkp.identity_proof import create_identity_commitment

commitment = create_identity_commitment(
    private_key=private_key,
    public_key=public_key,
    pii_data={"name": "Jane Doe", "ssn": "123-45-6789"},
    salt=secrets.token_bytes(32),
)
# Store commitment.commitment_hash - never store raw PII
```

### Proving Identity Without Revealing PII
```python
from src.quantum.zkp.identity_proof import prove_identity_without_pii

proof = prove_identity_without_pii(
    private_key=private_key,
    public_key=public_key,
    identity_commitment=commitment,
)
```

### Verification
```python
from src.quantum.zkp.identity_proof import verify_identity_proof

is_valid = verify_identity_proof(proof, commitment)
```

### Group Membership Proof
```python
from src.quantum.zkp.identity_proof import prove_membership_in_group

proof = prove_membership_in_group(
    private_key=private_key,
    public_key=public_key,
    group_members=[pub1, pub2, pub3],  # list of member public keys
    group_id="verified_creators",
)
```

## Mathematical Foundation

All ZKP implementations use a Schnorr-like protocol over a multiplicative group mod prime P:

- **Group**: (Z/pZ)* where p = 2^256 - 2^32 - 977
- **Generator**: g = 2
- **Order**: q = 2^256 - 189
- **Hash**: SHA-256 for challenge computation

### Protocol Steps
1. **Commit**: Prover picks random nonce r, computes t = g^r mod p
2. **Challenge**: Verifier (or hash function) produces c = H(t, pk, context)
3. **Response**: Prover computes s = r - c * sk mod q
4. **Verify**: Check g^s * pk^c == t (mod p)

## API Integration

### REST Endpoints
```
POST /api/v1/quantum/zkp/age/prove     - Generate age proof
POST /api/v1/quantum/zkp/age/verify     - Verify age proof
POST /api/v1/quantum/zkp/consent/prove  - Generate consent proof
POST /api/v1/quantum/zkp/consent/verify - Verify consent proof
POST /api/v1/quantum/zkp/identity/prove - Generate identity proof
POST /api/v1/quantum/zkp/identity/verify - Verify identity proof
```

### Python SDK
```python
from trust_safety_sdk import TrustSafetyClient

client = TrustSafetyClient(base_url="https://api.example.com", api_key="...")

# Verify age via ZKP
result = client.verify_zkp(
    proof_type="age",
    proof_data={...},
    public_key=pub_key,
)
```
