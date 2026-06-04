from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TraceSpan:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None
    name: str = ""
    trace_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    model: str = ""
    token_count: int = 0
    cost: float = 0.0
    error: str | None = None


@dataclass
class Trace:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    spans: list[TraceSpan] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    total_tokens: int = 0
    total_cost: float = 0.0


class LLMTracer:
    def __init__(self, max_traces: int = 10000) -> None:
        self._traces: dict[str, Trace] = {}
        self._active_spans: dict[str, TraceSpan] = {}
        self._max_traces = max_traces
        self._latencies: list[float] = []
        self._model_latencies: dict[str, list[float]] = {}

    def trace_call(
        self,
        model: str,
        operation: str,
        input_data: Any = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        trace_id = str(uuid.uuid4())
        if trace_id not in self._traces:
            self._traces[trace_id] = Trace(
                id=trace_id,
                name=operation,
                start_time=time.time(),
            )

        span = TraceSpan(
            trace_id=trace_id,
            name=operation,
            start_time=time.time(),
            model=model,
            attributes=attributes or {},
        )

        if input_data is not None:
            span.attributes["input"] = str(input_data)[:1000]

        self._active_spans[span.id] = span
        return span

    def end_trace(self, span: TraceSpan, output: Any = None, error: str | None = None) -> TraceSpan:
        span.end_time = time.time()
        span.duration_ms = (span.end_time - span.start_time) * 1000

        if output is not None:
            span.attributes["output"] = str(output)[:1000]

        if error:
            span.error = error
            span.status = "error"

        self._latencies.append(span.duration_ms)
        if span.model:
            self._model_latencies.setdefault(span.model, []).append(span.duration_ms)

        self._active_spans.pop(span.id, None)

        trace = self._traces.get(span.trace_id)
        if trace:
            trace.spans.append(span)
            trace.end_time = time.time()
            trace.total_duration_ms = (trace.end_time - trace.start_time) * 1000
            trace.total_tokens += span.token_count
            trace.total_cost += span.cost

        if len(self._traces) > self._max_traces:
            oldest_key = min(self._traces, key=lambda k: self._traces[k].start_time)
            del self._traces[oldest_key]

        return span

    def get_trace(self, trace_id: str) -> Trace | None:
        return self._traces.get(trace_id)

    def list_traces(self, limit: int = 100, model: str | None = None) -> list[Trace]:
        traces = list(self._traces.values())
        if model:
            traces = [t for t in traces if any(s.model == model for s in t.spans)]
        traces.sort(key=lambda t: t.start_time, reverse=True)
        return traces[:limit]

    def get_latency_stats(self, model: str | None = None) -> dict[str, Any]:
        if model:
            latencies = self._model_latencies.get(model, [])
        else:
            latencies = self._latencies

        if not latencies:
            return {"count": 0, "min": 0, "max": 0, "mean": 0, "p50": 0, "p95": 0, "p99": 0}

        sorted_lat = sorted(latencies)
        count = len(sorted_lat)
        return {
            "count": count,
            "min": round(sorted_lat[0], 2),
            "max": round(sorted_lat[-1], 2),
            "mean": round(sum(sorted_lat) / count, 2),
            "p50": round(sorted_lat[int(count * 0.5)], 2),
            "p95": round(sorted_lat[int(count * 0.95)], 2),
            "p99": round(sorted_lat[int(count * 0.99)], 2),
        }

    def export_traces(self, format: str = "json", limit: int = 100) -> str:
        traces = self.list_traces(limit=limit)

        if format == "json":
            data = []
            for trace in traces:
                trace_data = {
                    "id": trace.id,
                    "name": trace.name,
                    "start_time": datetime.fromtimestamp(trace.start_time).isoformat() if trace.start_time else None,
                    "total_duration_ms": trace.total_duration_ms,
                    "total_tokens": trace.total_tokens,
                    "total_cost": trace.total_cost,
                    "metadata": trace.metadata,
                    "spans": [
                        {
                            "id": span.id,
                            "name": span.name,
                            "model": span.model,
                            "duration_ms": span.duration_ms,
                            "status": span.status,
                            "error": span.error,
                            "attributes": span.attributes,
                        }
                        for span in trace.spans
                    ],
                }
                data.append(trace_data)
            return json.dumps(data, indent=2)

        elif format == "summary":
            lines = [f"Traces: {len(traces)}"]
            for trace in traces:
                lines.append(
                    f"  [{trace.id[:8]}] {trace.name}: "
                    f"{trace.total_duration_ms:.0f}ms, "
                    f"{trace.total_tokens} tokens, "
                    f"${trace.total_cost:.4f}"
                )
            return "\n".join(lines)

        return json.dumps({"error": f"Unknown format: {format}"})

    def clear(self) -> None:
        self._traces.clear()
        self._active_spans.clear()
        self._latencies.clear()
        self._model_latencies.clear()
