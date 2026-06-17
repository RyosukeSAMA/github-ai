# Frequently Asked Questions

## General

### What is Pantheon, in one sentence?

A framework where multiple specialized AI agents (called "gods") collaborate on tasks, coordinated by an orchestrator (Hermes).

### Why the Greek mythology theme?

It's a memorable mental model: each "god" has a domain (Hephaestus = forge = code, Athena = wisdom = research). You can rename them however you like.

### Is Pantheon production-ready?

**No.** It's at v0.1 (alpha). The architecture is sound but lacks production features: auth, persistent memory, observability, rate limiting, etc. Use it for experiments and prototypes.

### How is this different from LangChain / AutoGen / CrewAI?

| Framework | Focus | Pantheon |
|-----------|-------|----------|
| LangChain | Composable LLM chains | Different abstraction (role-based, not chain-based) |
| AutoGen | Multi-agent conversations | Pantheon has one orchestrator, not free-form chats |
| CrewAI | Roles + tasks | Very similar! Pantheon is lighter, has explicit models per role, no CrewAI-specific dependencies |

Pantheon is intentionally **small**. No heavy framework. Read the code in an afternoon.

## Configuration

### Do I need both OpenAI and Anthropic keys?

No. Set the provider per role in `pantheon.yaml`. You can run everything on one provider, or on local Ollama.

### Can I use a model not in the dropdown?

Yes. Edit the role's `model:` field to whatever string your provider accepts (e.g. `gpt-4-turbo`, `claude-opus-4-...`). The framework doesn't validate model names — it just passes them through.

### Can I add a new provider (e.g. Cohere, Mistral)?

Yes. Create `pantheon/llm/<provider>_client.py` implementing `BaseLLMClient`, then register it in `pantheon/llm/__init__.py: get_llm_client()`. The interface is two methods: `complete()`.

### Can I disable a role?

In `pantheon.yaml`:
```yaml
pantheon:
  roles:
    chronos:
      enabled: false
```

### How do I change the planner (Hermes's) model?

In `pantheon.yaml`:
```yaml
pantheon:
  hermes:
    model: gpt-4o
    provider: openai
```

Use your strongest model here — Hermes's planning quality bounds the whole system's quality.

## Usage

### Can I stream the output?

Not in v0.1. Each role's `run()` returns a `TaskResult` once. Adding streaming is a small change: have `run()` yield chunks. PRs welcome.

### Can roles call each other?

Only via Hermes in `multi` mode. There's no direct role-to-role messaging in v0.1. This avoids infinite loops.

### Can I save conversation history?

Not built-in. v0.2 will add session memory. For now, pass `context` yourself in multi-step custom flows.

### Can I use Pantheon from a FastAPI / Django app?

Yes — just instantiate `Pantheon()` once at startup and call `p.ask()` from your endpoints. Don't create a new instance per request.

### How much do calls cost?

Each `p.ask()` makes:
- 1 planner LLM call (Hermes) — small
- N role LLM calls (one per role that runs)

In single-role mode: 2 calls. In multi-role with 3 steps: 4 calls. Add up by your providers' pricing.

## Errors

### "No API key for provider 'X'"

Set the key in `.env` or the shell. See [setup.md](setup.md).

### "Role 'X' is not registered"

You used `p.ask(..., mode="role:nonexistent")` or the planner hallucinated a role. Check `pantheon.yaml` and `pantheon.roles.__init__`.

### Hermes keeps picking the wrong god

Try lowering the planner temperature (set `hermes.temperature: 0.0` in `pantheon.yaml`). Also check the role `description` strings — Hermes decides based on those.

### Hermes always picks single role and never uses multi

Either your tasks are genuinely single-step, or your task descriptions are too vague. Try `mode="multi"` explicitly first to see if multi-step works, then iterate on task phrasing.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md). Short version:

- New role? → subclass `Role`, register in YAML.
- Bug? → open an issue with a minimal repro.
- Feature? → open an issue first to discuss; PRs without alignment often stall.

## License

MIT. Do what you want, just keep the copyright notice.
