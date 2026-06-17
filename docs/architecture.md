# Pantheon Architecture

This document explains how Pantheon works under the hood. If you just want to use it, the [README](../README.md) is enough. Read this when you want to **extend** or **debug** Pantheon.

## High-level design

Pantheon is built around three layers:

```
┌────────────────────────────────────────────────────┐
│              Interaction layer (3 entry points)     │
│   CLI  │   Web UI (FastAPI + HTML)   │  Python SDK  │
└───────────────┬──────────────────────────┬──────────┘
                │ both call the same...    │
        ┌───────▼─────────────────────────▼──────┐
        │      Pantheon facade (core/pantheon.py) │
        └───────┬─────────────────────────────────┘
                │
        ┌───────▼─────────────────────────────────┐
        │   Hermes orchestrator (core/hermes.py)  │
        │   - understands the task                 │
        │   - picks single role or multi plan      │
        │   - runs the plan                        │
        │   - summarizes results                   │
        └───────┬─────────────────────────────────┘
                │
        ┌───────▼─────────────────────────────────┐
        │   Router (core/router.py)                │
        │   - uses Hermes's LLM to plan            │
        └───────┬─────────────────────────────────┘
                │
   ┌────────────┼────────────┬────────────┬────────────┐
   ▼            ▼            ▼            ▼            ▼
 Hephaestus   Athena       Apollo      Chronos      ... your roles
   │            │            │            │
   └────────────┴────────────┴────────────┘
                │
        ┌───────▼─────────────────────────────────┐
        │   LLM adapter layer (llm/)               │
        │   OpenAI / Anthropic / Ollama / ...      │
        └─────────────────────────────────────────┘
```

The three entry points (CLI / Web / SDK) all call the **same `Pantheon.ask()` method**, so behavior is identical no matter how you invoke it. This is deliberate: the Web UI and CLI are thin wrappers over the SDK.

## Request lifecycle

When a user calls `p.ask("write a Python decorator")`:

1. **Task construction** (`core/base.py:Task`): A `Task` object is created with the user's content and mode (default `auto`).

2. **Hermes dispatch** (`core/hermes.py:Hermes.dispatch`):
   - If mode is `role:<name>`, jump to step 5 with that role.
   - Otherwise, ask the Router for a plan.

3. **Router plans** (`core/router.py:Router.plan`):
   - Calls the LLM with a special planner system prompt.
   - The LLM returns JSON describing either:
     - `{type: "single", role: "..."}` — one god handles it, or
     - `{type: "multi", steps: [...]}` — sequence of gods.

4. **Execution** (`core/hermes.py:Hermes._run_*`):
   - **Single**: the named role's `run()` is called once, result returned.
   - **Multi**: each step's role is called in order; each step receives the prior steps' results as `context`. The final step's result is the immediate answer.

5. **Role execution** (`pantheon/roles/<name>.py`):
   - Each role's `run(task, context)` method formats the prompt with its own `system_prompt` and calls its LLM client.

6. **Summarization** (multi mode only): The Router's `summarize()` is called with all step results, producing a coherent final answer.

7. **Return** to the user as a `dict`: `{mode, plan, content, steps}`.

## Why this design?

### Why a single orchestrator (Hermes) instead of agents calling each other?

- **Predictable**: One LLM decides the plan. No infinite loops of agents calling agents.
- **Cheap**: We only pay for one planning LLM call per multi-role task, not N+1.
- **Debuggable**: You can log the plan and see exactly what Hermes decided.

### Why allow per-role models?

Different tasks favor different models:
- **Claude Sonnet** is strong at code → Hephaestus uses it.
- **GPT-4o** is solid at tool use + multimodal → Athena & Apollo use it.
- **No LLM at all** → Chronos doesn't need one.

This matches the user's intuition that "different roles should use different tools."

### Why three interfaces?

| User | Prefers |
|------|---------|
| Sysadmin / power user | CLI |
| Casual user / demo | Web UI |
| Developer building on top | Python SDK |

All three share the same `Pantheon.ask()` so there's one source of truth.

## Key classes

| Class | Location | Purpose |
|-------|----------|---------|
| `Pantheon` | `core/pantheon.py` | Public facade |
| `Hermes` | `core/hermes.py` | Orchestrator |
| `Router` | `core/router.py` | LLM-driven planner |
| `Role` (ABC) | `core/base.py` | Base class for all gods |
| `Task` / `TaskResult` / `Plan` | `core/base.py` | Data classes |
| `BaseLLMClient` (ABC) | `llm/base.py` | LLM provider interface |
| `OpenAIClient` / `AnthropicClient` / `OllamaClient` | `llm/` | Provider implementations |

## Adding a new role

See [CONTRIBUTING.md](../CONTRIBUTING.md#a-新增一个角色-) for the step-by-step. The TL;DR:

```python
# pantheon/roles/ares.py
from pantheon.core.base import Role, Task, TaskResult

class Ares(Role):
    name = "ares"
    description = "Security auditor"
    default_model = "claude-sonnet-4-20250514"
    default_provider = "anthropic"
    default_temperature = 0.2

    def run(self, task: Task, context=None) -> TaskResult:
        # your implementation
        ...
```

Then register in `pantheon/roles/__init__.py` and add a section in `config/pantheon.example.yaml`.

## Configuration

Configuration is split between:

- **`config/pantheon.yaml`** — non-secret config (model names, temperature, role enables).
- **`.env`** — secrets (API keys). Never commit.

This split lets users commit their `pantheon.yaml` (it's project-specific tuning, not secret) while keeping keys local.

The YAML schema is documented in `config/pantheon.example.yaml`.

## Error handling

- **No API key**: a warning is logged at startup; calling that role will fail with a clear error.
- **Unknown role** (in `role:<name>` or planner output): a `TaskResult` with `success=False` is returned; the user sees a friendly message.
- **Planner returns invalid JSON**: Router falls back to picking the first available role.
- **LLM call fails** (network, rate limit, etc.): the role catches it, returns a `TaskResult` with `success=False, error=...`. The dispatch continues for multi-role tasks (subsequent steps still run).

## Performance

- Each `Pantheon.ask()` creates the orchestrator on demand. For Web UI, it's created **once** and reused across requests.
- For high-throughput use, wrap `Pantheon()` in your own long-lived instance.

## What's intentionally NOT here

- **No agent-to-agent messaging**: avoids complexity and infinite loops.
- **No persistent memory**: every ask is stateless. (v0.2 may add session memory.)
- **No vector DB**: Athena could benefit from RAG, but it's not required for v0.1.
- **No streaming output yet**: results are returned all at once. (Trivial to add — modify `Role.run` to yield chunks.)
