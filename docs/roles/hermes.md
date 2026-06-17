# 📨 Hermes — The Orchestrator

> *Messenger of the gods, conductor of the pantheon.*

Hermes is the chief orchestrator. **Every** user request passes through him. He doesn't have a single domain — his job is to **understand** what you want and **decide** which other god(s) should handle it.

## Personality

Hermes is calm, decisive, and strategic. He thinks in plans, not in solutions. When a task lands, his first move is always: *"Who is best suited for this? Do I need one god, or several?"*

## Powers

- **Task understanding**: reads the user's intent, even when vaguely worded.
- **Routing**: chooses the right god (or sequence of gods) for each task.
- **Multi-step planning**: decomposes complex tasks into a sequence of role-specific subtasks.
- **Summarization**: at the end of a multi-step run, he synthesizes all results into a coherent answer.

## Limits

- Hermes does **not** execute tasks himself (no terminal, no web, no images).
- Hermes is **stateless** — every call is fresh; he doesn't remember previous asks.
- Hermes's planning quality depends entirely on his underlying LLM. Use your strongest model here.

## How he works (under the hood)

When you call `p.ask("...", mode="auto")`:

1. Hermes's LLM receives a system prompt asking it to output a JSON plan.
2. The plan is either:
   - `{type: "single", role: "..."}` — one god handles it, or
   - `{type: "multi", steps: [...]}` — a sequence of gods.
3. Hermes executes the plan, passing prior step results as context to subsequent steps.
4. In multi mode, Hermes writes the final summary.

The actual implementation: [`pantheon/core/hermes.py`](../../pantheon/core/hermes.py) and [`pantheon/core/router.py`](../../pantheon/core/router.py).

## Configuration

```yaml
pantheon:
  hermes:
    model: claude-sonnet-4-20250514   # use a strong model
    provider: anthropic
    temperature: 0.2                  # low; planning should be deterministic
    max_tokens: 4096
```

## Tips for getting good routing

- **Be specific in your task**. Hermes picks based on role `description` strings; if those match your words, routing works well.
- **Use `role:<name>`** when you know exactly who should handle it (skips planning).
- **Use `multi`** when you want to force multi-step collaboration regardless of what Hermes thinks.

## Example

```python
result = p.ask("Research the latest trends in LLM agents and write a summary")
# Hermes will likely route: athena (research) → hephaestus (structure it nicely)
```

Or:

```python
result = p.ask("Refactor this Python function", mode="role:hephaestus")
# Skip Hermes's planning; go straight to Hephaestus.
```

## Customizing Hermes

Hermes doesn't have a separate prompt file — his behavior is encoded in `Router.PLANNER_SYSTEM` (see `core/router.py`). To customize, subclass `Router` and inject your own system prompt.
