# Desktop completion plan — 2026-11-03

Approved scope: implement the remaining work in order, excluding software signing/notarization. Preserve the English client, floral light/dark themes, shared Web/CLI core, one-provider/mixed-provider choices and existing user data. No simulated account or hardware acceptance is reported as real validation.

## Ordered delivery and acceptance

1. **Merged; all three platforms passed; publication uploading: release and upgrades.** Stable/Beta channels; verified installer download/progress/cancel/retry; release notes; private pre-upgrade backup; guided install and version/data recovery. Publish the new Beta installers/checksums for actually tested OS/architectures after CI passes. Signing/notarization excluded.
2. **Implemented: download/version documentation.** Current native screenshots, system/architecture matrix, beginner install/update/recovery steps, retire misleading prototype/current-version statements.
3. **Implemented and native-tested: search/commands.** Complete keyboard selection, grouped results, loading/empty/failure states and workspace-aware commands.
4. **Implemented and native-tested: system theme.** System/Light/Dark with explicit override, including artwork, shared themes and independent window layouts.
5. **Implemented and native-tested: help/diagnostics.** In-app quick start, controls/shortcuts/version, explicit redacted diagnostic export.
6. **Implemented and native-tested: budget UI.** Validated beginner forms over the existing budget/usage contracts; unknown usage/prices remain unknown.
7. **Implemented and packaged-tested: backup/restore UI.** Reuse shared offline backup/restore validation and rollback, native file pickers, deliberate confirmation, no task/message replay or silent credential export.
8. **Implemented and native-tested: artifact versions.** Persistent version history, compare and conflict-checked restoration/review.
9. **Implemented and native-tested: model plans.** Explicit cost/balanced/quality preferences using verifiable capabilities/prices or user-entered data, with user-reviewed application and no silent role-model changes.
10. **Pending: offline cross-device sync.** Extend the existing authenticated HTTPS-host architecture; local queue/conflict review; no duplicated execution/message replay and clear local/remote file boundaries.
11. **Pending: browser/application operation.** Opt-in, scoped observable actions with an explicit stop; real platform permissions/adapter availability are represented honestly. Build after the earlier foundations.
12. **Acceptance in parallel with implementation:** actual third-party providers/media, Telegram/Slack/Discord accounts/callbacks, deployed HTTPS/two devices, native permissions and fresh-machine install-to-upgrade journey. Requires available accounts/devices and permission to perform actual external actions. Existing local fixture and three-platform CI results remain separately labelled.

## Current implementation notes

Working checkout: `/Users/taimei/Documents/codex 2/github-ai-desktop-completion`, branch `codex/desktop-release-updates`, based on merged main `d809f131ac6b36eadead76f39b60c70fe76e43dc`.

The existing core backup/restore deliberately requires a stopped runtime (`RuntimeLease`). Desktop must stop only owned, idle services and invoke an offline runner maintenance command, then reconnect all sibling windows; never bypass that lease or stop a reused/remote service. Update downloads must be bound to the official repository release metadata and a verified checksum, never arbitrary renderer URLs/paths. Existing unsigned beta installers remain explicitly unsigned; signing is not part of this scope.


Phase 1 local verification: 314 Python tests + 3 expected skips, 16 Node tests, Ruff, full macOS arm64 packaged four-suite pass. beta.17 packages built; current-head Windows/Linux CI and publication next. Shared backup changes also pause legacy restored Chronos schedules. Current download instructions and native update/recovery screenshots replaced outdated guidance. No paid APIs, user configuration or installed applications changed.


2026-11-04: PR #38 merged as `ae632205cb39a8d5b0da8bb562d95654a8780e9a`; all 12 checks passed for `c12f9b728bbd650f8e5f0aeded049d6378841563`. Desktop CI `41622646989` passed all four packaged suites on macOS arm64, Windows x64 and Linux x64. Five CI installers and SHA256SUMS are prepared for Beta publication.

The beta.18 working branch `codex/desktop-search-theme-help` implements grouped keyboard search with loading/empty/error/retry, System/Light/Dark and native OS updates, allowlisted local diagnostic export, beginner budget/price forms and persistent file snapshots with compare/reviewed restoration. Development native/productivity tests and backend version/retention/conflict tests passed. Packaged cross-platform checks will run after this batch is complete.
