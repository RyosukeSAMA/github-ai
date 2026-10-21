# Desktop beta verification

Validation date: 2026-10-21 (Asia/Singapore). Desktop package version: `0.5.0-beta.1`; shared core source is based on `v0.4.0` with the new bridge. These are separate from the already-installed stable Web/CLI service.

| Check | Recorded result |
| --- | --- |
| Python tests, including existing Web/CLI contracts | 308 passed, 3 skipped |
| Existing Web browser regression | 40 passed |
| Native proxy and release policy tests | 6 passed |
| Ruff and JavaScript syntax | Passed |
| Development native app, macOS arm64 | Full smoke flow passed with one localhost model call and zero paid calls |
| Final packaged native app | Passed the complete smoke flow and two normal exits (code 0); evidence in `dist/desktop-evidence/native-smoke.json` |
| Bundled Python | Frozen runtime starts without a system Python installation |
| macOS application integrity | Ad-hoc signature passed `codesign --verify --deep --strict` |
| macOS DMG integrity | `hdiutil verify` passed |
| Windows/macOS native packaging | CI build, packaged smoke and installer packaging passed at `7e4ee10` |
| Linux native packaging | Packaged smoke and AppImage passed at `7e4ee10`; Debian metadata fixed after that run. Final CI results are linked in PR #34. |

The three Python skips are the opt-in live model check and two Windows-native checks on a non-Windows host. The FastAPI TestClient emits an upstream deprecation warning; no test failure is hidden by it.

## What the native smoke test exercises

`desktop/test/native-smoke.cjs` creates a temporary project and app profile. It saves a provider connection to a localhost model fixture, updates new-task defaults, runs a specialist through the real shared core, reloads the page, saves a generated HTML output through a real diff, rejects an external-file conflict, reloads and saves a fresh edit, searches actual message content, checks that task focus survives unchanged polling and that attention filtering excludes ready/completed tasks, opens another window, resolves conflicting drafts, configures three dummy connections without making paid calls, checks role-model isolation across conversations, opens the capability pages and messaging form, verifies that direct terminal proxy requests cannot bypass native confirmation, executes a harmless confirmed `echo` command, saves an unsent draft, quits and restarts.

The final package test additionally asserts that the renderer is running in the packaged app. Python and UI assets come from the bundle. Screenshots use the local fixture and are not evidence of real commercial-provider access. Native consent dialogs are substituted only through the external test driver inside its isolated fixture; production dialogs are not overridden. No diagnostic quit controls or test command bypasses are shipped.

The smoke test uses Playwright's Electron driver and requires the native process to exit with code 0 within 20 seconds. A 240-second overall deadline prevents stalled CI. It also requires the final restart and shutdown to succeed before writing passing evidence. This exposed a real multi-window cleanup defect: accessing a destroyed window to retrieve its ID interrupted quit. Window IDs are now captured before destruction, and unexpected cleanup errors are recorded instead of silently disappearing.

## Backend checks added for Desktop

Tests cover private capability authentication; remote bindings requiring actual Web login instead of a local token; two authenticated clients seeing the same sessions; optimistic draft conflicts and isolation; persisted attachment drafts; invalid payload rejection; a request ID executing once; retaining a new draft typed during execution; reconciling a completed core archive after a lost final event; artifact extraction; diff/hash conflict protection; excluded secret paths; explicit Git worktree creation; excluding transient capabilities from every backup; and making restored active runs and pending reviews inert.

## Validation still required for public release

- Final three-platform CI packaging results and hands-on acceptance on supported desktop environments. CI status and installer downloads are linked in PR #34.
- Real OpenAI/Anthropic/DeepSeek media/account access and Telegram/Slack/Discord callbacks and replies. No real platform messages were sent in this work.
- An operator-managed real HTTPS remote server and a second physical device. Shared-session authentication is tested locally; this does not establish real TLS deployment or offline synchronization.
- OS notifications, tray behavior, global shortcuts, real OS drag-and-drop and credential prompts across the target platforms. The code and opt-in controls exist; automated fixture checks do not establish every OS permission behavior.
- Developer ID signing/notarization and Windows Authenticode credentials. The local macOS beta is ad-hoc signed and not notarized. It is not being advertised as a signed public release.

## Local beta artifacts

The latest local macOS Apple Silicon review app, DMG and ZIP are in `dist/desktop-beta`; default maintainer builds use `dist/desktop`. Replacing the app does not replace workspace configuration or data. No source changes were applied to the user's already-installed stable service, and it was not stopped.

`dist/desktop-beta/SHA256SUMS.txt` records the SHA-256 hashes of the current local DMG and ZIP.
