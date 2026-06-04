from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    operation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    cost: float = 0.0


@dataclass
class CostReport:
    total_cost: float
    total_tokens: int
    by_model: dict[str, dict[str, Any]]
    by_operation: dict[str, dict[str, Any]]
    period: str
    daily_breakdown: dict[str, float] = field(default_factory=dict)


DEFAULT_PRICING = {
    "llama3.1": {
        "input_per_1k": 0.0001,
        "output_per_1k": 0.0002,
    },
    "llama3.1:8b": {
        "input_per_1k": 0.0001,
        "output_per_1k": 0.0002,
    },
    "llama3.1:70b": {
        "input_per_1k": 0.0005,
        "output_per_1k": 0.001,
    },
    "mistral": {
        "input_per_1k": 0.0001,
        "output_per_1k": 0.0002,
    },
    "codellama": {
        "input_per_1k": 0.00015,
        "output_per_1k": 0.0003,
    },
    "nomic-embed-text": {
        "input_per_1k": 0.00005,
        "output_per_1k": 0.0,
    },
}


class CostTracker:
    def __init__(self, pricing: dict[str, dict[str, float]] | None = None) -> None:
        self._pricing = pricing or dict(DEFAULT_PRICING)
        self._usages: list[TokenUsage] = []
        self._max_entries = 100000

    def track_tokens(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        operation: str = "chat",
    ) -> TokenUsage:
        pricing = self._pricing.get(model, {"input_per_1k": 0.0, "output_per_1k": 0.0})

        cost = (
            (prompt_tokens / 1000.0) * pricing["input_per_1k"]
            + (completion_tokens / 1000.0) * pricing["output_per_1k"]
        )

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            model=model,
            operation=operation,
            cost=cost,
        )

        self._usages.append(usage)

        if len(self._usages) > self._max_entries:
            self._usages = self._usages[-self._max_entries:]

        return usage

    def get_cost_report(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        model: str | None = None,
    ) -> CostReport:
        filtered = self._filter_usages(start_date, end_date, model)

        total_cost = sum(u.cost for u in filtered)
        total_tokens = sum(u.total_tokens for u in filtered)

        by_model: dict[str, dict[str, Any]] = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "count": 0})
        by_operation: dict[str, dict[str, Any]] = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "count": 0})
        daily: dict[str, float] = defaultdict(float)

        for usage in filtered:
            by_model[usage.model]["cost"] += usage.cost
            by_model[usage.model]["tokens"] += usage.total_tokens
            by_model[usage.model]["count"] += 1

            by_operation[usage.operation]["cost"] += usage.cost
            by_operation[usage.operation]["tokens"] += usage.total_tokens
            by_operation[usage.operation]["count"] += 1

            day = usage.timestamp[:10]
            daily[day] += usage.cost

        period = "all"
        if start_date and end_date:
            period = f"{start_date} to {end_date}"
        elif start_date:
            period = f"from {start_date}"
        elif end_date:
            period = f"until {end_date}"

        return CostReport(
            total_cost=total_cost,
            total_tokens=total_tokens,
            by_model=dict(by_model),
            by_operation=dict(by_operation),
            period=period,
            daily_breakdown=dict(daily),
        )

    def get_daily_cost(self, date: str | None = None) -> float:
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return sum(u.cost for u in self._usages if u.timestamp.startswith(date))

    def set_pricing(self, model: str, input_per_1k: float, output_per_1k: float) -> None:
        self._pricing[model] = {
            "input_per_1k": input_per_1k,
            "output_per_1k": output_per_1k,
        }

    def get_pricing(self) -> dict[str, dict[str, float]]:
        return dict(self._pricing)

    def _filter_usages(
        self,
        start_date: str | None,
        end_date: str | None,
        model: str | None,
    ) -> list[TokenUsage]:
        result = self._usages
        if start_date:
            result = [u for u in result if u.timestamp >= start_date]
        if end_date:
            result = [u for u in result if u.timestamp <= end_date + "T23:59:59"]
        if model:
            result = [u for u in result if u.model == model]
        return result

    def get_model_costs(self) -> dict[str, float]:
        costs: dict[str, float] = defaultdict(float)
        for usage in self._usages:
            costs[usage.model] += usage.cost
        return dict(costs)

    def get_total_cost(self) -> float:
        return sum(u.cost for u in self._usages)

    def get_total_tokens(self) -> int:
        return sum(u.total_tokens for u in self._usages)
