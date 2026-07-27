"""Router: lets Hermes (the orchestrator LLM) decide how to handle tasks."""

from __future__ import annotations

import json
import re
from typing import Any

from pantheon.core.base import Plan, PlanStep


class Router:
    """Uses an LLM to plan task routing (single role vs. multi-role decomposition)."""

    PLANNER_SYSTEM = """You are Hermes, the messenger god and chief orchestrator of the Pantheon.

Your job: given a user task and a list of available gods (with their specialties),
decide the optimal execution plan.

Output ONLY valid JSON in one of two shapes:

1) Single-role plan:
{
  "type": "single",
  "role": "<role_name>",
  "skill": "<optional_skill_id>",
  "reasoning": "Why this role can handle it alone"
}

2) Multi-role plan:
{
  "type": "multi",
  "reasoning": "Why multiple roles are needed",
  "steps": [
    {
      "role": "<role_name>",
      "skill": "<optional_skill_id>",
      "task": "<specific task for this role>",
      "description": "<short note>"
    },
    ...
  ]
}

Rules:
- Order steps so each step can use prior steps' results.
- The last step's result should be the user-facing answer.
- Be concise in `task` strings; do not repeat the user's full prompt.
- Do not invent roles. Use only names from the provided list.
- Use only skill ids listed for the selected role. Omit `skill` when no listed skill fits.
- When a requested skill is supplied, route it to a compatible role and preserve its id.
- Output JSON only. No prose before or after."""

    def __init__(self, llm_client: Any, hermes_model: str | None = None) -> None:
        self.llm_client = llm_client
        self.hermes_model = hermes_model

    def plan(
        self,
        task: str,
        available_roles: dict[str, dict[str, Any]],
        requested_skill: str = "",
    ) -> Plan:
        """Decide how to route a task.

        Args:
            task: The user's task string.
            available_roles: Dict of role_name -> {description, ...}

        Returns:
            A Plan object.
        """
        role_lines: list[str] = []
        for name, info in available_roles.items():
            skills = info.get("skills") or []
            skill_text = ", ".join(
                f"${skill.get('id')} ({skill.get('description') or skill.get('name')})"
                for skill in skills
                if skill.get("id")
            )
            suffix = f"\n  Skills: {skill_text}" if skill_text else ""
            role_lines.append(
                f"- {name}: {info.get('description', '(no description)')}{suffix}"
            )
        role_descriptions = "\n".join(role_lines)

        user_prompt = f"""Available gods:
{role_descriptions}

User task: {task}
Requested skill: {f"${requested_skill}" if requested_skill else "(none)"}

Produce a JSON plan."""

        raw = self.llm_client.complete(
            messages=[{"role": "user", "content": user_prompt}],
            model=self.hermes_model or self.llm_client.default_model,
            system=self.PLANNER_SYSTEM,
            temperature=0.1,
        )

        return self._parse_plan(raw, available_roles, requested_skill=requested_skill)

    def summarize(
        self,
        original_task: str,
        context: list[dict[str, Any]],
    ) -> str:
        """Summarize a multi-step result into a final user-facing answer."""
        if not context:
            return ""

        steps_text = "\n\n".join(
            f"[{step.get('role', '?')}] {step.get('step', '?')}\n"
            f"Result: {step.get('result', '?')}"
            for step in context
        )

        prompt = f"""Original user task: {original_task}

The following steps were executed by different gods to fulfill this task:

{steps_text}

Please synthesize these results into a single coherent, user-facing answer.
Be concise, structured, and complete. Address the original task directly."""

        return self.llm_client.complete(
            messages=[{"role": "user", "content": prompt}],
            model=self.hermes_model or self.llm_client.default_model,
            system="You are Hermes, the chief orchestrator. Synthesize results clearly.",
            temperature=0.3,
        )

    # ----- internal -----

    def _parse_plan(
        self,
        raw: str,
        available_roles: dict[str, dict[str, Any]],
        requested_skill: str = "",
    ) -> Plan:
        """Parse the LLM's JSON output into a Plan object, with fallbacks."""
        data = self._extract_json(raw)

        if data is None:
            # Fallback: pick the first available role
            fallback_role = next(iter(available_roles.keys()), None)
            return Plan.single(
                role=fallback_role,
                reasoning=f"Router failed to parse plan; falling back to {fallback_role}. Raw: {raw[:200]}",
            )

        if data.get("type") == "single":
            role = data.get("role")
            if role not in available_roles:
                # pick first available
                role = next(iter(available_roles.keys()), None)
            skill = self._valid_skill(
                role,
                str(data.get("skill") or ""),
                requested_skill,
                available_roles,
            )
            return Plan.single(
                role=role,
                reasoning=data.get("reasoning", ""),
                skill=skill,
            )

        if data.get("type") == "multi":
            steps_raw = data.get("steps", [])
            steps: list[PlanStep] = []
            for s in steps_raw:
                role = s.get("role")
                if role not in available_roles:
                    continue  # skip unknown roles
                steps.append(
                    PlanStep(
                        role=role,
                        task=s.get("task", ""),
                        description=s.get("description", ""),
                        skill=self._valid_skill(
                            role,
                            str(s.get("skill") or ""),
                            requested_skill,
                            available_roles,
                        ) or "",
                    )
                )
            if not steps:
                # fall back to single role
                fallback_role = next(iter(available_roles.keys()), None)
                return Plan.single(role=fallback_role, reasoning="multi plan had no valid steps")
            return Plan.multi(steps=steps, reasoning=data.get("reasoning", ""))

        # Unknown type → single fallback
        fallback_role = next(iter(available_roles.keys()), None)
        return Plan.single(role=fallback_role, reasoning=f"Unknown plan type: {raw[:200]}")

    @staticmethod
    def _valid_skill(
        role: str | None,
        proposed_skill: str,
        requested_skill: str,
        available_roles: dict[str, dict[str, Any]],
    ) -> str | None:
        if not role or role not in available_roles:
            return None
        allowed = {
            str(item.get("id") or "").strip().lower()
            for item in available_roles[role].get("skills") or []
            if item.get("id")
        }
        proposed = proposed_skill.strip().lower().lstrip("$")
        requested = requested_skill.strip().lower().lstrip("$")
        if proposed and proposed in allowed:
            return proposed
        if requested and requested in allowed:
            return requested
        return None

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any] | None:
        """Extract a JSON object from a string, tolerating ```json fences and prose."""
        if not raw:
            return None
        # Strip code fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        # Try direct parse
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass
        # Try to find a JSON object inside
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None
