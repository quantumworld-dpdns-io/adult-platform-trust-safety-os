"""ETL pipeline: step management, execution, status tracking, and error handling."""

from __future__ import annotations

import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger(__name__)


class PipelineStep:
    def __init__(
        self,
        name: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        description: str = "",
    ) -> None:
        self.name = name
        self.handler = handler
        self.description = description
        self.step_id = str(uuid.uuid4())


class PipelineRun:
    def __init__(self, pipeline_id: str, pipeline_name: str) -> None:
        self.run_id = str(uuid.uuid4())
        self.pipeline_id = pipeline_id
        self.pipeline_name = pipeline_name
        self.status = "pending"
        self.started_at: str | None = None
        self.completed_at: str | None = None
        self.current_step: str | None = None
        self.step_results: list[dict[str, Any]] = []
        self.error: str | None = None
        self.input_data: dict[str, Any] = {}
        self.output_data: dict[str, Any] = {}


class ETLPipeline:
    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self.pipeline_id = str(uuid.uuid4())
        self._steps: list[PipelineStep] = []
        self._runs: dict[str, PipelineRun] = {}
        self._error_handlers: list[Callable[[str, Exception, dict[str, Any]], Awaitable[dict[str, Any]] | None]] = []

    def add_step(
        self,
        name: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
        description: str = "",
        position: int | None = None,
    ) -> dict[str, Any]:
        step = PipelineStep(name=name, handler=handler, description=description)

        if position is not None and 0 <= position <= len(self._steps):
            self._steps.insert(position, step)
        else:
            self._steps.append(step)

        return {
            "step_name": name,
            "step_id": step.step_id,
            "position": self._steps.index(step),
            "total_steps": len(self._steps),
        }

    def remove_step(self, name: str) -> bool:
        original_len = len(self._steps)
        self._steps = [s for s in self._steps if s.name != name]
        return len(self._steps) < original_len

    def on_error(
        self,
        handler: Callable[[str, Exception, dict[str, Any]], Awaitable[dict[str, Any]] | None],
    ) -> None:
        self._error_handlers.append(handler)

    async def run(
        self,
        input_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run = PipelineRun(self.pipeline_id, self.name)
        run.input_data = input_data or {}
        run.status = "running"
        run.started_at = datetime.now(timezone.utc).isoformat()
        self._runs[run.run_id] = run

        logger.info("pipeline_started", pipeline=self.name, run_id=run.run_id, steps=len(self._steps))

        current_data = dict(input_data or {})
        for step in self._steps:
            run.current_step = step.name
            step_start = time.monotonic()

            try:
                step_result = await step.handler(current_data)
                step_duration = time.monotonic() - step_start

                run.step_results.append({
                    "step_name": step.name,
                    "status": "completed",
                    "duration_ms": round(step_duration * 1000, 2),
                    "output_keys": list(step_result.keys()) if isinstance(step_result, dict) else [],
                })

                if isinstance(step_result, dict):
                    current_data.update(step_result)

                logger.info(
                    "pipeline_step_completed",
                    pipeline=self.name,
                    step=step.name,
                    duration_ms=round(step_duration * 1000, 2),
                )

            except Exception as e:
                step_duration = time.monotonic() - step_start
                error_msg = f"Step '{step.name}' failed: {e}"

                run.step_results.append({
                    "step_name": step.name,
                    "status": "failed",
                    "error": str(e),
                    "duration_ms": round(step_duration * 1000, 2),
                    "traceback": traceback.format_exc(),
                })

                error_handled = False
                for handler in self._error_handlers:
                    try:
                        result = await handler(step.name, e, current_data)
                        if result is not None:
                            current_data.update(result)
                            error_handled = True
                            break
                    except Exception:
                        pass

                if not error_handled:
                    run.status = "failed"
                    run.error = error_msg
                    run.completed_at = datetime.now(timezone.utc).isoformat()
                    run.output_data = current_data

                    logger.error(
                        "pipeline_failed",
                        pipeline=self.name,
                        step=step.name,
                        error=str(e),
                    )
                    return self._format_run(run)

                run.step_results.append({
                    "step_name": step.name,
                    "status": "recovered",
                    "recovery": "error_handler",
                })

        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc).isoformat()
        run.output_data = current_data
        run.current_step = None

        logger.info("pipeline_completed", pipeline=self.name, run_id=run.run_id)

        return self._format_run(run)

    def _format_run(self, run: PipelineRun) -> dict[str, Any]:
        started = datetime.fromisoformat(run.started_at) if run.started_at else None
        completed = datetime.fromisoformat(run.completed_at) if run.completed_at else None
        duration_ms = 0.0
        if started and completed:
            duration_ms = (completed - started).total_seconds() * 1000

        return {
            "run_id": run.run_id,
            "pipeline_name": run.pipeline_name,
            "status": run.status,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "duration_ms": round(duration_ms, 2),
            "current_step": run.current_step,
            "total_steps": len(self._steps),
            "completed_steps": sum(1 for s in run.step_results if s["status"] == "completed"),
            "failed_steps": sum(1 for s in run.step_results if s["status"] == "failed"),
            "step_results": run.step_results,
            "error": run.error,
            "output_keys": list(run.output_data.keys()) if run.output_data else [],
        }

    def get_status(self) -> dict[str, Any]:
        runs = list(self._runs.values())
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.name,
            "description": self.description,
            "total_steps": len(self._steps),
            "step_names": [s.name for s in self._steps],
            "total_runs": len(runs),
            "completed_runs": sum(1 for r in runs if r.status == "completed"),
            "failed_runs": sum(1 for r in runs if r.status == "failed"),
            "running_runs": sum(1 for r in runs if r.status == "running"),
        }

    def get_results(self, run_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        if run_id:
            run = self._runs.get(run_id)
            if run is None:
                return {"error": "Run not found", "run_id": run_id}
            return self._format_run(run)

        return [self._format_run(r) for r in self._runs.values()]
