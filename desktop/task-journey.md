# A clearer task journey — beta.20 local preview

This preview implements the four approved experience improvements. The English interface, full-floral light/dark gardens, provider connections and shared execution core are retained. It does not add an automatic desktop-control agent or change provider assignments.

## Discover the changes

An unobtrusive **New in 0.5.0-beta.20** strip opens **What’s new**. Its four cards lead to the feature guide, task templates, recorded activity and the current delivery. **Got it** or dismissing the strip remembers this version on the installation; ordinary reloads do not reintroduce it. **Help and diagnostics → What’s new** and the command palette reopen it. It does not open a modal or interrupt a running task automatically.

**Explore features** gathers templates, role models, usage/budgets, project files/history, offline drafts, backups, operation sessions and updates. Project-dependent entries explain their availability through disabled controls until a project is connected. It invokes existing controls and approval policies.

## Start with an editable brief

The four existing starting points now open a brief containing **Goal**, **Deliverables**, **Acceptance criteria**, and optional **Constraints**. **Use task brief** inserts editable text into the current draft. It sends no task, API probe or model change. Replacing nonempty text needs confirmation; cancel preserves it. A changed project/task/draft invalidates the open brief rather than overwriting newer text. Goal text forms the first line, keeping generated task titles concise.

Above the composer, a compact setup row identifies the current project, configured provider or mixed providers, and roles needing setup. It evaluates this conversation's assignments and selected mode. **Ready to start** means saved configuration is present; it is not an API-verification claim. API tests remain optional. Chronos is local scheduling; offline mode remains draft-only.

## Follow the actual work

The conversation includes **Task progress**: Queued, Plan, Work, Deliver; actual recorded steps and active roles; elapsed time; and waiting-for-approval/retained-work status. No percentage or estimated completion time is fabricated. **Recorded plan** expands real step descriptions. **Full activity** retains the underlying events. The top **View progress** shortcut returns to the progress area in a long conversation and becomes **Review delivery** on completion or interruption.

## Review a usable delivery

**Result** begins with the recorded outcome, completed steps, outputs for this run, and reviewed artifact saves. **Completed work** uses recorded execution descriptions. **Checks & open items** reports execution issues and clearly states that independent test results are not recorded; assertions made in the council response are not promoted to verified checks.

Artifacts and save counts are scoped to the selected run, even across multiple runs in one conversation. Old outputs remain in Artifact library. **Preview**, **Review and save**, hash-checked acceptance and **Version history** retain their existing behavior. Recorded artifact saves are explicitly not a complete project diff. Failed output loading has a visible retry. Stale project/task/run responses cannot populate another delivery.

**Council response** retains the complete model output. **Continue conversation**, **Review for gaps** and **Refine this result** help continue from it. Preparing follow-up text sends nothing; replacing an existing draft needs confirmation.

## Verification scope

The isolated `journey-ui-smoke` suite exercises the actual native UI and shared core: introduction persistence/help reentry, feature navigation, template editing/cancel/stale-draft protection, configured versus verified setup, real streamed steps, two real fixture-backed runs, per-run artifacts, reviewed saves and draft-only follow-ups. Light/dark/narrow screenshots are saved under `dist/journey-ui-evidence`. All fixture requests go to an inert localhost model; no user key or paid service is used.

The combined packaged runner now requires eight suites. Current local results and screenshots are recorded in [verification](verification.md). Three-platform current-head CI, publication and real account/OS-permission acceptance are separate from this local preview. Signing/notarization remains excluded by the user.
