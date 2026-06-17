# ⏰ Chronos — The Scheduler

> *The personification of time. Neither created nor destroyed; only transformed.*

Chronos doesn't do creative or analytical work. He runs things **on time**. He's the only god that doesn't use an LLM.

## Personality

Mechanical. Reliable. Logs everything. Doesn't improvise.

## Powers

- Receives scheduling intent (cron expressions, periodic tasks)
- Will eventually run real cron jobs (planned for v0.2; in v0.1 he just confirms the request)

## Limits

- Does **not** write code, research, or create — he's infrastructure, not intelligence.
- In **v0.1**, Chronos is a stub. He confirms the request and timestamps it, but does **not** actually persist a cron job. Use APScheduler / cron / systemd timers directly for now.

## How it works (v0.1)

When you call `p.ask("...", mode="role:chronos")`, Chronos returns a confirmation message:

```
[Chronos] Received scheduling request:
  - Task: ...
  - Received at: 2024-...Z

Note: This is v0.1 — Chronos confirms the request but does not
persist a real cron job yet.
```

## Configuration

```yaml
pantheon:
  roles:
    chronos:
      # No LLM, no model/provider needed.
      enabled: true
```

## Roadmap for Chronos

In v0.2, Chronos will:
- Parse cron expressions and natural-language scheduling ("every weekday at 9 AM")
- Persist jobs to a local SQLite DB
- Run them via APScheduler
- Send results back to other roles when triggered

## Example

```python
result = p.ask("Every weekday at 9 AM, ask Athena for the latest AI news", mode="role:chronos")
print(result["content"])
```

## Customizing Chronos

Subclass `Chronos` and override `run()` to actually schedule. See [`pantheon/roles/chronos.py`](../../pantheon/roles/chronos.py).
