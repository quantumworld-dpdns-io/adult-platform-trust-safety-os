"""Post-quantum cryptography migration toolkit."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MigrationStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CryptoAsset:
    name: str
    algorithm: str
    key_size: int
    usage: str
    location: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    pqc_replacement: str = ""
    migration_status: MigrationStatus = MigrationStatus.NOT_STARTED


@dataclass
class MigrationTask:
    task_id: str
    description: str
    priority: int
    estimated_hours: float
    dependencies: List[str] = field(default_factory=list)
    status: MigrationStatus = MigrationStatus.NOT_STARTED


@dataclass
class MigrationPlan:
    assets: List[CryptoAsset]
    tasks: List[MigrationTask]
    timeline_months: int
    total_estimated_hours: float
    risk_assessment: str
    recommendations: List[str]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


ALGORITHM_REPLACEMENTS: Dict[str, Dict[str, Any]] = {
    "RSA": {
        "pqc_replacement": "CRYSTALS-Kyber (KEM) / CRYSTALS-Dilithium (Sig)",
        "risk_level": RiskLevel.CRITICAL,
        "notes": "RSA is fully vulnerable to Shor's algorithm",
    },
    "ECDSA": {
        "pqc_replacement": "CRYSTALS-Dilithium",
        "risk_level": RiskLevel.HIGH,
        "notes": "ECDSA broken by Shor's algorithm",
    },
    "ECDH": {
        "pqc_replacement": "CRYSTALS-Kyber",
        "risk_level": RiskLevel.HIGH,
        "notes": "ECDH broken by Shor's algorithm",
    },
    "Ed25519": {
        "pqc_replacement": "CRYSTALS-Dilithium",
        "risk_level": RiskLevel.HIGH,
        "notes": "Ed25519 vulnerable to quantum attacks",
    },
    "AES-128": {
        "pqc_replacement": "AES-256",
        "risk_level": RiskLevel.MEDIUM,
        "notes": "Grover's algorithm halves effective key length",
    },
    "AES-256": {
        "pqc_replacement": "AES-256 (quantum-resistant)",
        "risk_level": RiskLevel.LOW,
        "notes": "AES-256 provides adequate quantum security",
    },
    "SHA-256": {
        "pqc_replacement": "SHA-384 / SHA-512",
        "risk_level": RiskLevel.LOW,
        "notes": "Grover's reduces security to 128-bit, still adequate",
    },
    "ChaCha20-Poly1305": {
        "pqc_replacement": "ChaCha20-Poly1305 (quantum-resistant)",
        "risk_level": RiskLevel.LOW,
        "notes": "Symmetric, consider increasing key size",
    },
}


def analyze_current_crypto(
    assets: List[CryptoAsset],
) -> Dict[str, Any]:
    risk_counts = {level: 0 for level in RiskLevel}
    total_assets = len(assets)
    assets_with_replacement = 0

    for asset in assets:
        algo_upper = asset.algorithm.upper()
        replacement_info = None
        for known_algo, info in ALGORITHM_REPLACEMENTS.items():
            if known_algo.upper() in algo_upper:
                replacement_info = info
                asset.risk_level = info["risk_level"]
                asset.pqc_replacement = info["pqc_replacement"]
                break

        if replacement_info is None:
            asset.risk_level = RiskLevel.MEDIUM
            asset.pqc_replacement = "Manual review required"

        risk_counts[asset.risk_level] += 1
        if asset.pqc_replacement:
            assets_with_replacement += 1

    critical_assets = [a for a in assets if a.risk_level == RiskLevel.CRITICAL]

    return {
        "total_assets": total_assets,
        "risk_distribution": {level.value: count for level, count in risk_counts.items()},
        "critical_assets": [a.name for a in critical_assets],
        "assets_with_known_replacement": assets_with_replacement,
        "migration_readiness": assets_with_replacement / total_assets if total_assets > 0 else 0.0,
    }


def generate_migration_plan(
    assets: List[CryptoAsset],
    team_size: int = 4,
    budget_constraint_months: int = 24,
) -> MigrationPlan:
    analysis = analyze_current_crypto(assets)

    tasks: List[MigrationTask] = []
    task_id = 1

    tasks.append(MigrationTask(
        task_id=f"T{task_id:03d}",
        description="Complete cryptographic inventory and risk assessment",
        priority=1,
        estimated_hours=40.0,
    ))
    task_id += 1

    critical_assets = [a for a in assets if a.risk_level == RiskLevel.CRITICAL]
    if critical_assets:
        tasks.append(MigrationTask(
            task_id=f"T{task_id:03d}",
            description=f"Migrate {len(critical_assets)} critical assets to PQC",
            priority=1,
            estimated_hours=len(critical_assets) * 80.0,
            dependencies=[f"T001"],
        ))
        task_id += 1

    high_assets = [a for a in assets if a.risk_level == RiskLevel.HIGH]
    if high_assets:
        tasks.append(MigrationTask(
            task_id=f"T{task_id:03d}",
            description=f"Migrate {len(high_assets)} high-risk assets to PQC",
            priority=2,
            estimated_hours=len(high_assets) * 60.0,
            dependencies=[f"T001"],
        ))
        task_id += 1

    tasks.append(MigrationTask(
        task_id=f"T{task_id:03d}",
        description="Deploy hybrid classical+PQC cryptographic infrastructure",
        priority=2,
        estimated_hours=200.0,
        dependencies=[f"T002"],
    ))
    task_id += 1

    tasks.append(MigrationTask(
        task_id=f"T{task_id:03d}",
        description="Update key management systems for PQC key sizes",
        priority=3,
        estimated_hours=120.0,
        dependencies=[f"T002"],
    ))
    task_id += 1

    tasks.append(MigrationTask(
        task_id=f"T{task_id:03d}",
        description="Implement PQC TLS endpoints",
        priority=3,
        estimated_hours=160.0,
        dependencies=[f"T004"],
    ))
    task_id += 1

    tasks.append(MigrationTask(
        task_id=f"T{task_id:03d}",
        description="Conduct PQC penetration testing and validation",
        priority=4,
        estimated_hours=120.0,
        dependencies=[f"T005", f"T006"],
    ))
    task_id += 1

    tasks.append(MigrationTask(
        task_id=f"T{task_id:03d}",
        description="Staff training and documentation",
        priority=5,
        estimated_hours=60.0,
    ))
    task_id += 1

    total_hours = sum(t.estimated_hours for t in tasks)
    estimated_months = max(6, int(total_hours / (team_size * 160)) + 1)
    estimated_months = min(estimated_months, budget_constraint_months)

    recommendations = [
        "Start with hybrid mode (classical + PQC) to maintain compatibility",
        "Prioritize CRYSTALS-Kyber for key encapsulation and CRYSTALS-Dilithium for signatures",
        "Implement crypto-agility to allow algorithm substitution without system redesign",
        "Maintain classical algorithms alongside PQC during transition period",
        "Establish quantum-safe key management practices with larger key sizes",
        "Schedule regular PQC standard compliance reviews (NIST FIPS 203, 204, 205)",
        "Consider NIST-approved algorithms only: ML-KEM, ML-DSA, SLH-DSA",
    ]

    return MigrationPlan(
        assets=assets,
        tasks=tasks,
        timeline_months=estimated_months,
        total_estimated_hours=total_hours,
        risk_assessment=json.dumps(analysis, indent=2),
        recommendations=recommendations,
    )


def get_pqc_recommendations(algorithm: str) -> List[str]:
    algo_upper = algorithm.upper()
    recommendations: List[str] = []

    for known_algo, info in ALGORITHM_REPLACEMENTS.items():
        if known_algo.upper() in algo_upper:
            recommendations.append(f"Replace {algorithm} with {info['pqc_replacement']}")
            recommendations.append(f"Risk level: {info['risk_level'].value}")
            recommendations.append(f"Notes: {info['notes']}")
            break

    if not recommendations:
        recommendations.append(f"No specific recommendation for {algorithm}")
        recommendations.append("Conduct manual cryptographic review")
        recommendations.append("Consider deploying hybrid classical+PQC as a precaution")

    recommendations.append("Use NIST FIPS 203 (ML-KEM) for key encapsulation")
    recommendations.append("Use NIST FIPS 204 (ML-DSA) for digital signatures")
    recommendations.append("Use NIST FIPS 205 (SLH-DSA) for hash-based signatures as backup")

    return recommendations


def migration_checklist(assets: List[CryptoAsset]) -> List[Dict[str, Any]]:
    checklist: List[Dict[str, Any]] = []

    checklist.append({
        "item": "Cryptographic Asset Inventory",
        "status": "pending",
        "description": f"Catalog all {len(assets)} identified cryptographic assets",
        "critical": True,
    })

    checklist.append({
        "item": "Risk Assessment",
        "status": "pending",
        "description": "Assess quantum risk for each asset using NIST guidelines",
        "critical": True,
    })

    checklist.append({
        "item": "Hybrid Crypto Deployment",
        "status": "pending",
        "description": "Deploy hybrid classical+PQC for backward compatibility",
        "critical": True,
    })

    checklist.append({
        "item": "Key Management Update",
        "status": "pending",
        "description": "Update KMS for larger PQC key sizes (Kyber: ~1.2KB pub, Dilithium: ~2KB pub)",
        "critical": False,
    })

    checklist.append({
        "item": "TLS Configuration",
        "status": "pending",
        "description": "Configure TLS endpoints to support PQC cipher suites",
        "critical": True,
    })

    checklist.append({
        "item": "Certificate Migration",
        "status": "pending",
        "description": "Issue PQC-capable certificates or hybrid certificates",
        "critical": True,
    })

    checklist.append({
        "item": "Testing & Validation",
        "status": "pending",
        "description": "Comprehensive testing of PQC implementations",
        "critical": True,
    })

    checklist.append({
        "item": "Documentation & Training",
        "status": "pending",
        "description": "Staff training and updated security procedures",
        "critical": False,
    })

    checklist.append({
        "item": "Compliance Verification",
        "status": "pending",
        "description": "Verify compliance with NIST FIPS 203/204/205",
        "critical": False,
    })

    checklist.append({
        "item": "Continuous Monitoring",
        "status": "pending",
        "description": "Set up monitoring for crypto algorithm deprecation and quantum threats",
        "critical": False,
    })

    return checklist
