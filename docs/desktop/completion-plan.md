# Desktop completion plan — 2026-11-03

Approved scope: implement the remaining work in order, excluding software signing/notarization. Preserve the English client, floral light/dark themes, shared Web/CLI core, one-provider/mixed-provider choices and existing user data. No simulated account or hardware acceptance is reported as real validation.

## Ordered delivery and acceptance

1. **Implemented; CI/publication pending: release and upgrades.** Stable/Beta channels; verified installer download/progress/cancel/retry; release notes; private pre-upgrade backup; guided install and version/data recovery. Publish the new Beta installers/checksums for actually tested OS/architectures after CI passes. Signing/notarization excluded.
2. **Implemented: download/version documentation.** Current native screenshots, system/architecture matrix, beginner install/update/recovery steps, retire misleading prototype/current-version statements.
3. **Pending: search/commands.** Complete keyboard selection, grouped results, loading/empty/failure states and workspace-aware commands.
4. **Pending: system theme.** System/Light/Dark with explicit override, including artwork, shared themes and independent window layouts.
5. **Pending: help/diagnostics.** In-app quick start, controls/shortcuts/version, explicit redacted diagnostic export.
6. **Pending: budget UI.** Validated beginner forms over the existing budget/usage contracts; unknown usage/prices remain unknown.
7. **Implemented and packaged-tested: backup/restore UI.** Reuse shared offline backup/restore validation and rollback, native file pickers, deliberate confirmation, no task/message replay or silent credential export.
8. **Pending: artifact versions.** Persistent version history, compare and conflict-checked restoration/review.
9. **Pending: model plans.** Explicit cost/balanced/quality preferences using verifiable capabilities/prices or user-entered data, with user-reviewed application and no silent role-model changes.
10. **Pending: offline cross-device sync.** Extend the existing authenticated HTTPS-host architecture; local queue/conflict review; no duplicated execution/message replay and clear local/remote file boundaries.
11. **Pending: browser/application operation.** Opt-in, scoped observable actions with an explicit stop; real platform permissions/adapter availability are represented honestly. Build after the earlier foundations.
12. **Acceptance in parallel with implementation:** actual third-party providers/media, Telegram/Slack/Discord accounts/callbacks, deployed HTTPS/two devices, native permissions and fresh-machine install-to-upgrade journey. Requires available accounts/devices and permission to perform actual external actions. Existing local fixture and three-platform CI results remain separately labelled.

## Current implementation notes

Working checkout: `/Users/taimei/Documents/codex 2/github-ai-desktop-completion`, branch `codex/desktop-release-updates`, based on merged main `d809f131ac6b36eadead76f39b60c70fe76e43dc`.

The existing core backup/restore deliberately requires a stopped runtime (`RuntimeLease`). Desktop must stop only owned, idle services and invoke an offline runner maintenance command, then reconnect all sibling windows; never bypass that lease or stop a reused/remote service. Update downloads must be bound to the official repository release metadata and a verified checksum, never arbitrary renderer URLs/paths. Existing unsigned beta installers remain explicitly unsigned; signing is not part of this scope.


Phase 1 local verification: 314 Python tests + 3 expected skips, 16 Node tests, Ruff, full macOS arm64 packaged four-suite pass. beta.17 packages built; current-head Windows/Linux CI and publication next. Shared backup changes also pause legacy restored Chronos schedules. Current download instructions and native update/recovery screenshots replaced outdated guidance. No paid APIs, user configuration or installed applications changed.
