from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import select, update, and_

from .consent import Consent, ConsentType

logger = logging.getLogger(__name__)


class ConsentService:
    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def grant_consent(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Consent:
        async with self._session_factory() as session:
            existing = await self._get_active_consent(session, user_id, consent_type)
            if existing is not None:
                existing.granted = True
                existing.withdrawn_at = None
                existing.ip_address = ip_address or existing.ip_address
                existing.user_agent = user_agent or existing.user_agent
                existing.version += 1
                await session.commit()
                await session.refresh(existing)
                logger.info(
                    "Consent updated for user %s type=%s v%d",
                    user_id, consent_type.value, existing.version,
                )
                return existing

            consent = Consent(
                user_id=user_id,
                consent_type=consent_type.value,
                granted=True,
                ip_address=ip_address,
                user_agent=user_agent,
                version=1,
            )
            session.add(consent)
            await session.commit()
            await session.refresh(consent)
            logger.info("Consent granted for user %s type=%s", user_id, consent_type.value)
            return consent

    async def withdraw_consent(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Consent | None:
        async with self._session_factory() as session:
            consent = await self._get_active_consent(session, user_id, consent_type)
            if consent is None:
                logger.warning(
                    "No active consent to withdraw for user %s type=%s",
                    user_id, consent_type.value,
                )
                return None

            consent.granted = False
            consent.withdrawn_at = datetime.now(timezone.utc)
            consent.ip_address = ip_address or consent.ip_address
            consent.user_agent = user_agent or consent.user_agent
            consent.version += 1
            await session.commit()
            await session.refresh(consent)

            await self._write_audit(session, consent, action="withdraw")
            logger.info("Consent withdrawn for user %s type=%s", user_id, consent_type.value)
            return consent

    async def get_consent_status(
        self, user_id: uuid.UUID, consent_type: ConsentType
    ) -> dict[str, Any]:
        async with self._session_factory() as session:
            consent = await self._get_active_consent(session, user_id, consent_type)
            if consent is None:
                return {
                    "user_id": str(user_id),
                    "consent_type": consent_type.value,
                    "granted": False,
                    "active": False,
                    "version": 0,
                }
            return {
                "user_id": str(user_id),
                "consent_type": consent_type.value,
                "granted": consent.granted,
                "active": consent.is_active,
                "version": consent.version,
                "granted_at": consent.granted_at.isoformat() if consent.granted_at else None,
                "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
            }

    async def get_all_consents(self, user_id: uuid.UUID) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for ct in ConsentType:
            results[ct.value] = await self.get_consent_status(user_id, ct)
        return results

    async def get_consent_history(
        self, user_id: uuid.UUID, consent_type: ConsentType
    ) -> Sequence[Consent]:
        async with self._session_factory() as session:
            stmt = (
                select(Consent)
                .where(
                    and_(
                        Consent.user_id == user_id,
                        Consent.consent_type == consent_type.value,
                    )
                )
                .order_by(Consent.version.desc())
            )
            result = await session.execute(stmt)
            return result.scalars().all()

    async def bulk_grant(
        self,
        user_id: uuid.UUID,
        consent_types: Sequence[ConsentType],
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> list[Consent]:
        consents: list[Consent] = []
        for ct in consent_types:
            consent = await self.grant_consent(
                user_id, ct, ip_address=ip_address, user_agent=user_agent
            )
            consents.append(consent)
        return consents

    async def bulk_withdraw(
        self,
        user_id: uuid.UUID,
        consent_types: Sequence[ConsentType],
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> list[Consent]:
        consents: list[Consent] = []
        for ct in consent_types:
            consent = await self.withdraw_consent(
                user_id, ct, ip_address=ip_address, user_agent=user_agent
            )
            if consent is not None:
                consents.append(consent)
        return consents

    async def _get_active_consent(
        self, session: Any, user_id: uuid.UUID, consent_type: ConsentType
    ) -> Consent | None:
        stmt = (
            select(Consent)
            .where(
                and_(
                    Consent.user_id == user_id,
                    Consent.consent_type == consent_type.value,
                )
            )
            .order_by(Consent.version.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def _write_audit(
        self, session: Any, consent: Consent, action: str
    ) -> None:
        logger.info(
            "AUDIT: action=%s user=%s consent=%s version=%d granted=%s withdrawn=%s",
            action,
            consent.user_id,
            consent.consent_type,
            consent.version,
            consent.granted,
            consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
        )
