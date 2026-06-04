# API Overview

## Base URL
```
https://api.trust-safety.example.com/api/v1
```

## Authentication

### JWT Bearer Token
All authenticated endpoints require a JWT in the `Authorization` header:
```
Authorization: Bearer <access_token>
```

### Obtaining a Token
```bash
# Register
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

# Login
POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

# Response
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Token Refresh
```bash
POST /api/v1/auth/refresh
{
  "refresh_token": "eyJ..."
}
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user |
| POST | `/auth/login` | Login and get tokens |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Invalidate session |
| POST | `/auth/mfa/enable` | Enable MFA |
| POST | `/auth/mfa/verify` | Verify MFA code |

### Content
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/content` | Submit content for moderation |
| GET | `/content/{id}` | Get content status |
| GET | `/content` | List content (paginated) |
| DELETE | `/content/{id}` | Delete content |

### Moderation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/moderation/{id}/approve` | Approve content (moderator) |
| POST | `/moderation/{id}/reject` | Reject content (moderator) |
| POST | `/moderation/{id}/escalate` | Escalate to human review |
| GET | `/moderation/queue` | Get review queue |

### Audit
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/audit/events` | List audit events |
| GET | `/audit/events/{id}` | Get specific event |
| GET | `/audit/events/actor/{id}` | Events by actor |
| GET | `/audit/events/resource/{type}/{id}` | Events by resource |
| GET | `/audit/verify` | Verify Merkle chain integrity |

### Quantum / ZKP
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/quantum/zkp/age/prove` | Generate age proof |
| POST | `/quantum/zkp/age/verify` | Verify age proof |
| POST | `/quantum/zkp/consent/prove` | Generate consent proof |
| POST | `/quantum/zkp/consent/verify` | Verify consent proof |
| POST | `/quantum/zkp/identity/prove` | Generate identity proof |
| POST | `/quantum/zkp/identity/verify` | Verify identity proof |
| POST | `/quantum/pqc/keygen` | Generate PQC keypair |
| POST | `/quantum/pqc/encapsulate` | Kyber key encapsulation |
| POST | `/quantum/pqc/sign` | Dilithium digital signature |
| POST | `/quantum/pqc/verify` | Verify PQC signature |
| POST | `/quantum/qrng/random` | Generate quantum random bytes |

### Reports
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reports` | Submit a report |
| GET | `/reports` | List reports |
| GET | `/reports/{id}` | Get report details |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List all users |
| PUT | `/admin/users/{id}/role` | Change user role |
| GET | `/admin/stats` | Platform statistics |
| POST | `/admin/keys/rotate` | Rotate cryptographic keys |

## Rate Limiting
- Default: 100 requests/minute per API key
- Auth endpoints: 10 requests/minute per IP
- Premium tier: 1000 requests/minute

## Error Responses
```json
{
  "detail": {
    "error": "authentication_required",
    "message": "Valid JWT token required"
  }
}
```

## SDKs
- [Python SDK](../../sdk/python/) - `pip install trust-safety-sdk`
- [JavaScript SDK](../../sdk/javascript/)
