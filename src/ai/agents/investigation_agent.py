from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime

from src.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class InvestigationReport:
    id: str = ""
    target_type: str = ""
    target_id: str = ""
    summary: str = ""
    findings: list[dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0
    recommendations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class UserPattern:
    pattern_type: str
    description: str
    frequency: int
    severity: str
    evidence: list[dict[str, Any]] = field(default_factory=list)


class InvestigationAgent(BaseAgent):
    def __init__(self, model: str = "llama3.1") -> None:
        super().__init__(
            name="investigation_agent",
            model=model,
            system_prompt=self._build_system_prompt(),
        )
        self._active_investigations: dict[str, InvestigationReport] = {}

    def _build_system_prompt(self) -> str:
        return (
            "You are an investigation agent for trust and safety operations. "
            "Your role is to thoroughly investigate users, content, and patterns "
            "that may indicate policy violations, fraud, or abuse. "
            "Always provide evidence-based findings and actionable recommendations."
        )

    async def investigate_user(
        self,
        user_id: str,
        user_data: dict[str, Any] | None = None,
        content_history: list[dict[str, Any]] | None = None,
        reported_by: str | None = None,
    ) -> InvestigationReport:
        self.add_to_memory({"type": "investigation_start", "target": "user", "user_id": user_id})

        report = InvestigationReport(
            id=f"inv_user_{user_id}",
            target_type="user",
            target_id=user_id,
        )

        context = f"Investigating user: {user_id}\n"
        if user_data:
            context += f"User data: {user_data}\n"
        if content_history:
            context += f"Content history ({len(content_history)} items): {content_history[:10]}\n"
        if reported_by:
            context += f"Reported by: {reported_by}\n"

        findings_text = await self.think(context)

        report.summary = findings_text
        report.findings = self._parse_findings(findings_text)
        report.risk_score = self._calculate_risk_score(report.findings)
        report.recommendations = await self._generate_recommendations(report)

        self._active_investigations[report.id] = report
        self.add_to_memory({"type": "investigation_complete", "report_id": report.id, "risk_score": report.risk_score})

        return report

    async def investigate_content(
        self,
        content_id: str,
        content_data: dict[str, Any] | None = None,
        reports: list[dict[str, Any]] | None = None,
    ) -> InvestigationReport:
        self.add_to_memory({"type": "investigation_start", "target": "content", "content_id": content_id})

        report = InvestigationReport(
            id=f"inv_content_{content_id}",
            target_type="content",
            target_id=content_id,
        )

        context = f"Investigating content: {content_id}\n"
        if content_data:
            context += f"Content data: {content_data}\n"
        if reports:
            context += f"Reports ({len(reports)}): {reports[:10]}\n"

        findings_text = await self.think(context)

        report.summary = findings_text
        report.findings = self._parse_findings(findings_text)
        report.risk_score = self._calculate_risk_score(report.findings)
        report.recommendations = await self._generate_recommendations(report)

        self._active_investigations[report.id] = report
        self.add_to_memory({"type": "investigation_complete", "report_id": report.id, "risk_score": report.risk_score})

        return report

    async def find_patterns(
        self,
        data_points: list[dict[str, Any]],
        pattern_type: str | None = None,
    ) -> list[UserPattern]:
        if not data_points:
            return []

        context = (
            f"Analyze {len(data_points)} data points for patterns.\n"
            f"Pattern type focus: {pattern_type or 'all'}\n"
            f"Data samples: {data_points[:20]}\n"
        )

        analysis = await self.think(context)

        patterns = self._extract_patterns(analysis, data_points)
        return patterns

    async def generate_report(
        self,
        investigation_ids: list[str] | None = None,
        summary_query: str | None = None,
    ) -> str:
        reports_to_include = []
        if investigation_ids:
            for inv_id in investigation_ids:
                if inv_id in self._active_investigations:
                    reports_to_include.append(self._active_investigations[inv_id])
        else:
            reports_to_include = list(self._active_investigations.values())

        context = f"Generate summary report for {len(reports_to_include)} investigations.\n"
        for r in reports_to_include:
            context += (
                f"\n--- Investigation {r.id} ---\n"
                f"Target: {r.target_type} ({r.target_id})\n"
                f"Risk Score: {r.risk_score}\n"
                f"Summary: {r.summary[:200]}\n"
            )
        if summary_query:
            context += f"\nSpecific query: {summary_query}\n"

        report_text = await self.think(context)
        return report_text

    def _parse_findings(self, text: str) -> list[dict[str, Any]]:
        findings = []
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                finding_text = line.lstrip("-*• ").strip()
                if finding_text:
                    severity = "medium"
                    lower = finding_text.lower()
                    if any(w in lower for w in ["critical", "severe", "dangerous", "illegal"]):
                        severity = "high"
                    elif any(w in lower for w in ["minor", "low", "minimal"]):
                        severity = "low"
                    findings.append({"finding": finding_text, "severity": severity})
        return findings

    def _calculate_risk_score(self, findings: list[dict[str, Any]]) -> float:
        if not findings:
            return 0.0
        severity_map = {"high": 1.0, "medium": 0.5, "low": 0.2}
        total = sum(severity_map.get(f.get("severity", "medium"), 0.5) for f in findings)
        return min(total / len(findings), 1.0)

    async def _generate_recommendations(self, report: InvestigationReport) -> list[str]:
        context = (
            f"Investigation report for {report.target_type} {report.target_id}\n"
            f"Risk score: {report.risk_score}\n"
            f"Findings: {report.findings}\n"
            "Generate 3-5 specific, actionable recommendations."
        )
        response = await self.think(context)

        recommendations = []
        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*") or line.startswith("•"):
                rec = line.lstrip("-*• ").strip()
                if rec:
                    recommendations.append(rec)
        return recommendations[:5] if recommendations else [response[:200]]

    def _extract_patterns(self, analysis: str, data_points: list[dict[str, Any]]) -> list[UserPattern]:
        patterns = []
        lines = analysis.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                desc = line.lstrip("-* ").strip()
                if desc:
                    patterns.append(
                        UserPattern(
                            pattern_type="detected",
                            description=desc,
                            frequency=1,
                            severity="medium",
                            evidence=[],
                        )
                    )
        return patterns[:10]

    def get_active_investigations(self) -> list[InvestigationReport]:
        return list(self._active_investigations.values())
