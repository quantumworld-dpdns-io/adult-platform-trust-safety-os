from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelEndpoint:
    name: str
    base_url: str
    models: list[str]
    weight: int = 1
    healthy: bool = True
    last_health_check: float = 0.0
    request_count: int = 0
    avg_latency_ms: float = 0.0
    max_concurrent: int = 10
    current_load: int = 0


@dataclass
class RoutingDecision:
    endpoint: str
    model: str
    reason: str
    alternatives: list[str]


class ModelRouter:
    def __init__(self, health_check_interval: float = 30.0) -> None:
        self._endpoints: dict[str, ModelEndpoint] = {}
        self._health_check_interval = health_check_interval
        self._routing_history: list[RoutingDecision] = []
        self._model_aliases: dict[str, str] = {}

    def register_endpoint(
        self,
        name: str,
        base_url: str,
        models: list[str],
        weight: int = 1,
        max_concurrent: int = 10,
    ) -> None:
        self._endpoints[name] = ModelEndpoint(
            name=name,
            base_url=base_url,
            models=models,
            weight=weight,
            max_concurrent=max_concurrent,
        )
        logger.info("Registered endpoint %s with models: %s", name, models)

    def unregister_endpoint(self, name: str) -> None:
        self._endpoints.pop(name, None)

    def set_model_alias(self, alias: str, target: str) -> None:
        self._model_aliases[alias] = target

    def resolve_model(self, model: str) -> str:
        return self._model_aliases.get(model, model)

    def route_request(self, model: str) -> RoutingDecision:
        resolved = self.resolve_model(model)

        candidates = []
        for ep in self._endpoints.values():
            if not ep.healthy:
                continue
            if resolved in ep.models or any(m in resolved for m in ep.models):
                candidates.append(ep)

        if not candidates:
            for ep in self._endpoints.values():
                if ep.healthy:
                    candidates.append(ep)

        if not candidates:
            return RoutingDecision(
                endpoint="",
                model=resolved,
                reason="no_healthy_endpoints",
                alternatives=[],
            )

        candidates.sort(key=lambda e: (e.current_load / max(e.max_concurrent, 1)) - e.weight * 0.1)

        best = candidates[0]
        alternatives = [c.name for c in candidates[1:3]]

        decision = RoutingDecision(
            endpoint=best.name,
            model=resolved,
            reason="load_balanced",
            alternatives=alternatives,
        )

        self._routing_history.append(decision)
        if len(self._routing_history) > 1000:
            self._routing_history = self._routing_history[-1000:]

        return decision

    async def get_available_models(self) -> list[dict[str, Any]]:
        models = []
        for ep in self._endpoints.values():
            if ep.healthy:
                for model in ep.models:
                    models.append({
                        "model": model,
                        "endpoint": ep.name,
                        "base_url": ep.base_url,
                        "load": ep.current_load,
                    })
        return models

    async def health_check(self) -> dict[str, dict[str, Any]]:
        import httpx

        results = {}
        for name, ep in self._endpoints.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{ep.base_url}/api/tags")
                    ep.healthy = response.status_code == 200
                    ep.last_health_check = time.time()
                    results[name] = {
                        "healthy": ep.healthy,
                        "status_code": response.status_code,
                        "models": ep.models,
                    }
            except Exception as exc:
                ep.healthy = False
                ep.last_health_check = time.time()
                results[name] = {
                    "healthy": False,
                    "error": str(exc),
                    "models": ep.models,
                }
        return results

    async def load_balance(self, model: str, request_count: int = 1) -> list[RoutingDecision]:
        decisions = []
        for _ in range(request_count):
            decision = self.route_request(model)
            decisions.append(decision)
        return decisions

    def update_endpoint_load(self, endpoint_name: str, delta: int) -> None:
        if endpoint_name in self._endpoints:
            ep = self._endpoints[endpoint_name]
            ep.current_load = max(0, ep.current_load + delta)
            ep.request_count += max(0, delta)

    def get_endpoint_stats(self) -> dict[str, dict[str, Any]]:
        stats = {}
        for name, ep in self._endpoints.items():
            stats[name] = {
                "healthy": ep.healthy,
                "models": ep.models,
                "weight": ep.weight,
                "request_count": ep.request_count,
                "current_load": ep.current_load,
                "max_concurrent": ep.max_concurrent,
                "avg_latency_ms": ep.avg_latency_ms,
            }
        return stats

    def get_routing_stats(self) -> dict[str, Any]:
        if not self._routing_history:
            return {"total_routes": 0, "endpoints_used": {}}
        endpoint_counts: dict[str, int] = {}
        for d in self._routing_history:
            endpoint_counts[d.endpoint] = endpoint_counts.get(d.endpoint, 0) + 1
        return {
            "total_routes": len(self._routing_history),
            "endpoints_used": endpoint_counts,
        }
