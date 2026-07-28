---
name: review-code-change
description: Review a code change for concrete defects, regressions, security risk, and missing tests. Use for pull requests, diffs, patches, and pre-release quality checks.
---

# Review Code Change

Athena analyzes contracts and risk; Hephaestus validates implementation details.

## Review Order

1. Understand the intended behavior and the boundaries changed.
2. Trace modified inputs through state changes, side effects, and outputs.
3. Look for correctness defects, compatibility breaks, unsafe assumptions,
   security exposure, concurrency issues, and data-loss paths.
4. Check whether tests cover the newly introduced behavior and important failures.
5. Ignore purely stylistic preferences unless they hide a behavioral problem.

## Output

Lead with findings ordered by severity. Each finding must name the affected file
or component, explain the failure scenario, and propose a concrete correction.
Then list open assumptions and test gaps. If there are no actionable findings,
say so clearly and identify the remaining verification risk.

Do not invent line numbers, command results, or repository context that was not
provided by a file, diff, connected tool, or prior task step.
