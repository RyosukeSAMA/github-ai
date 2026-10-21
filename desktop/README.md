# Pantheon Desktop beta

The native app is an English, white-first workbench built on the same Python core as Web and CLI. Its renderer is separate from the browser design prototype in `docs/desktop`.

## First run

1. Open Pantheon and choose your project folder. **Opening project…** shows progress; the connected project appears as a folder tile with its actual name and full path. The first setup step gets a checkmark and **Configure models** becomes the next action. Click the folder to browse project files; use **Change project** or the sidebar chevron to choose another folder. If opening fails, its reason and **Choose another folder** remain visible. Canceling the picker keeps your current task and draft. The app bundles Python; installing Python or Node is unnecessary for a packaged app.
2. Open **Models & connections**. Save one provider connection, then choose **Use this provider for new tasks**. DeepSeek alone is sufficient for text tasks. Testing access sends a small, potentially billable request only when you confirm it.
3. Create a task and choose Auto route, Multi-role council, or a specialist. **Assign role models** can use one provider for all roles or different providers per role. Connections are saved once; assignments stay with each conversation.
4. Run the task. Conversation, Result and Activity show actual shared-core results and events. Usage reports missing prices and missing provider usage as unknown.
5. Preview outputs in Result or Artifact library. **Review and save** prepares a real diff; accepting checks the file hash again before writing. The project editor also keeps a draft separately from the file on disk.

Windows and Linux use their native window controls. The default light theme, optional dark theme, Focus layout, text size and context width are saved per installation. Icon tooltips work with hover and keyboard focus. Ctrl/Cmd+K opens search and commands; Ctrl/Cmd+N starts a task; Ctrl/Cmd+Enter sends it.

The welcome page pairs the white interface with a quiet architectural illustration, sky/sand colors and an overview of the five council roles. Both illustrations are local vector assets; task reading and execution keep their plain workspace. Long folder names retain their full title/path even when the folder face or sidebar label needs truncation.

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

The app checks the official GitHub stable release on startup and periodically, and has a manual check. A prompt requires a newer version and an installer matching the current OS and architecture. It opens the official Releases page; it does not silently install or restart. Replace the application to update it. Workspace data stays outside the bundle. Retain the prior app for rollback and stop services before making a private `pantheon backup`.

Current local packages are **beta builds with ad-hoc macOS signing, without Developer ID notarization or Windows Authenticode signing**. Public distribution still needs signing credentials and platform acceptance. Do not disable operating-system security globally. Build from source if you do not trust an unsigned beta.

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

Set `PANTHEON_DESKTOP_PYTHON` to your development interpreter for `npm start --prefix desktop`. For the isolated native smoke test, use `DEBUG=pw:browser node desktop/test/native-smoke.cjs` (on PowerShell set `$env:DEBUG = "pw:browser"` first); optionally set `PANTHEON_TEST_EXECUTABLE` to the packaged executable. The test creates its own project and profile and calls a localhost model stub. It does not use saved user keys, contact paid models, send messages or modify the user's installed service.

See `.github/workflows/desktop.yml` for the three-platform build, package and smoke-test pipeline. Passing a local macOS run does not establish Windows/Linux native acceptance or real provider/channel access. See [verification](verification.md) for the actual evidence and remaining validation.

### Application icon

`assets/icon.svg` places the existing Pantheon mark inside a rounded tile with transparent outer spacing and a soft shadow. It supplies the application PNG, macOS ICNS and Windows ICO; the Web/CLI branding stays unchanged. Regenerate the committed icon files after editing the frame or source mark:

```sh
npx --prefix desktop playwright install chromium
node scripts/desktop/build_icons.cjs
```
