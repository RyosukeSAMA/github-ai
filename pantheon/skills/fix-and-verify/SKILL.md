---
name: fix-and-verify
description: Diagnose a software defect, make the smallest compatible correction, and verify the affected behavior. Use for bugs, regressions, failing tests, and focused code changes.
---

# Fix and Verify

Work as Hephaestus and keep the change scoped to the reported behavior.

## Workflow

1. Identify the observed behavior, expected behavior, and likely execution path.
2. Inspect the relevant code and tests when they are available.
3. State the most likely root cause before changing code.
4. Implement the smallest change that preserves surrounding contracts.
5. Add or update a focused regression test when the risk justifies it.
6. Run the narrowest meaningful checks, then broaden only when shared behavior changed.
7. Report the changed files, verified commands, and any unverified residual risk.

Never claim a command passed unless its output was actually available. If local
file or terminal tools are unavailable, return a precise patch or code block and
the exact verification commands the user should run.
