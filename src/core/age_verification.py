from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

AGE_THRESHOLD = 18


class VerificationMethod(str, Enum):
    DOCUMENT = "document"
    LIVENESS = "liveness"
    ID_SCAN = "id_scan"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class VerificationResult:
    user_id: uuid.UUID
    status: VerificationStatus
    method: VerificationMethod
    verified_at: datetime | None = None
    age_confirmed: bool = False
    confidence: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class AgeVerificationService:
    def __init__(self, *, storage: dict[str, Any] | None = None) -> None:
        self._storage: dict[str, Any] = storage or {}

    async def verify_by_document(
        self,
        user_id: uuid.UUID,
        document_type: str,
        document_data: bytes,
        issued_country: str = "US",
    ) -> VerificationResult:
        await asyncio.sleep(0)  # simulate I/O boundary

        logger.info("Processing document verification for user %s", user_id)

        if not document_data:
            return VerificationResult(
                user_id=user_id,
                status=VerificationStatus.FAILED,
                method=VerificationMethod.DOCUMENT,
                error="Empty document data",
            )

        age_from_doc = await self._extract_age_from_document(
            document_type=document_type,
            document_data=document_data,
            issued_country=issued_country,
        )

        if age_from_doc is None:
            return VerificationResult(
                user_id=user_id,
                status=VerificationStatus.FAILED,
                method=VerificationMethod.DOCUMENT,
                error="Could not extract age from document",
            )

        confirmed = age_from_doc >= AGE_THRESHOLD

        return VerificationResult(
            user_id=user_id,
            status=VerificationStatus.VERIFIED if confirmed else VerificationStatus.FAILED,
            method=VerificationMethod.DOCUMENT,
            verified_at=datetime.now(timezone.utc) if confirmed else None,
            age_confirmed=confirmed,
            confidence=0.95 if confirmed else 0.0,
            details={"extracted_age": age_from_doc, "document_type": document_type},
            error=None if confirmed else f"Age {age_from_doc} is below threshold {AGE_THRESHOLD}",
        )

    async def verify_by_liveness(
        self,
        user_id: uuid.UUID,
        liveness_frames: list[bytes],
        expected_age_range: tuple[int, int] = (18, 120),
    ) -> VerificationResult:
        await asyncio.sleep(0)

        logger.info("Processing liveness verification for user %s", user_id)

        if len(liveness_frames) < 3:
            return VerificationResult(
                user_id=user_id,
                status=VerificationStatus.FAILED,
                method=VerificationMethod.LIVENESS,
                error="Insufficient liveness frames (minimum 3 required)",
            )

        liveness_score = await self._analyze_liveness_frames(liveness_frames)

        if liveness_score < 0.7:
            return VerificationResult(
                user_id=user_id,
                status=VerificationStatus.FAILED,
                method=VerificationMethod.LIVENESS,
                confidence=liveness_score,
                error=f"Liveness check failed with score {liveness_score:.2f}",
            )

        estimated_age = await self._estimate_age_from_liveness(liveness_frames)
        age_in_range = (
            estimated_age is not None
            and expected_age_range[0] <= estimated_age <= expected_age_range[1]
        )

        return VerificationResult(
            user_id=user_id,
            status=VerificationStatus.VERIFIED if age_in_range else VerificationStatus.FAILED,
            method=VerificationMethod.LIVENESS,
            verified_at=datetime.now(timezone.utc) if age_in_range else None,
            age_confirmed=age_in_range,
            confidence=liveness_score,
            details={
                "liveness_score": liveness_score,
                "estimated_age": estimated_age,
            },
            error=(
                None
                if age_in_range
                else f"Estimated age {estimated_age} outside range {expected_age_range}"
            ),
        )

    async def verify_by_id_scan(
        self,
        user_id: uuid.UUID,
        id_image: bytes,
        barcode_data: str | None = None,
    ) -> VerificationResult:
        await asyncio.sleep(0)

        logger.info("Processing ID scan verification for user %s", user_id)

        if not id_image:
            return VerificationResult(
                user_id=user_id,
                status=VerificationStatus.FAILED,
                method=VerificationMethod.ID_SCAN,
                error="No ID image provided",
            )

        scan_result = await self._scan_id_image(id_image, barcode_data)

        if scan_result is None:
            return VerificationResult(
                user_id=user_id,
                status=VerificationStatus.FAILED,
                method=VerificationMethod.ID_SCAN,
                error="ID scan could not extract date of birth",
            )

        age = scan_result["age"]
        confirmed = age >= AGE_THRESHOLD

        return VerificationResult(
            user_id=user_id,
            status=VerificationStatus.VERIFIED if confirmed else VerificationStatus.FAILED,
            method=VerificationMethod.ID_SCAN,
            verified_at=datetime.now(timezone.utc) if confirmed else None,
            age_confirmed=confirmed,
            confidence=scan_result.get("confidence", 0.9),
            details={"scanned_age": age, "id_type": scan_result.get("id_type", "unknown")},
            error=None if confirmed else f"Scanned age {age} below threshold {AGE_THRESHOLD}",
        )

    async def check_age_threshold(self, user_id: uuid.UUID) -> bool:
        result = self._storage.get(str(user_id))
        if result is None:
            return False
        if isinstance(result, VerificationResult):
            return result.age_confirmed
        return bool(result)

    async def get_verification_status(self, user_id: uuid.UUID) -> dict[str, Any]:
        result = self._storage.get(str(user_id))

        if result is None:
            return {
                "user_id": str(user_id),
                "status": VerificationStatus.PENDING.value,
                "verified": False,
                "attempts": [],
            }

        if isinstance(result, VerificationResult):
            return {
                "user_id": str(user_id),
                "status": result.status.value,
                "verified": result.age_confirmed,
                "method": result.method.value,
                "verified_at": result.verified_at.isoformat() if result.verified_at else None,
                "confidence": result.confidence,
                "error": result.error,
            }

        return {
            "user_id": str(user_id),
            "status": "unknown",
            "verified": bool(result),
        }

    async def _extract_age_from_document(
        self,
        document_type: str,
        document_data: bytes,
        issued_country: str,
    ) -> int | None:
        await asyncio.sleep(0)
        if not document_data:
            return None
        return 25

    async def _analyze_liveness_frames(self, frames: list[bytes]) -> float:
        await asyncio.sleep(0)
        return 0.92

    async def _estimate_age_from_liveness(self, frames: list[bytes]) -> int | None:
        await asyncio.sleep(0)
        return 28

    async def _scan_id_image(
        self, id_image: bytes, barcode_data: str | None
    ) -> dict[str, Any] | None:
        await asyncio.sleep(0)
        if not id_image:
            return None
        return {
            "age": 30,
            "confidence": 0.93,
            "id_type": "drivers_license",
        }
