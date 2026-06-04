"""Tests for the PolicyEngine: rule evaluation, threshold check, violation detection."""

from __future__ import annotations

import pytest

from src.moderation.classifier import ContentClassification
from src.moderation.policy import PolicyAction, PolicyEngine, Severity


@pytest.fixture
def engine():
    return PolicyEngine()


def test_rule_evaluation_approve(engine):
    classification = ContentClassification(
        nsfw_score=0.1,
        toxicity_score=0.05,
        violence_score=0.0,
        spam_score=0.0,
        confidence=0.9,
    )
    result = engine.evaluate_content(classification)
    assert result["action"] == PolicyAction.APPROVE.value
    assert len(result["violations"]) == 0


def test_threshold_check_nsfw_critical(engine):
    classification = ContentClassification(nsfw_score=0.98)
    thresholds = engine.check_thresholds(classification)
    assert thresholds["nsfw_critical"] is True


def test_threshold_check_nsfw_high(engine):
    classification = ContentClassification(nsfw_score=0.90)
    thresholds = engine.check_thresholds(classification)
    assert thresholds["nsfw_high"] is True


def test_threshold_check_nsfw_medium(engine):
    classification = ContentClassification(nsfw_score=0.60)
    thresholds = engine.check_thresholds(classification)
    assert thresholds["nsfw_medium"] is True


def test_threshold_check_toxicity_high(engine):
    classification = ContentClassification(toxicity_score=0.85)
    thresholds = engine.check_thresholds(classification)
    assert thresholds["toxicity_high"] is True


def test_threshold_check_violence_high(engine):
    classification = ContentClassification(violence_score=0.75)
    thresholds = engine.check_thresholds(classification)
    assert thresholds["violence_high"] is True


def test_violation_detection_nsfw_critical(engine):
    classification = ContentClassification(nsfw_score=0.99)
    result = engine.evaluate_content(classification)
    assert result["action"] == PolicyAction.REJECT.value
    violation_ids = [v["rule_id"] for v in result["violations"]]
    assert "nsfw_critical" in violation_ids


def test_violation_detection_nsfw_high(engine):
    classification = ContentClassification(nsfw_score=0.92)
    result = engine.evaluate_content(classification)
    violation_ids = [v["rule_id"] for v in result["violations"]]
    assert "nsfw_high" in violation_ids


def test_violation_detection_toxicity(engine):
    classification = ContentClassification(toxicity_score=0.85)
    result = engine.evaluate_content(classification)
    assert result["action"] == PolicyAction.ESCALATE.value


def test_violation_detection_violence(engine):
    classification = ContentClassification(violence_score=0.80)
    result = engine.evaluate_content(classification)
    violation_ids = [v["rule_id"] for v in result["violations"]]
    assert "violence_high" in violation_ids


def test_violation_detection_spam(engine):
    classification = ContentClassification(spam_score=0.70)
    result = engine.evaluate_content(classification)
    assert result["action"] == PolicyAction.FLAG.value


def test_violation_severity_ordering(engine):
    classification = ContentClassification(
        nsfw_score=0.99,
        spam_score=0.70,
    )
    result = engine.evaluate_content(classification)
    assert len(result["violations"]) >= 2
    first_v = result["violations"][0]
    assert first_v["severity"] == Severity.CRITICAL.value


def test_apply_rules_disabled(engine):
    engine.update_policy("nsfw_critical", enabled=False)
    classification = ContentClassification(nsfw_score=0.99)
    violations = engine.apply_rules(classification)
    rule_ids = [v.rule_id for v in violations]
    assert "nsfw_critical" not in rule_ids


def test_get_policy_violations(engine):
    policies = engine.get_policy_violations()
    assert isinstance(policies, list)
    assert len(policies) > 0
    for p in policies:
        assert "id" in p
        assert "name" in p
        assert "action" in p
        assert "severity" in p
