# Chronos - The Scheduler

Chronos is the local scheduling role. It does not use an LLM. Its job is to parse simple scheduling requests, persist them locally, and run them later through Pantheon.

## What Chronos Does

- Parses natural-language schedule requests.
- Creates local jobs in `.pantheon/chronos_jobs.json`.
- Runs due jobs from the FastAPI web server background loop.
- Can route a scheduled job back through Auto, Multi-role, or a direct god role.
- Exposes jobs in the Web UI Workspace Activity panel.

## Supported Phrases

Examples:

```text
every 10 minutes remind me to drink water
in 30 minutes ask Athena to summarize my notes
daily at 09:00 ask Apollo to draft a status message
10分钟后提醒我开会
每天 9:00 提醒我查看任务
```

Chronos infers direct roles from phrases such as `ask Athena`, `ask Apollo`, `让火神`, or `让雅典娜`. Otherwise the job runs in Auto routing.

## Web UI Usage

1. Click `Chronos` in the left Pantheon list, or run `/chronos`, `/schedule`, or `/timer`.
2. Send a scheduling request.
3. Open Workspace -> Activity.
4. Check the `Chronos Jobs` section.
5. Use `Run now`, `Pause`, `Resume`, or `Delete` as needed.

## Storage

Runtime jobs are stored under the current workspace:

```text
.pantheon/chronos_jobs.json
```

This directory is ignored by Git because it is local runtime state, not source code.

## Configuration

Chronos should remain model-free:

```yaml
pantheon:
  roles:
    chronos:
      enabled: true
      provider: none
      model: none
```

The Web UI attaches the local scheduler automatically when the FastAPI app starts.

## Limits

- The scheduler runs only while the Pantheon web server is running.
- This is not a system daemon yet. If the machine sleeps or the server is stopped, jobs will resume when the server is running again.
- The first parser supports common interval, relative, daily, and one-time clock expressions. Full cron expressions are not implemented yet.
- Jobs execute by calling Pantheon again, so scheduled tasks that need model output still require the relevant API keys to be configured.
