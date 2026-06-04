from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    OBSERVING = "observing"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentMemory:
    entries: list[dict[str, Any]] = field(default_factory=list)
    max_size: int = 100

    def add(self, entry: dict[str, Any]) -> None:
        entry["timestamp"] = str(uuid.uuid4())
        self.entries.append(entry)
        if len(self.entries) > self.max_size:
            self.entries = self.entries[-self.max_size:]

    def search(self, query: str) -> list[dict[str, Any]]:
        query_lower = query.lower()
        return [e for e in self.entries if query_lower in str(e).lower()]

    def get_recent(self, n: int = 10) -> list[dict[str, Any]]:
        return self.entries[-n:]


@dataclass
class ToolCall:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None


@dataclass
class AgentStep:
    thought: str = ""
    action: str = ""
    observation: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


ToolFunc = Callable[..., Awaitable[Any]]


class BaseAgent:
    def __init__(
        self,
        name: str = "base_agent",
        model: str = "llama3.1",
        system_prompt: str = "",
        max_iterations: int = 10,
        tools: dict[str, ToolFunc] | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.max_iterations = max_iterations
        self.state = AgentState.IDLE
        self.memory = AgentMemory()
        self._tools: dict[str, ToolFunc] = tools or {}
        self._ollama_client = None
        self._history: list[AgentStep] = []

    def _default_system_prompt(self) -> str:
        return (
            f"You are {self.name}, an AI agent. "
            "Think step by step. Use tools when needed. "
            "Provide clear reasoning for your actions."
        )

    def _get_ollama(self):
        if self._ollama_client is None:
            from src.ai.ollama_client import OllamaClient

            self._ollama_client = OllamaClient()
        return self._ollama_client

    async def think(self, input_data: str, context: dict[str, Any] | None = None) -> str:
        self.state = AgentState.THINKING

        memory_context = ""
        recent = self.memory.get_recent(5)
        if recent:
            memory_context = "\nRecent memory:\n" + "\n".join(str(e) for e in recent)

        tool_descriptions = self._get_tool_descriptions()
        tools_section = f"\nAvailable tools:\n{tool_descriptions}" if tool_descriptions else ""

        messages = [
            {"role": "system", "content": self.system_prompt + memory_context + tools_section},
            {"role": "user", "content": input_data},
        ]

        if context:
            messages.append({"role": "user", "content": f"Context: {context}"})

        ollama = self._get_ollama()
        response = await ollama.chat(model=self.model, messages=messages, temperature=0.3)

        thought = response.get("message", {}).get("content", "") if isinstance(response, dict) else ""
        self._history.append(AgentStep(thought=thought))
        return thought

    async def act(self, thought: str) -> str:
        self.state = AgentState.ACTING

        tool_calls = self._parse_tool_calls(thought)
        results = []
        for tc in tool_calls:
            result = await self.tool_call(tc.name, **tc.arguments)
            tc.result = result
            results.append(f"{tc.name}: {result}")

        action = "\n".join(results) if results else "No tool calls needed"
        if self._history:
            self._history[-1].action = action
            self._history[-1].tool_calls = tool_calls
        return action

    async def observe(self, action: str, input_data: str) -> str:
        self.state = AgentState.OBSERVING

        observation = f"Action completed: {action}"
        self.memory.add({"type": "observation", "content": observation, "input": input_data})

        if self._history:
            self._history[-1].observation = observation
        return observation

    def _get_tool_descriptions(self) -> str:
        if not self._tools:
            return ""
        lines = []
        for name, func in self._tools.items():
            doc = func.__doc__ or "No description"
            lines.append(f"- {name}: {doc.strip()}")
        return "\n".join(lines)

    def _parse_tool_calls(self, text: str) -> list[ToolCall]:
        import re

        calls = []
        pattern = r"tool_call:\s*(\w+)\((.*?)\)"
        for match in re.finditer(pattern, text, re.DOTALL):
            name = match.group(1)
            args_str = match.group(2).strip()
            args = {}
            if args_str:
                for pair in args_str.split(","):
                    if "=" in pair:
                        key, val = pair.split("=", 1)
                        args[key.strip()] = val.strip().strip("\"'")
            if name in self._tools:
                calls.append(ToolCall(name=name, arguments=args))
        return calls

    async def tool_call(self, tool_name: str, **kwargs: Any) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        try:
            result = await self._tools[tool_name](**kwargs)
            self.memory.add({"type": "tool_call", "tool": tool_name, "args": kwargs, "result": str(result)})
            return result
        except Exception as exc:
            logger.error("Tool call %s failed: %s", tool_name, exc)
            return f"Error: {exc}"

    def get_memory(self, query: str | None = None) -> list[dict[str, Any]]:
        if query:
            return self.memory.search(query)
        return self.memory.entries

    def add_to_memory(self, entry: dict[str, Any]) -> None:
        self.memory.add(entry)

    async def run(self, input_data: str, context: dict[str, Any] | None = None) -> str:
        self.state = AgentState.IDLE
        self._history.clear()

        try:
            for iteration in range(self.max_iterations):
                thought = await self.think(input_data, context)

                if "FINAL ANSWER:" in thought or "DONE" in thought.upper():
                    self.state = AgentState.DONE
                    self.memory.add({"type": "run_complete", "input": input_data, "result": thought})
                    return thought

                action = await self.act(thought)
                observation = await self.observe(action, input_data)

                if "task_complete" in observation.lower() or "no further" in observation.lower():
                    self.state = AgentState.DONE
                    return thought

            self.state = AgentState.DONE
            final = self._history[-1].thought if self._history else "Max iterations reached"
            self.memory.add({"type": "run_complete", "input": input_data, "result": final})
            return final

        except Exception as exc:
            self.state = AgentState.ERROR
            logger.error("Agent %s run failed: %s", self.name, exc)
            raise
