# Desktop completion — status on 2026-11-04

Approved scope: all remaining items in order, excluding Developer ID/Authenticode signing and notarization. Preserve the English client, floral light/dark gardens, shared core and explicit one-provider/mixed-provider choices.

| Item | Current implementation and evidence |
| --- | --- |
| Verified releases/upgrades | PR #38 merged; beta.17 published with five three-platform CI installers, checksums and verification JSON. Stable/Beta, bounded verified download, cancel/retry, pre-install offline backup and guided recovery are implemented. PR #40 adds GitHub-runner publication to avoid local upload timeouts, with tested-tree, platform/suite and uploaded-digest checks. |
| Download/version instructions | Native OS/CPU matrix, macOS 13+ actual runtime minimum, Windows without WSL, first-task/update/recovery steps and current native screenshots are maintained. |
| Search/commands | PR #39 merged after all 12 checks and three-platform five-suite packaging passed. Grouped keyboard search, stale-query protection, loading/empty/error/retry and project-aware commands. beta.19 also searches cached drafts/messages/artifacts offline. |
| System appearance | System/Light/Dark, native OS-change updates, shared theme and independent window Focus; native tests passed. |
| Help/diagnostics | In-app quick start, controls, shortcuts/version and explicitly exported allowlisted local diagnostics. No credentials, prompts/files, paths or raw logs in diagnostics. |
| Budgets | Beginner request/token/USD forms and user-entered token/media prices, duplicate/range validation and honest unknown values. Shared CLI/Web/Desktop enforcement is retained. |
| Backups/recovery | Owned idle local service only; shared stopped-runtime lease, inspected native archive selection, rollback and sibling reconnect. Restored jobs/messages/approvals stay stopped. |
| File versions | Actual bounded snapshots, comparison and conflict-checked reviewed restoration, including CRLF and external edits. |
| Explicit model plans | Cost/balanced/quality suggestions use user prices/ratings and model-specific API evidence, with review before Apply. A verified alias can override catalog omission. |
| Offline device drafts | Implemented: opt-in private host/account/workspace cache, new unsent tasks, local search, coalesced bounded queue, explicit idempotent sync, revision conflicts including Web edits, retained/exportable local copies. Disk errors do not masquerade as network outages. No execution/message/file/model replay. Source and final macOS packaged fixture tests passed. |
| Browser/application operations | Implemented: visible isolated origin-scoped browser, native reviewed plans, bounded steps, redacted activity/captures and Stop; download/pop-up/cookie/bridge guards. macOS allowlisted app adapter uses fixed argv scripts plus actual Accessibility/Automation checks; scripts compiled without running app actions. Windows/Linux application adapter is explicitly unavailable; browser is cross-platform. Native inert-browser tests passed. |

Working checkout: `/Users/taimei/Documents/codex 2/github-ai-desktop-completion`, branch `codex/desktop-offline-operations`. Delivery requires all seven suites on each actual packaged CI build, a matching tested source tree and verified uploaded installer digests. The release verification JSON records those final gates; source implementation and account/device acceptance are recorded separately.

Published beta.17: `https://github.com/RyosukeSAMA/github-ai/releases/tag/v0.5.0-beta.17`, from successful native run `41622646989` and tree-matching main `ae632205cb39a8d5b0da8bb562d95654a8780e9a`; publisher run `41770372252` succeeded. PR #39 merged as `5096b4bde9d7f65a5e1cd3b34e27ea1b9b9fe370`, with successful native run `41759083880`. PR #40 merged after updated-head CI `41769355842`.

## Real account/device acceptance

- **Passed:** one minimal real saved DeepSeek `deepseek-flash` API request, 1,382 ms. No key or provider response content was printed/copied. This is separate from zero-paid-call native fixtures.
- **Passed locally:** 44 Chrome Web regression checks; shared Python and Node suites; real native source workflows and inert browser. Final packaged and three-platform result counts are recorded in `desktop/verification.md` when complete.
- **Unavailable accounts/devices:** OpenAI/Anthropic and their media APIs are not configured; real Telegram/Slack/Discord callbacks/messages, deployed HTTPS/two physical devices, fresh-machine installation and OS permission/tray/notification/global-shortcut journeys need the corresponding accounts/devices and explicit message recipients. No real platform messages were sent.
- **macOS application permissions:** adapter code and fixed-script compilation are checked, but real Accessibility/Automation approval and app actions remain device acceptance; fixtures do not count as that approval.
- **Excluded by user:** publisher signing/notarization. Do not add it to the unfinished implementation list.

No provider configuration, role assignments or installed application bundle was replaced during this work. The minimal DeepSeek probe records normal usage/readiness evidence. Fixture projects/profiles and release builds are separate from user conversations and keys.
