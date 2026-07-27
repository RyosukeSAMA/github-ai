---
name: schedule-and-deliver
description: Convert an explicit natural-language time request into a persistent local Chronos job and confirm its next run. Use for reminders, recurring agent work, and delayed tasks.
---

# Schedule and Deliver

Work as Chronos. The schedule must be explicit enough to execute safely.

## Workflow

1. Extract the task payload separately from its timing.
2. Determine whether it is one-time, interval, daily, or cron-like recurrence.
3. Preserve the requested execution mode or target god when present.
4. Reject ambiguous timing instead of guessing a date or timezone.
5. Create the persistent local job through the attached scheduler.
6. Confirm the job id, normalized schedule, next run, and task prompt.

Use the host timezone unless the user provides another timezone. A reminder
request without a clear time should return examples of accepted phrasing rather
than silently creating an incorrect job.
