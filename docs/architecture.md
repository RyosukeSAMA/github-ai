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
        │   - selects role-scoped SKILL.md methods │
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

The three entry points (CLI / Web / SDK) all call the **same `Pantheon.ask()` method**, so core capabilities and state are shared across entry points. This is deliberate: the Web UI and CLI are thin wrappers over the SDK.

## Request lifecycle

When a user calls `p.ask("write a Python decorator")`:

1. **Task construction** (`core/base.py:Task`): A `Task` object is created with the user's content, mode (default `auto`), and optional explicit Skill id.

2. **Hermes dispatch** (`core/hermes.py:Hermes.dispatch`):
   - If mode is `role:<name>`, jump to step 5 with that role.
   - Otherwise, ask the Router for a plan.

3. **Router plans** (`core/router.py:Router.plan`):
   - Calls the LLM with a special planner system prompt.
   - Includes the enabled Skill catalog for each god.
   - The LLM returns JSON describing either:
     - `{type: "single", role: "..."}` — one god handles it, or
     - `{type: "multi", steps: [...]}` - a sequence of gods with a step type,
       dependencies, an expected deliverable, and acceptance criteria.

4. **Skill selection and execution** (`core/hermes.py:Hermes._run_*`):
   - An explicit Skill is validated against its assigned gods.
   - Otherwise the role receives at most one matching implicit Skill.
   - Skill instructions are injected only for the selected step and recorded in `TaskResult.metadata`.
   - **Single**: the named role's `run()` is called once, result returned.
   - **Multi**: dependency-ready safe steps run concurrently (up to 4); unsafe tools and scheduling run exclusively. Hermes converts dependencies
     into typed `AgentMessage` records (`handoff`, `question`, `review_request`, or
     `revision_request`) and sends the role its contract plus prior results.
   - Successful steps return a structured `result` message to Hermes or the role
     that supplied the incoming work.

5. **Role execution** (`pantheon/roles/<name>.py`):
   - Each role's `run(task, context)` method formats the prompt with its own `system_prompt` and calls its LLM client.

6. **Summarization** (multi mode only): The Router's `summarize()` is called with all step results, producing a coherent final answer.

7. **Return** to the user as a `dict`:
   `{mode, plan, content, steps, communications}`.

## Why this design?

### Why Hermes-mediated messages instead of open-ended agent chat?

- **Predictable**: Hermes owns the plan, dependencies, and final synthesis, so
  agents cannot create an infinite conversation loop.
- **Useful collaboration**: roles still exchange explicit handoffs, questions,
  review requests, revision requests, and results.
- **Debuggable**: every message is recorded and streamed to Workspace Activity.
- **Bounded work**: plans have at most eight steps and up to two recovery rounds; requests reserve the shared budget before being sent.

### Why allow per-role models?

Each role can use a separately configured provider/model. Directory discovery updates selectable models without switching existing conversations or defaults. Actual API checks are explicit and bound to credentials, model and endpoint. Chronos uses no LLM for deterministic scheduling.

## Shared runtime and recovery

`WorkspaceServices` owns paths, credentials, readiness, budgets, tasks, memory, extensions, scheduler, media and channels. Execution snapshots isolate cancellation, roles and router settings between concurrent requests. A task ContextVar shares reservations across planner, independent workers, recovery and synthesis.

`TaskStore` persists the root request, attachment IDs and interpreted context, plan, complete step results and attempted external effects. Resume claims the failed task atomically, reuses successful steps and refuses unreviewed uncertain external effects. Full results are separate private JSON artifacts; lists/details can return marked excerpts.

`MediaService` validates bounded inputs, stores private UUID artifacts and calls OpenAI Responses/Images/Audio or Anthropic Messages. Media reservations use explicit per-request estimates rather than pricing base64 as text. Apollo can create one real image and records that effect before sending.

`ChannelStore` verifies platform callbacks before parsing tasks, enforces identity/destination allowlists and atomically queues unique event IDs. Web acknowledges immediately and a single workspace worker invokes the shared runtime. Delivery is one attempt; uncertain replies are not automatically repeated. Backups disable adapters and convert pending events to interrupted state.

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
| `WorkspaceServices` | `core/services.py` | Shared workspace capabilities |
| `MediaService` / `ChannelStore` | `core/media.py`, `core/channels.py` | Multimodal artifacts and verified platform tasks |
| `Pantheon` | `core/pantheon.py` | Public facade |
| `Hermes` | `core/hermes.py` | Orchestrator |
| `Router` | `core/router.py` | LLM-driven planner |
| `Role` (ABC) | `core/base.py` | Base class for all gods |
| `Task` / `TaskResult` / `Plan` / `AgentMessage` | `core/base.py` | Task, plan, result, and collaboration contracts |
| `SkillStore` | `core/extensions.py` | Built-in/local SKILL.md registry and role matching |
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
    default_model = "claude-sonnet-4-6"
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
- **`.env` / supported system credential storage** — secrets. Never commit secrets or credential reference files.

Keep runtime configuration private; commit only reviewed examples without literal credentials. Setup can explicitly migrate keys to supported OS storage after readback verification.

The YAML schema is documented in `config/pantheon.example.yaml`.

## Error handling

- **No API key**: a warning is logged at startup; calling that role will fail with a clear error.
- **Unknown role** (in `role:<name>` or planner output): a `TaskResult` with `success=False` is returned; the user sees a friendly message.
- **Planner returns invalid JSON**: Router falls back to picking the first available role.
- **LLM call fails** (network, rate limit, etc.): the role catches it, returns a `TaskResult` with `success=False, error=...`. The dispatch continues for multi-role tasks (subsequent steps still run).

## Skill layout

Pantheon ships read-only built-ins under `pantheon/skills/<skill-id>/`. User
skills live under `.pantheon/skills/<skill-id>/`.

Each folder contains:

```text
skill-id/
├── SKILL.md
├── pantheon.json
└── agents/openai.yaml
```

`SKILL.md` contains portable instructions. `pantheon.json` contains role
assignment, trigger phrases, version, and workflow type. Disabling a built-in
does not edit the packaged file; the override is stored in
`.pantheon/skill_state.json`.

## Performance

- `Pantheon()` creates one orchestrator and Skill registry. Reuse that instance across requests.
- For high-throughput use, wrap `Pantheon()` in your own long-lived instance.

## What's intentionally NOT here

- **No unbounded peer-to-peer agent chat**: collaboration is structured,
  plan-driven, and mediated by Hermes.
- **No runtime replanning loop yet**: question, review, and revision steps are
  selected during planning rather than created recursively from agent output.
- **No vector DB dependency**: local long-term memory currently uses SQLite and bounded text matching.
- **No streaming output yet**: results are returned all at once. (Trivial to add — modify `Role.run` to yield chunks.)
