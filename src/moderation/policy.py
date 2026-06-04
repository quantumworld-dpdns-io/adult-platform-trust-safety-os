"""Policy engine for content moderation – rule-based + ML hybrid."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

import structlog

from src.moderation.classifier import ContentClassification

logger = structlog.get_logger(__name__)


class PolicyAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
    FLAG = "FLAG"
    REVIEW = "REVIEW"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class PolicyRule:
    id: str
    name: str
    description: str
    condition: str  # e.g. "nsfw_score > 0.9"
    action: PolicyAction
    severity: Severity
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyViolation:
    rule_id: str
    rule_name: str
    action: PolicyAction
    severity: Severity
    score: float
    details: str


class PolicyEngine:
    """Evaluate content against a set of configurable moderation rules.

    The engine supports both static keyword/threshold rules and ML-scored
    classification inputs.  Rules are evaluated in severity order (CRITICAL
    first) and the most severe matching rule determines the final action.
    """

    def __init__(self) -> None:
        self._rules: list[PolicyRule] = [
            PolicyRule(
                id="nsfw_critical",
                name="Critical NSFW Content",
                description="Reject content with extremely high NSFW scores",
                condition="nsfw_score > 0.95",
                action=PolicyAction.REJECT,
                severity=Severity.CRITICAL,
            ),
            PolicyRule(
                id="nsfw_high",
                name="High NSFW Content",
                description="Escalate content with high NSFW scores for human review",
                condition="nsfw_score > 0.85",
                action=PolicyAction.ESCALATE,
                severity=Severity.HIGH,
            ),
            PolicyRule(
                id="toxicity_high",
                name="High Toxicity",
                description="Reject content with high toxicity",
                condition="toxicity_score > 0.80",
                action=PolicyAction.REJECT,
                severity=Severity.HIGH,
            ),
            PolicyRule(
                id="violence_high",
                name="Violence Detected",
                description="Escalate violent content for urgent review",
                condition="violence_score > 0.70",
                action=PolicyAction.ESCALATE,
                severity=Severity.CRITICAL,
            ),
            PolicyRule(
                id="spam_medium",
                name="Spam Detection",
                description="Flag spam content",
                condition="spam_score > 0.60",
                action=PolicyAction.FLAG,
                severity=Severity.MEDIUM,
            ),
            PolicyRule(
                id="nsfw_medium",
                name="Moderate NSFW Content",
                description="Flag borderline NSFW content",
                condition="nsfw_score > 0.50",
                action=PolicyAction.FLAG,
                severity=Severity.LOW,
            ),
            PolicyRule(
                id="low_confidence",
                name="Low Confidence Classification",
                description="Send low-confidence results to human review",
                condition="confidence < 0.40",
                action=PolicyAction.REVIEW,
                severity=Severity.LOW,
            ),
        ]

    def evaluate_content(self, classification: ContentClassification) -> dict[str, Any]:
        """Evaluate a classified content against all active rules."""
        violations = self.apply_rules(classification)
        action = self._determine_action(violations)
        thresholds_met = self.check_thresholds(classification)

        return {
            "action": action.value,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "action": v.action.value,
                    "severity": v.severity.value,
                    "score": v.score,
                    "details": v.details,
                }
                for v in violations
            ],
            "thresholds_met": thresholds_met,
            "classification": {
                "labels": classification.labels,
                "scores": classification.scores,
                "confidence": classification.confidence,
            },
        }

    def apply_rules(self, classification: ContentClassification) -> list[PolicyViolation]:
        """Return all rules violated by the given classification."""
        violations: list[PolicyViolation] = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._evaluate_condition(rule.condition, classification):
                score = self._extract_score(rule.condition, classification)
                violations.append(
                    PolicyViolation(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        action=rule.action,
                        severity=rule.severity,
                        score=score,
                        details=f"Rule '{rule.name}' triggered: {rule.condition}",
                    )
                )

        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
        }
        violations.sort(key=lambda v: severity_order.get(v.severity, 99))
        return violations

    def check_thresholds(self, classification: ContentClassification) -> dict[str, bool]:
        """Check which score thresholds are exceeded."""
        return {
            "nsfw_critical": classification.nsfw_score > 0.95,
            "nsfw_high": classification.nsfw_score > 0.85,
            "nsfw_medium": classification.nsfw_score > 0.50,
            "toxicity_high": classification.toxicity_score > 0.80,
            "violence_high": classification.violence_score > 0.70,
            "spam_medium": classification.spam_score > 0.60,
            "low_confidence": classification.confidence < 0.40,
        }

    def get_policy_violations(self) -> list[dict[str, Any]]:
        """Return all configured rules with their current status."""
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "condition": r.condition,
                "action": r.action.value,
                "severity": r.severity.value,
                "enabled": r.enabled,
            }
            for r in self._rules
        ]

    def update_policy(
        self,
        rule_id: str,
        *,
        enabled: bool | None = None,
        condition: str | None = None,
        action: PolicyAction | None = None,
        severity: Severity | None = None,
    ) -> PolicyRule | None:
        """Update an existing rule by ID.  Returns the updated rule or None."""
        for rule in self._rules:
            if rule.id == rule_id:
                if enabled is not None:
                    rule.enabled = enabled
                if condition is not None:
                    rule.condition = condition
                if action is not None:
                    rule.action = action
                if severity is not None:
                    rule.severity = severity
                logger.info("policy_rule_updated", rule_id=rule_id)
                return rule
        return None

    def _determine_action(self, violations: list[PolicyViolation]) -> PolicyAction:
        if not violations:
            return PolicyAction.APPROVE

        severity_actions = {
            Severity.CRITICAL: PolicyAction.REJECT,
            Severity.HIGH: PolicyAction.ESCALATE,
            Severity.MEDIUM: PolicyAction.FLAG,
            Severity.LOW: PolicyAction.REVIEW,
        }

        for v in violations:
            if v.severity in severity_actions:
                return severity_actions[v.severity]

        return PolicyAction.APPROVE

    @staticmethod
    def _evaluate_condition(condition: str, c: ContentClassification) -> bool:
        """Safely evaluate a condition string against a classification."""
        namespace = {
            "nsfw_score": c.nsfw_score,
            "toxicity_score": c.toxicity_score,
            "violence_score": c.violence_score,
            "spam_score": c.spam_score,
            "confidence": c.confidence,
        }
        try:
            return bool(eval(condition, {"__builtins__": {}}, namespace))  # noqa: S307
        except Exception:  # noqa: BLE001
            return False

    @staticmethod
    def _extract_score(condition: str, c: ContentClassification) -> float:
        """Extract the numeric score referenced in a condition."""
        for attr in ("nsfw_score", "toxicity_score", "violence_score", "spam_score", "confidence"):
            if attr in condition:
                return getattr(c, attr)
        return 0.0
