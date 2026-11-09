# Pantheon Desktop beta

The native app is an English, white-first workbench built on the same Python core as Web and CLI. Its renderer is separate from the browser design prototype in `docs/desktop`.

For the current button locations, English labels, operation scopes and beginner workflow, see the [Chinese controls and features guide](../docs/desktop/controls.zh-CN.md).

Connection controls, saved connections and model menus show small, locally bundled provider marks. Watercolor portraits remain the role identity. Model fields accept typing, offer searchable choices and support Arrow Up/Down, Enter, Escape and Tab; selecting a choice does not test or call a model. Full IDs remain editable, and unknown providers use a neutral glyph. Catalog entries and API verification remain separate. The connection hint identifies custom endpoints and local/remote Ollama runtimes. Role details show configured assignments, without claiming that a task has used them. See [asset sources and usage scope](../docs/desktop/provider-marks.md).

Top-bar **Connection status** opens a non-modal panel separating project-service access from saved provider test evidence, with model IDs, timestamps, reconnect and connection settings. Opening it does not probe a provider. Focus layouts are independent per native window; theme and accessibility preferences remain shared. New windows start in the standard layout. **Open in new window** (Command/Ctrl Shift N) saves task and editor drafts before opening the same project/task; save errors keep the originating window and draft intact. With no project selected, **New window** opens a fresh welcome screen.

Toolbar previews: [Light](../docs/desktop/toolbar-status-light.png) · [Dark](../docs/desktop/toolbar-status-dark.png) · [Narrow](../docs/desktop/toolbar-status-narrow.png). The screenshots use isolated fixture connections and do not show the user's real API status.

## beta.22 checked website delivery

This milestone adds reviewed website criteria, actual desktop/mobile browser evidence, up to two approved text-only repair requests, hash-guarded candidate application, separate user acceptance and a reviewed project handoff across Desktop, Web and CLI. See [website delivery workflow, limits and CLI commands](delivery-checks.md).

## beta.21 project continuity

This milestone adds a shared **Project overview** to Desktop and Web: user-controlled goals, decisions, outputs and next steps, tracked file observations and a reviewed continuation into a new conversation. Existing drafts remain intact. See [project continuity behavior and limits](project-continuity.md).

## beta.20 task journey

This milestone adds a version-aware **What’s new**, an **Explore features** guide, editable task briefs, current-task setup, real-event progress and a per-run delivery summary with reviewed saves and deliberate follow-ups. See [task journey behavior and verification scope](task-journey.md). The approved floral themes remain intact.

## First run

1. Open Pantheon and choose your project folder. **Opening project…** shows progress; the connected project appears as a folder tile with its actual name and full path. The first setup step gets a checkmark and **Configure models** becomes the next action. Click the folder to browse project files; use **Change project** or the sidebar chevron to choose another folder. If opening fails, its reason and **Choose another folder** remain visible. Canceling the picker keeps your current task and draft. The app bundles Python; installing Python or Node is unnecessary for a packaged app.
2. Open **Models & connections** and follow its two numbered steps. Enter the provider/model, URL and API key; optionally choose **Test API**, then **Save connection**. Testing requires confirmation and can incur provider usage; testing alone does not save settings or unlock assignment. Unsaved edits lock step 2. After saving, choose **Use this provider for new tasks** for future-task defaults, or **Assign this task** for the current conversation. Successful application closes configuration and shows a persistent green confirmation on the workbench with its exact scope. Saving alone keeps the dialog open so several provider connections can be added; **Done** ends this save-only flow without changing role assignments. The confirmation's **Add another provider** action reopens configuration at an unsaved provider. Existing tasks and Chronos are kept when updating new-task defaults. **Refresh models** is under **Storage & streaming**. DeepSeek alone is sufficient for text tasks; more providers can be added independently.
3. Create a task and choose Auto route, Multi-role council, or a specialist. **Assign role models** can use one provider for all roles or different providers per role. Connections are saved once; assignments stay with each conversation.
4. Run the task. Conversation, Result and Activity show actual shared-core results and events. Usage reports missing prices and missing provider usage as unknown.
5. Preview outputs in Result or Artifact library. **Review and save** prepares a real diff; accepting checks the file hash again before writing. The project editor also keeps a draft separately from the file on disk.

A saved API key displays a fixed masked row with **Saved** and **Change**. The mask is a display-only element: the renderer never fetches a saved secret, and the mask is never submitted as a credential. **Change** opens an empty password field for a replacement; **Cancel change** retains the stored key without discarding other edited settings. Returning all fields to their saved values clears the unsaved state. Reopening configuration restores the saved mask.

Windows and Linux use their native window controls. The default light theme, optional dark theme, Focus layout, text size and context width are saved per installation. Icon tooltips work with hover and keyboard focus. Ctrl/Cmd+K opens search and commands; Ctrl/Cmd+N starts a task; Ctrl/Cmd+Enter sends it.

**Focus layout** hides the left sidebar, right task context and council progress row so the current task can use the full window width. It works on a new task even though its context is already collapsed. The toolbar button stays highlighted, a **Focus** indicator remains visible, and a short message confirms the change. Click **Exit Focus layout** to restore standard navigation. **Show context** can temporarily open a drawer in Focus without changing layouts. Use the command palette to open project files, find another task, configure models or leave Focus; the layout persists across theme changes and restarts without changing the task, draft or model assignment.

The refined workbench groups recent tasks into **Pinned**, **Today** and **Earlier**, with state indicators and a compact actions menu. The project folder retains its full name and path in hover/focus details; **Task context → Project location** expands the canonical path. The composer grows with multi-line input up to a bounded height and then scrolls internally, keeping its tools and send control in place.

Conversation and Result use a bounded reading column, semantic lists, scrollable tables and labelled code blocks. **Copy code** and **Copy response** write the visible text to the native clipboard through a bounded write-only bridge and show confirmation. Result content stays stable across unchanged polling. Activity uses role/event rows, artifacts separate saved state from review actions, and Changes distinguishes additions, removals and diff headers before the existing hash-checked save. The saved task title and current status share one compact header row. A small council summary shows only roles present in recorded events; expand it for recorded participants and status guidance and Open full activity. Approval and recovery guidance stays visible even while details are collapsed. The follow-up composer starts smaller and grows with longer drafts.

Task context starts closed and opens only when requested; changing themes or saving text preferences preserves that choice. Task context keeps model IDs in each provider button's tooltip, and separates reported calls/tokens from estimated or unknown cost. Models & connections, role assignments and Desktop preferences have scrollable bodies and fixed action rows. **Storage & streaming** expands advanced connection options. Preference sliders show their values immediately; saving confirms success. Existing task assignments, API tests and default-model scope retain their prior behavior.

The welcome page pairs the white interface with a quiet architectural illustration, sky/sand colors and an overview of the five council roles. Both welcome illustrations are local vector assets; task reading and execution retain the selected garden around local text backdrops and solid code/table surfaces. Long folder names retain their full title/path even when the folder face or sidebar label needs truncation.

New tasks open in a full-floral botanical watercolor garden with a centered prompt, Mediterranean colonnade and five smaller watercolor role portraits. The light theme uses ivory/sage surfaces and a green send button; the moonlit dark theme uses deep blue-green surfaces and a purple send button. The theme icon switches both the artwork and controls, retaining the current draft and saving the theme preference. All text, portraits, mode choices and buttons remain live interface elements. Artwork is bundled locally and makes no network request. See [art provenance and prompts](../docs/desktop/botanical-art.md).

Click a portrait to select its mode, or open **Council mode** for descriptions of Auto route, Multi-role council and each specialist; the menu supports arrow keys, Home/End and Escape. The four starting points only populate a draft and ask before replacing existing text. They never send a task or call a provider. An empty prompt cannot be sent. Changing a mode while a draft is being saved retains the latest typed text. The context panel starts collapsed and can be opened from its icon; the matching garden stays visible behind Conversation, Result, Activity and Changes, including running/completed tasks and reopened conversations. A compact header, collapsed council details and local text backdrops and solid code/table surfaces keep text, code and controls readable without a full-width panel covering the landscape. User messages fit their content, and the tabs and composer float above the canvas. Project files and other utility pages keep their dedicated surfaces. Role details show responsibilities and a concise provider label; hover the provider to inspect its full model ID. Reopening an existing task does not redisplay the initial connected-project banner.

## Search, appearance, help and spending

Search groups commands, tasks and artifacts in the current project. Arrow Up/Down moves through enabled results; Home/End move within results, Enter opens one, Escape closes. Project-only commands are disabled before connection. Loading, no matches and failed-search retry remain visible; results from an older query/project cannot replace the current query.

Desktop preferences offers **System**, **Light** and **Dark**. System follows native OS changes, including the matching garden. An explicit theme overrides OS changes. Appearance is shared between windows; Focus remains independent.

**Help and diagnostics** contains first-run steps, controls, shortcuts and the app version. Its local JSON export is built from an allowlist: runtime/OS versions, service flags and aggregate task counts. It excludes credentials, prompts/messages, file contents, project names/paths, server addresses and raw logs/errors. It is never uploaded automatically.

**Usage and budgets** offers request limits per task/24 hours, output-token limits per request, estimated USD limits and user-entered token/media prices. Empty limits mean unlimited. Unknown usage/prices remain unknown; USD limits block unpriced requests. All roles share workspace limits across Desktop/Web/CLI. Estimates are not invoices.

## File history and model plans

Reviewed saves retain actual text snapshots: the latest 20 per file, up to 200 per workspace. **Version history** appears in the file editor and on saved artifacts. Comparing a snapshot changes no file. **Review restoration** prepares a real diff; accepting checks the current file hash again. Existing data-only workspace backups include recorded snapshots, but do not back up the project tree. Generated unsaved artifacts retain their original source-task output.

**Assign role models → Compare model plans** suggests Cost conscious, Balanced and Quality preference. The cost comparison uses entered input/output prices for an illustrative 1M input + 1M output token workload; balanced uses 60% of your quality rating and 40% normalized price. Quality is your own 1–5 rating, not an inferred benchmark. Additional tool/vision capabilities are explicit user declarations. By default only a model with current saved API verification is eligible; including untested models is an explicit choice. Missing ratings/prices leave the corresponding suggestion unavailable. A suggestion populates the assignment dialog for review; only **Apply to this task** saves it. No provider test, task or model switch runs automatically.

## Task and project lifecycle

- A private local service owns execution; closing or reloading a renderer does not resend a task. Opt into tray background mode to keep the last window and local core alive. Quitting warns about active owned tasks, requests cancellation and stops only desktop-owned services. Provider calls already sent may still finish and incur usage.
- Sessions, drafts, attachment IDs, events, results and review records live outside the app bundle under the shared `DataPaths`. Existing project configuration, `.env` and state paths retain their precedence. `pantheon paths` shows them.
- Restart reconciles core task archives. Unfinished work is marked interrupted. Recovery requires review and an explicit resume; no task, message or file write is automatically replayed.
- A compatible local Web service is reused only after identity, workspace, lease owner and a private capability are checked. Desktop does not stop an existing service. If a pre-desktop service owns the project, update/restart it yourself or choose another project. The current stable v0.4.0 installation has no desktop bridge.
- Task center searches titles and messages, filters tasks, and supports rename, pin, archive, restore and another window. The artifact library searches real outputs and links back to their source task. Other CLI/Web runs are visible through the shared task ledger; CLI continuous-chat history retains its existing explicit session format.
- Multiple windows share one service per project. Optimistic versions prevent a stale window from overwriting another window's draft. A conflict keeps the local draft visible; reload the task before retrying the edit.
- Git worktrees start from an explicitly selected commit on a new `pantheon/…` branch. They do not copy uncommitted files. Opening the worktree creates an independent workspace/service. Git must already be installed for this optional feature; the desktop app does not bundle it.

## Broader workbench

Project files, real terminal streaming with native command confirmation, skills, plugin instructions, MCP servers and approvals, project memory, local schedules, Telegram/Slack/Discord callback configuration, media models, image generation and audio transcription use the existing core contracts. Saving a messaging connection sends no platform message. Image/PDF understanding, generation and transcription require the configured provider's account access and can incur charges. HTML artifact previews are isolated from scripts and network access.

Drop supported images/PDFs to attach them; audio belongs in **Capabilities → Media** for transcription. Drop a folder to choose a different project after native confirmation. Native file picker, reveal in Finder/Explorer, optional completion/approval notifications, tray background mode and an optional global shortcut are available. macOS/Linux notification permissions are managed by the operating system.

## Remote host and shared devices

**Service and updates → Connect remote server** accepts an HTTPS origin with Web authentication enabled and desktop API v1. The server must run this bridge version, permit its public hostname through `PANTHEON_ALLOWED_HOSTS`, and have TLS configured by its operator. Sign into the same server from another Desktop installation to access the same sessions and artifacts. Files and terminal commands remain on the displayed remote host. This is online shared-server access; there is no offline merge or hosted Pantheon account service.

Login cookies stay in the native process. Remembering a remote password is opt-in and uses Electron OS-backed encryption; insecure Linux fallback storage is refused. API keys stay in the core credential store and are never delivered to the renderer. Local tokens are private, transient and excluded from backups, including secret-inclusive backups.

## Updates and recovery

Use **Service & updates → Updates** to choose **Stable** or **Beta + Stable**. Beta installations start on the Beta channel; channel selection never downgrades or replaces the app automatically. A release must contain an installer for this computer's actual OS and CPU. The update card shows release notes, download progress, cancel/retry and checksum verification. Files come from the official repository and must match GitHub's SHA-256 digest or the release's `SHA256SUMS.txt` before opening. Cached installers are verified again before use.

**Back up & open installer** asks for native confirmation, saves a private data-only backup of each idle local service owned by Desktop, then opens the OS installer. Quit Pantheon before replacing the application. Active tasks block maintenance. Remote and reused services must be managed on their host. Downloaded older compatible versions are available under **Version recovery**; choosing one is explicit and does not silently restore data.

**Backups & recovery** creates a workspace backup with a native Save dialog. Project source files are outside this backup; use Git or your own file backup for them. API credentials/configuration are excluded unless **Include credentials and configuration** is explicitly selected and confirmed. Choose an archive, inspect its contents summary, then confirm restoration. Desktop stops only its owned idle service, applies the shared offline validation/rollback rules and reconnects sibling windows. Restored running tasks, pending approvals/messages, channel callbacks and schedules stay stopped or paused until reviewed. Existing files replaced during restoration are retained in a private rollback directory reported by the operation.

See [downloads, installation and recovery](downloads.md) for platform-specific steps. These beta packages are not Developer ID notarized or Windows Authenticode signed. Signing/notarization is excluded from this delivery.

## Build and verify

Maintainers need Node 22+, Python 3.10–3.12 and platform build tools. Build separately on every target OS; PyInstaller output is platform-specific.

```sh
python -m pip install --require-hashes -r requirements.lock
python -m pip install -e '.[dev]' pyinstaller==6.22.3
npm ci --prefix desktop
python -m pytest tests/test_desktop.py tests/test_backup.py
npm test --prefix desktop
python scripts/desktop/build_runtime.py
npm run build --prefix desktop
npm run package --prefix desktop
```

Set `PANTHEON_DESKTOP_PYTHON` to your development interpreter for `npm start --prefix desktop`. For the isolated native smoke test, use `DEBUG=pw:browser node desktop/test/native-smoke.cjs` (on PowerShell set `$env:DEBUG = "pw:browser"` first); optionally set `PANTHEON_TEST_EXECUTABLE` to the packaged executable. The test creates its own project and profile and calls a localhost model stub. It does not use saved user keys, contact paid models, send messages or modify the user's installed service. `npm run test:providers --prefix desktop` checks provider marks, searchable/keyboard model menus, custom IDs, single/mixed assignment, cancel retention and light/dark/narrow layouts in another isolated project; it saves dummy connections without requesting API tests, model refresh or task runs. Screenshots and its report are written to `dist/provider-ui-evidence`.

See `.github/workflows/desktop.yml` for the three-platform build, package and smoke-test pipeline. Passing a local macOS run does not establish Windows/Linux native acceptance or real provider/channel access. See [verification](verification.md) for the actual evidence and remaining validation.

### Application icon

`assets/icon.svg` places the existing Pantheon mark inside a rounded tile with transparent outer spacing and a soft shadow. It supplies the application PNG, macOS ICNS and Windows ICO; the Web/CLI branding stays unchanged. Regenerate the committed icon files after editing the frame or source mark:

```sh
npx --prefix desktop playwright install chromium
node scripts/desktop/build_icons.cjs
```

`npm run test:toolbar --prefix desktop` verifies actual native-window layout isolation, draft saving before opening, empty-project windows, saved API health, light/dark/narrow status panels and real local-service restart/reconnect in a disposable project. Explicit API probes use a localhost fixture; toolbar operations make no provider calls. Evidence is written to `dist/toolbar-ui-evidence`.


### Combined packaged verification

Set `PANTHEON_TEST_EXECUTABLE` to the built app and run `npm run test:packaged --prefix desktop`. The runner executes the full native smoke, provider UI, toolbar UI, update/recovery, productivity, offline-sync, operation and task-journey suites in separate disposable profiles and requires all eight to exit successfully. CI runs this same command path on macOS, Windows and Linux. It records stage durations, failed/expired stages and the combined outcome in `dist/desktop-evidence`, `dist/provider-ui-evidence` and `dist/toolbar-ui-evidence`; all eight evidence directories are uploaded even on failure.

The combined runner allows 600 seconds for the full native flow and 300 seconds for each focused suite, within the 45-minute job limit. A bounded `PANTHEON_DESKTOP_TEST_TIMEOUT_MS` override accepts 1000–900000 ms for diagnosis; malformed or out-of-range values fail immediately. Standalone native smoke retains its original platform defaults unless overridden. All existing assertions and zero-paid-call checks remain enabled. Passing local macOS tests does not establish a Windows/Linux CI pass.


## Offline drafts and local operations

The optional **Offline drafts** tab binds a private cache to a remote host/account/project. It permits unsent draft edits/new tasks and cached search, with explicit sync, duplicate protection and revision-based conflict review that also detects Web changes. Provider settings, attachments, files and execution are not replayed. **Operation sessions** offers a visible isolated browser and, on macOS with actual permission, scoped application actions. Every plan needs native review; Stop cancels its remaining steps. See [the complete workflow, limits and acceptance boundaries](offline-and-operations.md).
