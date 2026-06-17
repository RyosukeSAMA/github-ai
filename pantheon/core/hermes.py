"""Hermes: the chief orchestrator. Routes tasks to other gods."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pantheon.core.base import Plan, PlanStep, Task, TaskResult, time_ms
from pantheon.core.router import Router


class Hermes:
    """The orchestrator.

    Hermes receives every user task. He uses an LLM (via Router) to decide:
      - Whether to dispatch to a single role
      - Or to decompose into multiple steps executed by different roles
    Then he collects results and produces the final answer.
    """

    def __init__(self, roles: Dict[str, Any], router: Router) -> None:
        self.roles = roles  # name -> Role instance
        self.router = router

    def dispatch(self, task: Task) -> Dict[str, Any]:
        """Dispatch a task according to its mode.

        Returns a dict:
          {
            "mode": "single" | "multi",
            "plan": Plan summary,
            "content": final user-facing content,
            "steps": [TaskResult, ...]   # multi only
          }
        """
        if task.mode.startswith("role:"):
            role_name = task.mode.split(":", 1)[1]
            return self._run_single(role_name, task, plan_reasoning=f"User specified role: {role_name}")

        if task.mode == "multi":
            available = self._role_descriptions()
            plan = self.router.plan(task.content, available)
            if plan.is_single_role:
                return self._run_single(
                    plan.single_role, task, plan_reasoning=plan.reasoning
                )
            return self._run_multi(task, plan=plan)

        # mode == "auto": let Hermes decide
        available = self._role_descriptions()
        plan = self.router.plan(task.content, available)
        if plan.is_single_role:
            return self._run_single(
                plan.single_role, task, plan_reasoning=plan.reasoning
            )
        return self._run_multi(task, plan=plan)

    # ----- internal -----

    def _run_single(
        self,
        role_name: str,
        task: Task,
        plan_reasoning: str = "",
    ) -> Dict[str, Any]:
        role = self.roles.get(role_name)
        if role is None:
            return {
                "mode": "single",
                "plan": plan_reasoning,
                "content": f"Error: role '{role_name}' is not registered.",
                "steps": [],
            }

        result = role.run(task)
        return {
            "mode": "single",
            "plan": plan_reasoning,
            "content": result.content,
            "steps": [result],
        }

    def _run_multi(
        self,
        task: Task,
        plan: Plan,
    ) -> Dict[str, Any]:
        steps_output: List[TaskResult] = []
        context: List[Dict[str, Any]] = []

        for i, step in enumerate(plan.steps, 1):
            role = self.roles.get(step.role)
            if role is None:
                steps_output.append(
                    TaskResult(
                        role=step.role,
                        content=f"[Step {i}] Skipped: role '{step.role}' not found.",
                        success=False,
                        error="role_not_found",
                    )
                )
                continue

            # Build a sub-task for this role, including prior context
            sub_task = Task(
                content=step.task,
                mode="role:" + step.role,
                context=list(context),
            )
            result = role.run(sub_task, context=context)
            result.metadata["step_index"] = i
            result.metadata["description"] = step.description
            steps_output.append(result)

            context.append(
                {
                    "step": step.task,
                    "role": step.role,
                    "result": result.content,
                }
            )

        # Summarize via Hermes
        summary = self.router.summarize(task.content, context)

        return {
            "mode": "multi",
            "plan": plan.reasoning,
            "content": summary,
            "steps": steps_output,
        }

    def _role_descriptions(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {"description": getattr(role, "description", "")}
            for name, role in self.roles.items()
        }
