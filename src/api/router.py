from __future__ import annotations

from fastapi import APIRouter

from src.api.v1 import admin, ai, audit, auth, consent, content, moderation, quantum, reports, users

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(consent.router, prefix="/consent", tags=["consent"])
router.include_router(content.router, prefix="/content", tags=["content"])
router.include_router(moderation.router, prefix="/moderation", tags=["moderation"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(reports.router, prefix="/reports", tags=["reports"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(quantum.router, prefix="/quantum", tags=["quantum"])
router.include_router(ai.router, prefix="/ai", tags=["ai"])
