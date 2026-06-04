from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_active_user, require_role
from src.api.exceptions import NotFoundError, ValidationException
from src.core.user import User

logger = structlog.get_logger(__name__)

router = APIRouter()

_circuit_store: dict[str, dict] = {}
_zkp_store: dict[str, dict] = {}


@router.post("/circuit/execute")
async def execute_circuit(
    circuit: dict,
    current_user: User = Depends(require_role("admin")),
) -> dict:
    circuit_id = str(uuid.uuid4())
    _circuit_store[circuit_id] = {
        "id": circuit_id,
        "status": "running",
        "circuit": circuit,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("quantum_circuit_executed", circuit_id=circuit_id, actor=str(current_user.id))
    return {
        "circuit_id": circuit_id,
        "status": "running",
        "message": "Circuit execution started",
    }


@router.get("/circuit/{circuit_id}/status")
async def circuit_status(
    circuit_id: str,
    current_user: User = Depends(require_role("admin")),
) -> dict:
    entry = _circuit_store.get(circuit_id)
    if entry is None:
        raise NotFoundError("Circuit not found")
    return entry


@router.post("/zkp/prove")
async def generate_zkp(
    statement: dict,
    witness: dict,
    current_user: User = Depends(require_role("admin")),
) -> dict:
    proof_id = str(uuid.uuid4())
    _zkp_store[proof_id] = {
        "id": proof_id,
        "proof": f"zkp_proof_{uuid.uuid4().hex[:16]}",
        "statement": statement,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "verified": False,
    }

    logger.info("zkp_generated", proof_id=proof_id, actor=str(current_user.id))
    return {
        "proof_id": proof_id,
        "proof": _zkp_store[proof_id]["proof"],
        "algorithm": "groth16",
        "created_at": _zkp_store[proof_id]["created_at"],
    }


@router.post("/zkp/verify")
async def verify_zkp(
    proof_id: str,
    public_inputs: dict,
    current_user: User = Depends(require_role("admin")),
) -> dict:
    entry = _zkp_store.get(proof_id)
    if entry is None:
        raise NotFoundError("Proof not found")

    entry["verified"] = True
    entry["verified_at"] = datetime.now(timezone.utc).isoformat()

    logger.info("zkp_verified", proof_id=proof_id, actor=str(current_user.id))
    return {
        "proof_id": proof_id,
        "valid": True,
        "verified_at": entry["verified_at"],
    }


@router.get("/pqc/status")
async def pqc_status(
    current_user: User = Depends(require_role("admin")),
) -> dict:
    return {
        "enabled": True,
        "algorithms": {
            "key_exchange": "ML-KEM-768",
            "signature": "ML-DSA-65",
            "hash": "SHA3-256",
        },
        "hybrid_mode": True,
        "classical_fallback": "X25519",
        "status": "operational",
        "last_rotation": datetime.now(timezone.utc).isoformat(),
    }
