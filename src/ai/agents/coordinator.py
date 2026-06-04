from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from src.ai.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str = ""
    task_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    status: str = "pending"
    result: Any = None
    error: str | None = None


@dataclass
class WorkflowStep:
    agent_name: str
    task_type: str
    payload_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    depends_on: list[str] = field(default_factory=list)
    condition: Callable[[dict[str, Any]], bool] | None = None


@dataclass
class WorkflowDefinition:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MultiAgentCoordinator:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}
        self._task_queue: list[AgentTask] = []
        self._completed_tasks: dict[str, AgentTask] = {}
        self._workflows: dict[str, WorkflowDefinition] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent
        logger.info("Registered agent: %s", agent.name)

    def unregister_agent(self, agent_name: str) -> None:
        self._agents.pop(agent_name, None)

    def get_agent(self, agent_name: str) -> BaseAgent | None:
        return self._agents.get(agent_name)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    async def dispatch_task(self, task: AgentTask) -> AgentTask:
        agent = self._agents.get(task.agent_name)
        if agent is None:
            task.status = "failed"
            task.error = f"Agent not found: {task.agent_name}"
            logger.error("Cannot dispatch task %s: agent %s not found", task.id, task.agent_name)
            return task

        task.status = "running"
        self._task_queue.append(task)

        try:
            input_data = task.payload.get("input", "")
            context = task.payload.get("context", {})
            result = await agent.run(input_data, context)

            task.result = result
            task.status = "completed"
            self._completed_tasks[task.id] = task
            logger.info("Task %s completed by agent %s", task.id, task.agent_name)

        except Exception as exc:
            task.status = "failed"
            task.error = str(exc)
            logger.error("Task %s failed: %s", task.id, exc)

        return task

    async def collect_results(self, task_ids: list[str]) -> dict[str, Any]:
        results = {}
        for tid in task_ids:
            if tid in self._completed_tasks:
                task = self._completed_tasks[tid]
                results[tid] = {
                    "status": task.status,
                    "result": task.result,
                    "error": task.error,
                    "agent": task.agent_name,
                }
            else:
                results[tid] = {"status": "not_found"}
        return results

    async def orchestrate_workflow(
        self,
        workflow: WorkflowDefinition,
        initial_input: dict[str, Any],
    ) -> dict[str, Any]:
        context = dict(initial_input)
        step_results: dict[str, Any] = {}
        completed_steps: set[str] = set()

        for step in workflow.steps:
            deps_met = all(d in completed_steps for d in step.depends_on)
            if not deps_met:
                logger.warning("Skipping step %s: dependencies not met", step.agent_name)
                continue

            if step.condition and not step.condition(context):
                logger.info("Skipping step %s: condition not met", step.agent_name)
                continue

            payload = step.payload_transform(context) if step.payload_transform else context

            task = AgentTask(
                agent_name=step.agent_name,
                task_type=step.task_type,
                payload=payload,
            )

            completed_task = await self.dispatch_task(task)
            step_results[step.agent_name] = completed_task.result
            completed_steps.add(step.agent_name)

            context[f"{step.agent_name}_result"] = completed_task.result

        return {
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "step_results": step_results,
            "final_context": context,
        }

    async def parallel_execute(self, tasks: list[AgentTask]) -> list[AgentTask]:
        coros = [self.dispatch_task(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        completed = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Parallel task failed: %s", result)
            elif isinstance(result, AgentTask):
                completed.append(result)
        return completed

    def create_workflow(self, name: str, steps: list[WorkflowStep], metadata: dict[str, Any] | None = None) -> WorkflowDefinition:
        workflow = WorkflowDefinition(name=name, steps=steps, metadata=metadata or {})
        self._workflows[workflow.id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        return self._workflows.get(workflow_id)

    def get_task_status(self, task_id: str) -> str | None:
        if task_id in self._completed_tasks:
            return self._completed_tasks[task_id].status
        for task in self._task_queue:
            if task.id == task_id:
                return task.status
        return None

    def get_queue_stats(self) -> dict[str, int]:
        return {
            "pending": sum(1 for t in self._task_queue if t.status == "pending"),
            "running": sum(1 for t in self._task_queue if t.status == "running"),
            "completed": sum(1 for t in self._task_queue if t.status == "completed"),
            "failed": sum(1 for t in self._task_queue if t.status == "failed"),
            "total": len(self._task_queue),
        }
