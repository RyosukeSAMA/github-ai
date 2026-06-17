"""Base classes for roles, tasks, and plans."""

from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Task:
    """A unit of work submitted to the Pantheon."""

    content: str
    mode: str = "auto"  # "auto" | "role:<name>" | "multi"
    context: List[Dict[str, Any]] = field(default_factory=list)
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def __post_init__(self) -> None:
        if self.mode not in ("auto", "multi") and not self.mode.startswith("role:"):
            raise ValueError(
                f"Invalid mode: {self.mode}. "
                "Must be 'auto', 'multi', or 'role:<name>'"
            )


@dataclass
class TaskResult:
    """Result of a single task execution by one role."""

    role: str
    content: str
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class PlanStep:
    """A single step in a multi-role plan."""

    role: str
    task: str
    description: str = ""


@dataclass
class Plan:
    """A multi-step plan produced by the Router for Hermes."""

    is_single_role: bool = False
    single_role: Optional[str] = None
    steps: List[PlanStep] = field(default_factory=list)
    reasoning: str = ""

    @classmethod
    def single(cls, role: str, reasoning: str = "") -> "Plan":
        return cls(is_single_role=True, single_role=role, reasoning=reasoning)

    @classmethod
    def multi(cls, steps: List[PlanStep], reasoning: str = "") -> "Plan":
        return cls(is_single_role=False, steps=steps, reasoning=reasoning)


class Role(abc.ABC):
    """Abstract base class for all Pantheon roles (gods).

    To add a new role, subclass this and implement:
      - name, description (class attributes)
      - system_prompt (string)
      - run(task: Task, context: list) -> TaskResult

    Optionally override config defaults.
    """

    name: str = ""
    description: str = ""
    default_model: str = ""
    default_provider: str = ""
    default_temperature: float = 0.3
    tools: List[str] = []

    def __init__(
        self,
        llm_client: Any,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.name:
            raise ValueError(f"{type(self).__name__} must define `name`")
        self.llm_client = llm_client
        self.model = model or self.default_model
        self.temperature = (
            temperature if temperature is not None else self.default_temperature
        )
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.config = config or {}

    def _default_system_prompt(self) -> str:
        return (
            f"You are {self.name}, {self.description}.\n"
            "Answer concisely and accurately. Use the tools available when needed."
        )

    @abc.abstractmethod
    def run(self, task: Task, context: Optional[List[Dict[str, Any]]] = None) -> TaskResult:
        """Execute a task and return a TaskResult."""
        raise NotImplementedError

    def _make_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """Helper: make a synchronous LLM call."""
        if self.llm_client is None:
            raise RuntimeError(
                f"Role {self.name} has no LLM client configured. "
                "Set the role's `model` and `provider` in pantheon.yaml."
            )
        return self.llm_client.complete(
            messages=messages,
            model=self.model,
            system=self.system_prompt,
            temperature=self.temperature,
        )

    def _format_context(self, context: Optional[List[Dict[str, Any]]]) -> str:
        """Format prior steps' context as a string."""
        if not context:
            return ""
        lines = ["Prior steps in this multi-role task:"]
        for i, step in enumerate(context, 1):
            lines.append(
                f"\n[Step {i} — {step.get('role', '?')}]\n"
                f"Task: {step.get('step', '?')}\n"
                f"Result: {step.get('result', '?')}"
            )
        return "\n".join(lines)


def time_ms() -> int:
    """Current time in milliseconds."""
    return int(time.time() * 1000)
