# Task outcomes and recovery

CLI, Web HTTP/SSE, webhooks and durable task history use the same terminal outcome rules. These changes are currently unreleased.

| Field | Meaning |
| --- | --- |
| `task_id` | Durable task ID, or `null` if setup failed before a task was created |
| `status` | `completed`, `failed`, `partial_failure`, `stopped` or `interrupted` |
| `success` | `true` only when status is `completed` |
| `error` | Failure explanation, or `null` on success |
| `steps` | JSON objects containing role, content, success, error, duration and recorded metadata |

Existing content, plan, communications and memory fields remain available. The Python SDK retains `TaskResult` objects in `steps`; transport serialization does not mutate them. HTTP step metadata keeps its existing flattened public fields. Model identity comes from execution records; an absent record is not replaced with today's configuration.

`/api/ask` and `/api/channels/webhook` may return HTTP 200 for a completed request whose task failed. Check `success` and `status`; webhook `ok` equals `success`. Transport, authentication and request-validation failures still use HTTP error responses. Failed explicit-skill validation emits `step_error`, followed by `done` with `success: false`. SSE `done` includes task ID, status and error.

## CLI scripts

`pantheon ask "..." --raw` writes a JSON object to stdout, including when configuration or execution raises an error. Real steps are objects, not `TaskResult(...)` strings. Argument parsing errors remain normal CLI usage errors. Diagnostic logs use stderr.

- Exit 0: completed.
- Exit 1: failed or partially failed.
- Exit 130: stopped/interrupted, including keyboard cancellation after execution starts.

Human-readable runs retain partial output and show “Needs attention” on failure. `pantheon tasks --resume <id>` uses the same exit rules. This does not add an implicit continuous CLI conversation or change saved model assignments.

## Web interruption

If SSE closes without `done`/`error`, the Web client stops its local running indicators and preserves partial text with the task ID. It queries `/api/tasks/<id>` and, when available, the saved result archive. A confirmed terminal record restores the available result; an unavailable or still-running record displays “Connection interrupted” with the status unconfirmed.

The client never automatically resends or resumes that request. Check Settings → Info → Task history before deciding to retry. A network interruption alone does not prove the server task failed or that no provider charge occurred.

Model catalog refresh preserves in-progress custom IDs and focus. These drafts stay in the current page and are scoped to the chat (or new-chat defaults), role and provider. Applying a model remains explicit. Prompt enhancement applies only if its chat, mode, Hermes choice and draft revision still match; switching chats or changing Hermes cancels/invalidates the old request. Cancelling a browser request does not guarantee cancellation of a provider request already in flight.
