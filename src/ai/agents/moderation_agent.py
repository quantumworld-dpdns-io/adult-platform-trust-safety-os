from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.ai.agents.base_agent import BaseAgent
from src.ai.classifiers.ensemble import EnsembleClassifier, EnsembleResult

logger = logging.getLogger(__name__)


@dataclass
class ModerationDecision:
    action: str
    confidence: float
    reason: str
    categories: list[str]
    details: dict[str, Any] = field(default_factory=dict)


class ModerationAgent(BaseAgent):
    def __init__(
        self,
        ensemble_classifier: EnsembleClassifier | None = None,
        model: str = "llama3.1",
    ) -> None:
        super().__init__(
            name="moderation_agent",
            model=model,
            system_prompt=self._build_system_prompt(),
        )
        self._classifier = ensemble_classifier or EnsembleClassifier()
        self._decision_history: list[ModerationDecision] = []

    def _build_system_prompt(self) -> str:
        return (
            "You are a content moderation agent for an adult platform. "
            "Your role is to analyze content and make fair, consistent moderation decisions. "
            "You must consider platform policies, user safety, and legal requirements. "
            "Always explain your reasoning clearly."
        )

    async def analyze_content(
        self,
        content_type: str,
        content: str | None = None,
        image_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.add_to_memory({"type": "analysis_start", "content_type": content_type})

        ensemble_result = await self._classifier.classify(text=content, image_path=image_path)

        analysis = {
            "content_type": content_type,
            "ensemble_result": {
                "decision": ensemble_result.decision,
                "confidence": ensemble_result.confidence,
                "reasons": ensemble_result.reasons,
            },
            "metadata": metadata or {},
        }

        context_msg = (
            f"Content type: {content_type}\n"
            f"Ensemble decision: {ensemble_result.decision} (confidence: {ensemble_result.confidence:.2f})\n"
            f"Reasons: {', '.join(ensemble_result.reasons)}\n"
        )
        if content:
            context_msg += f"Content preview: {content[:500]}\n"
        if metadata:
            context_msg += f"Metadata: {metadata}\n"

        ai_analysis = await self.think(context_msg)
        analysis["ai_reasoning"] = ai_analysis

        self.add_to_memory({"type": "analysis_complete", "analysis": analysis})
        return analysis

    async def make_decision(
        self,
        analysis: dict[str, Any],
        user_history: dict[str, Any] | None = None,
        platform_rules: dict[str, Any] | None = None,
    ) -> ModerationDecision:
        ensemble_data = analysis.get("ensemble_result", {})
        decision_str = ensemble_data.get("decision", "ALLOW")
        confidence = ensemble_data.get("confidence", 0.0)
        reasons = ensemble_data.get("reasons", [])

        user_violations = user_history.get("violations", []) if user_history else []
        account_age = user_history.get("account_age_days", 365) if user_history else 365

        risk_multiplier = 1.0
        if len(user_violations) > 3:
            risk_multiplier = 1.3
        elif len(user_violations) > 0:
            risk_multiplier = 1.1

        if account_age < 30:
            risk_multiplier *= 1.15

        adjusted_confidence = min(confidence * risk_multiplier, 1.0)

        if adjusted_confidence >= 0.8:
            action = "BLOCK"
        elif adjusted_confidence >= 0.5:
            action = "REVIEW"
        elif adjusted_confidence >= 0.2:
            action = "FLAG"
        else:
            action = "ALLOW"

        if platform_rules:
            auto_block = platform_rules.get("auto_block_categories", [])
            for reason in reasons:
                category = reason.split(":")[0].strip()
                if category in auto_block:
                    action = "BLOCK"
                    break

        categories = [reason.split(":")[0].strip() for reason in reasons if ":" in reason]

        decision = ModerationDecision(
            action=action,
            confidence=adjusted_confidence,
            reason=self._build_decision_reason(action, reasons, user_violations),
            categories=categories,
            details={
                "ensemble_decision": decision_str,
                "risk_multiplier": risk_multiplier,
                "user_violations": len(user_violations),
                "account_age_days": account_age,
            },
        )

        self._decision_history.append(decision)
        self.add_to_memory({
            "type": "decision_made",
            "action": action,
            "confidence": adjusted_confidence,
            "categories": categories,
        })

        return decision

    async def explain_decision(self, decision: ModerationDecision) -> str:
        context = (
            f"Moderation decision: {decision.action}\n"
            f"Confidence: {decision.confidence:.2f}\n"
            f"Categories: {', '.join(decision.categories)}\n"
            f"Reason: {decision.reason}\n"
            f"Details: {decision.details}\n\n"
            "Provide a clear, user-facing explanation of this moderation decision."
        )

        explanation = await self.think(context)
        return explanation

    def _build_decision_reason(self, action: str, reasons: list[str], violations: list[str]) -> str:
        parts = [f"Action: {action}"]
        if reasons:
            parts.append(f"Triggered categories: {'; '.join(reasons)}")
        if violations:
            parts.append(f"User has {len(violations)} prior violations")
        return " | ".join(parts)

    def get_decision_history(self, limit: int = 50) -> list[ModerationDecision]:
        return self._decision_history[-limit:]
