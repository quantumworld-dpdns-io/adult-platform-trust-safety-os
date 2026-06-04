"""Trust & Safety SDK for the Adult Platform API."""

__version__ = "1.0.0-alpha.1"

from .client import TrustSafetyClient
from .models import (
    AuditEntry,
    ContentClassification,
    ZKPProof,
    AgeVerification,
)

__all__ = [
    "TrustSafetyClient",
    "ContentClassification",
    "AgeVerification",
    "AuditEntry",
    "ZKPProof",
]
