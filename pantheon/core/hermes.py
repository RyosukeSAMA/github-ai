"""Hermes: the chief orchestrator. Routes tasks to other gods."""

from __future__ import annotations

import inspect
import json
import time
import uuid
from collections.abc import Callable
from typing import Any

from pantheon.core.base import AgentMessage, Plan, PlanStep, Task, TaskResult
from pantheon.core.router import Router


class Hermes:
    """The orchestrator.

    Hermes receives every user task. He uses an LLM (via Router) to decide:
      - Whether to dispatch to a single role
      - Or to decompose into multiple steps executed by different roles
    Then he collects results and produces the final answer.
    """

    def __init__(self, roles: dict[str, Any], router: Router) -> None:
        self.roles = roles  # name -> Role instance
        self.router = router
        self.memory_context_provider: Any = None
        self.skill_context_provider: Any = None
        self.skill_catalog_provider: Any = None
        self.skill_lookup_provider: Any = None
        self.plugin_context_provider: Any = None
        self.mcp_context_provider: Any = None
        self.mcp_tool_executor: Any = None

    def dispatch(
        self,
        task: Task,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        """Dispatch a task according to its mode.

        Returns a dict:
          {
            "mode": "single" | "multi",
            "plan": Plan summary,
            "content": final user-facing content,
            "steps": [TaskResult, ...],  # multi only
            "communications": [AgentMessage, ...]
          }
        """
        requested_skill = self._requested_skill(task.skill)
        if task.skill and requested_skill is None:
            return self._skill_error(task.skill, "is not installed or is disabled")

        if task.mode.startswith("role:"):
            role_name = task.mode.split(":", 1)[1]
            if requested_skill and not self._skill_applies_to_role(requested_skill, role_name):
                return self._skill_error(
                    task.skill or "",
                    f"cannot be used by {role_name}",
                )
            return self._run_single(
                role_name,
                task,
                plan_reasoning=f"User specified role: {role_name}",
                plan_skill=task.skill,
                on_event=on_event,
            )

        if task.mode == "auto" and requested_skill:
            target_roles = [
                role for role in requested_skill.get("roles") or []
                if role not in {"global", "hermes"} and role in self.roles
            ]
            if len(target_roles) == 1:
                return self._run_single(
                    target_roles[0],
                    task,
                    plan_reasoning=(
                        f"Explicit skill ${requested_skill.get('id')} is assigned to "
                        f"{target_roles[0]}."
                    ),
                    plan_skill=str(requested_skill.get("id") or ""),
                    on_event=on_event,
                )

        if task.mode == "multi":
            self._emit(
                on_event,
                "plan_start",
                {
                    "role": "hermes",
                    "task": task.content,
                    "description": "Analyzing the task and building a multi-role plan",
                    "mode": task.mode,
                },
            )
            available = self._role_descriptions()
            planning_task, planning_memories, planning_skills = self._task_with_memory(
                task,
                "hermes",
            )
            plan = self.router.plan(
                planning_task.content,
                available,
                requested_skill=task.skill or "",
            )
            if plan.is_single_role:
                plan = self._force_multi_plan(planning_task, plan)
                if plan.is_single_role:
                    result = self._run_single(
                        plan.single_role,
                        task,
                        plan_reasoning=plan.reasoning,
                        plan_skill=plan.single_skill,
                        on_event=on_event,
                    )
                    result["memory_matches"] = self._merge_memory_matches(
                        planning_memories,
                        result.get("memory_matches", []),
                    )
                    result["skill_matches"] = self._merge_skill_matches(
                        planning_skills,
                        result.get("skill_matches", []),
                    )
                    return result
            result = self._run_multi(task, plan=plan, on_event=on_event)
            result["memory_matches"] = self._merge_memory_matches(
                planning_memories,
                result.get("memory_matches", []),
            )
            result["skill_matches"] = self._merge_skill_matches(
                planning_skills,
                result.get("skill_matches", []),
            )
            return result

        # mode == "auto": let Hermes decide
        self._emit(
            on_event,
            "plan_start",
            {
                "role": "hermes",
                "task": task.content,
                "description": "Analyzing the task and choosing the best route",
                "mode": task.mode,
            },
        )
        available = self._role_descriptions()
        planning_task, planning_memories, planning_skills = self._task_with_memory(
            task,
            "hermes",
        )
        plan = self.router.plan(
            planning_task.content,
            available,
            requested_skill=task.skill or "",
        )
        if plan.is_single_role:
            result = self._run_single(
                plan.single_role,
                task,
                plan_reasoning=plan.reasoning,
                plan_skill=plan.single_skill,
                on_event=on_event,
            )
            result["memory_matches"] = self._merge_memory_matches(
                planning_memories,
                result.get("memory_matches", []),
            )
            result["skill_matches"] = self._merge_skill_matches(
                planning_skills,
                result.get("skill_matches", []),
            )
            return result
        result = self._run_multi(task, plan=plan, on_event=on_event)
        result["memory_matches"] = self._merge_memory_matches(
            planning_memories,
            result.get("memory_matches", []),
        )
        result["skill_matches"] = self._merge_skill_matches(
            planning_skills,
            result.get("skill_matches", []),
        )
        return result

    # ----- internal -----

    def _run_single(
        self,
        role_name: str,
        task: Task,
        plan_reasoning: str = "",
        plan_skill: str | None = None,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        role = self.roles.get(role_name)
        if role is None:
            return {
                "mode": "single",
                "plan": plan_reasoning,
                "content": f"Error: role '{role_name}' is not registered.",
                "steps": [],
                "skill_matches": [],
            }

        selected_skill = task.skill or plan_skill
        execution_task = Task(
            content=task.content,
            mode=task.mode,
            skill=selected_skill,
            context=list(task.context),
            task_id=task.task_id,
        )
        role_task, memories, skills = self._task_with_memory(execution_task, role_name)
        step_payload = {
            "index": 0,
            "total": 1,
            "role": role_name,
            "task": task.content,
            "description": plan_reasoning or "Direct role execution",
            "skills": skills,
        }
        self._emit(
            on_event,
            "plan_ready",
            {
                "plan": plan_reasoning,
                "mode": "single",
                "steps": [step_payload],
            },
        )
        self._emit(on_event, "step_start", step_payload)
        result = self._run_role(
            role,
            role_task,
            role_name=role_name,
            on_event=on_event,
        )
        if memories:
            result.metadata["memory_matches"] = memories
        if skills:
            result.metadata["skill_matches"] = skills
        result_payload = {
            **step_payload,
            "content": result.content,
            "duration_ms": result.duration_ms,
            "success": result.success,
            "error": result.error,
        }
        self._emit(
            on_event,
            "step_done" if result.success else "step_error",
            result_payload,
        )
        return {
            "mode": "single",
            "plan": plan_reasoning,
            "content": result.content,
            "steps": [result],
            "memory_matches": memories,
            "skill_matches": skills,
        }

    def _run_multi(
        self,
        task: Task,
        plan: Plan,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        steps_output: list[TaskResult] = []
        context: list[dict[str, Any]] = []
        communications: list[dict[str, Any]] = []
        total_steps = len(plan.steps)
        self._emit(
            on_event,
            "plan_ready",
            {
                "plan": plan.reasoning,
                "mode": "multi",
                "steps": [
                    {
                        "index": index,
                        "total": total_steps,
                        "role": step.role,
                        "task": step.task,
                        "description": step.description,
                        "skills": [{"id": step.skill}] if step.skill else [],
                        "kind": step.kind,
                        "depends_on": list(step.depends_on),
                        "deliverable": step.deliverable,
                        "acceptance_criteria": list(step.acceptance_criteria),
                    }
                    for index, step in enumerate(plan.steps)
                ],
            },
        )

        for i, step in enumerate(plan.steps, 1):
            role = self.roles.get(step.role)
            if role is None:
                step_payload = {
                    "index": i - 1,
                    "total": total_steps,
                    "role": step.role,
                    "task": step.task,
                    "description": step.description,
                    "skills": [],
                }
                self._emit(on_event, "step_start", step_payload)
                result = TaskResult(
                    role=step.role,
                    content=f"[Step {i}] Skipped: role '{step.role}' not found.",
                    success=False,
                    error="role_not_found",
                )
                steps_output.append(result)
                self._emit(
                    on_event,
                    "step_error",
                    {
                        **step_payload,
                        "content": result.content,
                        "duration_ms": 0,
                        "success": False,
                        "error": result.error,
                    },
                )
                continue

            incoming_messages = self._incoming_agent_messages(
                step_index=i,
                step=step,
                plan=plan,
                steps_output=steps_output,
            )
            for message in incoming_messages:
                payload = message.to_dict()
                communications.append(payload)
                self._emit(on_event, "agent_message", payload)

            # Keep the concise plan step, but always give the role the complete
            # request. Planner steps are labels, not enough context to execute.
            sub_task = Task(
                content=self._multi_step_content(
                    original_task=task.content,
                    assigned_task=step.task,
                    step_index=i,
                    total_steps=total_steps,
                    step_kind=step.kind,
                    deliverable=step.deliverable,
                    acceptance_criteria=step.acceptance_criteria,
                    incoming_messages=[item.to_dict() for item in incoming_messages],
                ),
                mode="role:" + step.role,
                skill=step.skill or task.skill,
                context=list(context),
            )
            role_task, memories, skills = self._task_with_memory(sub_task, step.role)
            step_payload = {
                "index": i - 1,
                "total": total_steps,
                "role": step.role,
                "task": step.task,
                "description": step.description,
                "skills": skills,
                "kind": step.kind,
                "depends_on": list(step.depends_on),
                "deliverable": step.deliverable,
                "acceptance_criteria": list(step.acceptance_criteria),
            }
            self._emit(on_event, "step_start", step_payload)
            result = self._run_role(
                role,
                role_task,
                context=context,
                role_name=step.role,
                on_event=on_event,
            )
            result.metadata["step_index"] = i
            result.metadata["task"] = step.task
            result.metadata["description"] = step.description
            result.metadata["kind"] = step.kind
            result.metadata["depends_on"] = list(step.depends_on)
            result.metadata["deliverable"] = step.deliverable
            result.metadata["acceptance_criteria"] = list(step.acceptance_criteria)
            if memories:
                result.metadata["memory_matches"] = memories
            if skills:
                result.metadata["skill_matches"] = skills
            if incoming_messages:
                result.metadata["incoming_messages"] = [
                    item.to_dict() for item in incoming_messages
                ]
            steps_output.append(result)
            self._emit(
                on_event,
                "step_done" if result.success else "step_error",
                {
                    **step_payload,
                    "content": result.content,
                    "duration_ms": result.duration_ms,
                    "success": result.success,
                    "error": result.error,
                },
            )

            context.append(
                {
                    "step": step.task,
                    "role": step.role,
                    "result": result.content,
                    "skills": [item.get("id") for item in skills],
                    "kind": step.kind,
                    "deliverable": step.deliverable,
                    "acceptance_criteria": list(step.acceptance_criteria),
                    "incoming_messages": [
                        item.to_dict() for item in incoming_messages
                    ],
                }
            )

            if result.success:
                acknowledgement = self._completion_message(
                    step_index=i,
                    step=step,
                    result=result,
                    incoming_messages=incoming_messages,
                )
                payload = acknowledgement.to_dict()
                communications.append(payload)
                self._emit(on_event, "agent_message", payload)

        # Summarize via Hermes
        self._emit(
            on_event,
            "summary_start",
            {
                "role": "hermes",
                "task": "Synthesize the completed agent results",
                "description": "Preparing the final answer",
                "total": total_steps,
            },
        )
        summary = self.router.summarize(task.content, context)
        self._emit(
            on_event,
            "summary_done",
            {
                "role": "hermes",
                "content": summary,
                "success": True,
            },
        )

        return {
            "mode": "multi",
            "plan": plan.reasoning,
            "content": summary,
            "steps": steps_output,
            "communications": communications,
            "memory_matches": self._merge_memory_matches(*[
                getattr(step, "metadata", {}).get("memory_matches", [])
                for step in steps_output
            ]),
            "skill_matches": self._merge_skill_matches(*[
                getattr(step, "metadata", {}).get("skill_matches", [])
                for step in steps_output
            ]),
        }

    @staticmethod
    def _multi_step_content(
        *,
        original_task: str,
        assigned_task: str,
        step_index: int,
        total_steps: int,
        step_kind: str = "work",
        deliverable: str = "",
        acceptance_criteria: list[str] | None = None,
        incoming_messages: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build an executable step without losing the user's original scope."""
        messages = incoming_messages or []
        handoff_lines = []
        for message in messages:
            source = message.get("from_role") or "hermes"
            message_type = message.get("type") or "handoff"
            summary = message.get("summary") or "Prior result is available in context."
            handoff_lines.append(f"- {message_type} from {source}: {summary}")
        handoff_block = "\n".join(handoff_lines) or "- Initial assignment from Hermes."
        criteria = acceptance_criteria or []
        criteria_block = "\n".join(f"- {item}" for item in criteria) or "- Complete the assigned step with a usable result."
        expected_deliverable = deliverable or "A concrete result that the next role can use."
        return f"""You are executing step {step_index}/{total_steps} of an active Pantheon multi-role workflow.

Original user request:
{original_task}

Your assigned step:
{assigned_task}

Structured collaboration:
- Step kind: {step_kind}
- Expected deliverable: {expected_deliverable}
- Incoming messages:
{handoff_block}
- Acceptance criteria:
{criteria_block}

Workflow rules:
- Complete the assigned step now using the original request and prior-step context.
- Do not ask the user to repeat a scope, feature, or constraint already present above.
- Do not end with a vague follow-up question or ask the user to start a new task.
- For a minor, reversible ambiguity, state a reasonable assumption and continue so the workflow does not pause.
- When user confirmation is genuinely required, do not ask a vague or open-ended question. Provide 2-4 concrete numbered options in the user's language. Give every option its own practical suggestion:
  1. <choice> - Suggestion: <when or why to choose it>
  2. <choice> - Suggestion: <when or why to choose it>
  3. <optional choice> - Suggestion: <when or why to choose it>
  Recommended: <option number> - <brief reason>
- Confirmation is required for decisions involving cost, external writes, security, irreversible actions, or a major change of scope. Do not perform the dependent action or claim the user approved it; prepare the options for Hermes to surface in the final answer.
- Return a useful intermediate deliverable for the next role."""

    @staticmethod
    def _incoming_agent_messages(
        *,
        step_index: int,
        step: PlanStep,
        plan: Plan,
        steps_output: list[TaskResult],
    ) -> list[AgentMessage]:
        if step_index <= 1:
            return []
        dependencies = list(step.depends_on)
        message_type = {
            "question": "question",
            "review": "review_request",
            "revision": "revision_request",
        }.get(step.kind, "handoff")
        messages: list[AgentMessage] = []
        for dependency in dependencies:
            source_index = dependency - 1
            if source_index < 0 or source_index >= len(steps_output):
                continue
            source_step = plan.steps[source_index]
            source_result = steps_output[source_index]
            if message_type in {"question", "revision_request"}:
                summary = step.task or step.description or "A response is required."
            else:
                summary = (
                    source_step.deliverable
                    or source_step.description
                    or source_step.task
                    or source_result.content
                    or "Prior step completed."
                )
            messages.append(AgentMessage(
                message_type=message_type,
                from_role=source_step.role,
                to_role=step.role,
                summary=str(summary)[:600],
                step_index=step_index,
                target_step_index=dependency,
                deliverable=step.deliverable,
                acceptance_criteria=list(step.acceptance_criteria),
                metadata={
                    "source_success": source_result.success,
                    "source_task": source_step.task,
                },
            ))
        return messages

    @staticmethod
    def _completion_message(
        *,
        step_index: int,
        step: PlanStep,
        result: TaskResult,
        incoming_messages: list[AgentMessage],
    ) -> AgentMessage:
        recipient = incoming_messages[-1].from_role if incoming_messages else "hermes"
        summary = result.content or step.deliverable or step.task or "Step completed."
        return AgentMessage(
            message_type="result",
            from_role=step.role,
            to_role=recipient,
            summary=str(summary)[:600],
            step_index=step_index,
            target_step_index=step_index,
            deliverable=step.deliverable,
            acceptance_criteria=list(step.acceptance_criteria),
            metadata={"duration_ms": result.duration_ms, "success": result.success},
        )

    def _role_descriptions(self) -> dict[str, dict[str, Any]]:
        descriptions = {
            name: {"description": getattr(role, "description", "")}
            for name, role in self.roles.items()
        }
        if callable(self.skill_catalog_provider):
            catalog = self.skill_catalog_provider() or {}
            for name, info in descriptions.items():
                info["skills"] = list(catalog.get(name) or [])
        return descriptions

    def _force_multi_plan(self, task: Task, single_plan: Plan) -> Plan:
        runnable_roles = [name for name in self.roles if name != "chronos"]
        if len(runnable_roles) < 2:
            return single_plan

        preferred = [
            name for name in ("athena", "hephaestus", "apollo")
            if name in runnable_roles
        ]
        for name in runnable_roles:
            if name not in preferred:
                preferred.append(name)

        primary = (
            single_plan.single_role
            if single_plan.single_role in runnable_roles
            else preferred[0]
        )

        ordered: list[str] = []
        if "athena" in preferred and primary != "athena":
            ordered.append("athena")
        ordered.append(primary)
        for name in preferred:
            if name not in ordered:
                ordered.append(name)
            if len(ordered) >= 3:
                break

        if len(ordered) < 2:
            return single_plan

        steps: list[PlanStep] = []
        for index, role in enumerate(ordered):
            if index == 0 and role == "athena" and primary != "athena":
                steps.append(PlanStep(
                    role=role,
                    task=f"Analyze the task and gather the key constraints: {task.content}",
                    description="research and framing",
                    skill=task.skill or "",
                    kind="work",
                    deliverable="A concise brief of constraints, risks, and recommended direction.",
                    acceptance_criteria=[
                        "Covers the complete user request.",
                        "Separates evidence, assumptions, and open decisions.",
                    ],
                ))
            elif role == primary:
                steps.append(PlanStep(
                    role=role,
                    task=f"Produce the core answer for: {task.content}",
                    description="core execution",
                    skill=task.skill or "",
                    kind="work",
                    depends_on=[index] if index else [],
                    deliverable="The primary implementation or answer requested by the user.",
                    acceptance_criteria=[
                        "Uses prior role findings where relevant.",
                        "Produces a concrete, usable result.",
                    ],
                ))
            else:
                steps.append(PlanStep(
                    role=role,
                    task="Review prior results and refine the final direction.",
                    description="review and refinement",
                    kind="review",
                    depends_on=[index] if index else [],
                    deliverable="A focused review with corrections or an explicit pass decision.",
                    acceptance_criteria=[
                        "Checks the result against the original request.",
                        "Names concrete defects before proposing corrections.",
                    ],
                ))

        reasoning = single_plan.reasoning or "User selected Multi-role."
        return Plan.multi(
            steps=steps,
            reasoning=f"{reasoning} Multi-role mode forced a council workflow.",
        )

    def _task_with_memory(
        self,
        task: Task,
        role_name: str,
    ) -> tuple[Task, list[dict[str, Any]], list[dict[str, Any]]]:
        blocks: list[str] = []
        memories: list[dict[str, Any]] = []
        skills: list[dict[str, Any]] = []
        providers = (
            (self.memory_context_provider, "memory"),
            (self.skill_context_provider, "skill"),
            (self.plugin_context_provider, "plugin"),
            (self.mcp_context_provider, "mcp"),
        )
        for provider, provider_kind in providers:
            if not callable(provider):
                continue
            if provider_kind == "skill":
                result = provider(task.content, role_name, task.skill or "")
            else:
                result = provider(task.content, role_name)
            context = result[0] if isinstance(result, tuple) else result
            details = result[1] if isinstance(result, tuple) and len(result) > 1 else []
            if context:
                blocks.append(str(context))
            if provider_kind == "memory" and details:
                memories = list(details)
            if provider_kind == "skill" and details:
                skills = list(details)
        if not blocks:
            return task, memories, skills
        return (
            Task(
                content=f"{task.content}\n\n---\n" + "\n\n---\n".join(blocks),
                mode=task.mode,
                skill=task.skill,
                context=list(task.context),
                task_id=task.task_id,
            ),
            memories,
            skills,
        )

    def _run_role(
        self,
        role: Any,
        task: Task,
        context: list[dict[str, Any]] | None = None,
        role_name: str = "",
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> TaskResult:
        """Run a role and handle the explicit MCP tool-call envelope."""
        result = role.run(task, context=context)
        executor = self.mcp_tool_executor
        if not callable(executor):
            return result
        calls: list[dict[str, Any]] = []
        for _ in range(3):
            call = self._extract_tool_call(result.content)
            if not call:
                break
            call["call_id"] = uuid.uuid4().hex[:12]
            call["role"] = role_name or result.role
            calls.append(call)
            started = time.monotonic()
            event_payload = {
                "call_id": call["call_id"],
                "role": call["role"],
                "server_id": call.get("server_id", ""),
                "tool": call.get("tool", ""),
                "arguments": call.get("arguments", {}),
            }
            self._emit(on_event, "mcp_call_start", event_payload)
            try:
                tool_result = self._invoke_mcp_executor(
                    executor,
                    call,
                    role_name=call["role"],
                    on_event=on_event,
                )
            except Exception as exc:
                tool_result = {"error": str(exc)}
                self._emit(
                    on_event,
                    "mcp_call_error",
                    {
                        **event_payload,
                        "error": str(exc),
                        "duration_ms": int((time.monotonic() - started) * 1000),
                    },
                )
            else:
                is_error = bool(
                    isinstance(tool_result, dict)
                    and tool_result.get("is_error")
                )
                event = "mcp_call_error" if is_error else "mcp_call_done"
                payload = {
                    **event_payload,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "result_preview": self._mcp_result_preview(tool_result),
                    "truncated": bool(
                        isinstance(tool_result, dict)
                        and tool_result.get("truncated")
                    ),
                }
                if is_error:
                    payload["error"] = payload["result_preview"] or "MCP tool returned an error"
                self._emit(on_event, event, payload)
            continuation = Task(
                content=(
                    f"{task.content}\n\n---\nMCP tool result for {call.get('tool', '')}:\n"
                    f"{json.dumps(tool_result, ensure_ascii=False)}\n\n"
                    "Use this result to complete the user's task. Do not output another tool call "
                    "unless another listed MCP tool is genuinely needed."
                ),
                mode=task.mode,
                skill=task.skill,
                context=list(task.context),
                task_id=task.task_id,
            )
            result = role.run(continuation, context=context)
        if calls:
            result.metadata["mcp_calls"] = calls
        return result

    @staticmethod
    def _invoke_mcp_executor(
        executor: Callable[..., Any],
        call: dict[str, Any],
        *,
        role_name: str,
        on_event: Callable[[str, dict[str, Any]], None] | None,
    ) -> Any:
        """Call newer context-aware executors while preserving the old one-arg hook."""
        try:
            parameters = inspect.signature(executor).parameters.values()
        except (TypeError, ValueError):
            return executor(call)
        accepts_context = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            or parameter.name in {"role_name", "on_event"}
            for parameter in parameters
        )
        if accepts_context:
            return executor(call, role_name=role_name, on_event=on_event)
        return executor(call)

    @staticmethod
    def _mcp_result_preview(result: Any) -> str:
        if isinstance(result, dict):
            text = str(result.get("text") or result.get("error") or "").strip()
            if text:
                return text[:600]
            structured = result.get("structured")
            if structured is not None:
                return json.dumps(structured, ensure_ascii=False)[:600]
        return str(result or "")[:600]

    @staticmethod
    def _extract_tool_call(content: str) -> dict[str, Any] | None:
        import re

        match = re.search(r"<tool_call>\s*(.*?)\s*</tool_call>", content or "", re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(1))
        except (TypeError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        if not payload.get("server_id") or not payload.get("tool"):
            return None
        arguments = payload.get("arguments")
        payload["arguments"] = arguments if isinstance(arguments, dict) else {}
        return payload

    @staticmethod
    def _emit(
        callback: Callable[[str, dict[str, Any]], None] | None,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Send an optional progress event without affecting task execution."""
        if not callable(callback):
            return
        try:
            callback(event, data)
        except Exception:
            return

    @staticmethod
    def _merge_memory_matches(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        for group in groups:
            for item in group or []:
                item_id = str(item.get("id") or "")
                if item_id and item_id in seen:
                    continue
                if item_id:
                    seen.add(item_id)
                merged.append(item)
        return merged

    @staticmethod
    def _merge_skill_matches(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for group in groups:
            for item in group or []:
                key = (
                    str(item.get("id") or ""),
                    str(item.get("invocation") or ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged

    def _requested_skill(self, skill_id: str | None) -> dict[str, Any] | None:
        if not skill_id or not callable(self.skill_lookup_provider):
            return None
        item = self.skill_lookup_provider(skill_id)
        if not item or not item.get("enabled", True):
            return None
        return item

    @staticmethod
    def _skill_applies_to_role(item: dict[str, Any], role_name: str) -> bool:
        roles = item.get("roles") or []
        return "global" in roles or role_name in roles

    @staticmethod
    def _skill_error(skill_id: str, reason: str) -> dict[str, Any]:
        return {
            "mode": "single",
            "plan": "Explicit skill validation failed.",
            "content": f"Skill '${str(skill_id).lstrip('$')}' {reason}.",
            "steps": [],
            "memory_matches": [],
            "skill_matches": [],
        }
