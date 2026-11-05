# Offline drafts and local operation sessions

These are optional Desktop features. One configured model provider remains sufficient for normal tasks. Offline storage and operation sessions start only after you choose them.

## Share drafts across your devices

Use an authenticated HTTPS Pantheon host running this Desktop source version. Sign in to that same host/account from each computer. Its workspace and project files stay on the host; this feature does not copy a local project tree to another device.

1. Open **Service & updates → Offline drafts** and select **Enable offline drafts**. Confirm the local cache. The host must support Desktop API v1 revision 2 and the draft-sync revision protocol; an older stable Web/CLI host needs an explicit source upgrade before this works.
2. The private app profile stores the task list/drafts plus viewed conversation and artifact details. Provider credentials, endpoint secrets and project files are excluded. The cache is bounded to 200 entries/about 20 MB; unviewed history and old evicted artifacts may be unavailable offline.
3. When disconnected, the badge shows **Offline drafts**. Existing drafts and new unsent tasks can be edited; **Saved locally** means the host has not received them. Cached search works on local titles, drafts and viewed messages/artifacts. Provider settings, files, attachments, terminal commands and task execution require the host connection. Usage is explicitly unavailable offline.
4. Sign in again if needed, then choose **Sync drafts**. Reconnection alone does not send queued changes. A server operation ID makes a lost-response retry idempotent; it does not execute a task or send a conversation message.
5. If another device or the Web UI changed the draft/metadata, compare **This computer** and **Remote host**. **Keep my draft for reviewed sync** queues a revised edit; choose **Sync drafts** separately to apply it. **Use remote draft** retains a recovered copy of your previous local text. Newer changes can produce another conflict rather than being overwritten silently.

Pending edits are coalesced per task, with a maximum of 100 tasks. Up to 20 discarded local drafts remain under **Recovered draft copies**. **Export local drafts…** writes a private text JSON file for manual safekeeping. Inspect it before sharing. Workspace backup ZIP files cover host state (including reviewed text snapshots), not this device's unsynced app-profile cache; sync or export pending drafts before moving to another computer. Removing a cache is refused while edits remain pending. Uninstalling or deleting the application profile can remove unsynced local text.

**Cached remote workspaces → Open cached workspace** can reopen opted-in data without a live login. You must sign into the original host before syncing. Caches are bound to the exact server origin, account and workspace. Login cookies and passwords are not saved in these cache files. Remembered remote passwords retain the separate opt-in OS-backed storage policy.

## Run a reviewed browser plan

1. Choose a project, then **Operation sessions** in the sidebar.
2. Select **Isolated browser**, enter an HTTPS URL (or a localhost preview URL) and select **Start scoped session**. Confirm the exact origin in the native dialog.
3. Add **Navigate**, **Click element**, **Fill field**, **Wait**, or **Capture browser** steps. Click/fill uses a CSS selector. Navigation must stay within the approved origin. Plans have at most 30 steps, with waits of at most 3 seconds each/10 seconds total.
4. Select **Review & run steps** and inspect the native summary before approving. Steps run in the separate visible browser. Normal site assets can use other hosts; top-level navigation is limited to the approved origin. Downloads, pop-ups and device permissions are blocked. The browser has neither the Pantheon native bridge nor the app's login cookies.
5. Inspect **Session activity**, **View capture**, or explicitly **Save capture…**. Activity contains action types/statuses, without typed text, selectors, page contents or URL tokens. Plans and captures are not automatically uploaded or stored as task messages.
6. **Stop session**, the workbench's **Stop**, or closing the controlled browser cancels remaining steps and closes that owned browser. Site requests/actions already sent may finish; stopping cannot undo them. Changing projects also stops the scoped session.

These forms are a user-reviewed operation workbench. Existing agent MCP tool approvals remain separate; opening this workbench does not grant a model unreviewed desktop access.

## macOS application adapter

The application adapter is available only on macOS, for installed TextEdit, Notes, Safari, Google Chrome or Visual Studio Code. Select one application as the scope. Available steps are **Bring app forward**, **Type text**, **Click named button**, **Press key**, and **Wait**. The button title must match a button in the app's front window; complex custom interfaces may not expose it. Add explicit Enter/Tab steps instead of embedding control characters in typed text. The supported key list is shown in the form.

Typing/clicking/keys require actual **Accessibility** access. **Request Accessibility** invokes the OS prompt; grant access in system settings and reopen the panel to refresh. macOS may separately request **Automation** access for System Events on the first approved action. A missing or denied permission leaves an actionable error; successful script compilation is not evidence that your OS granted access. Only one native application plan runs at a time across windows. Typed values are argv to a fixed script, never script source or shell commands.

Windows/Linux currently provide the browser adapter; their native application adapter is explicitly unavailable. Notifications, tray/shortcut behavior and real application permissions still depend on the user's OS session. Electron documents [Accessibility status](https://www.electronjs.org/docs/latest/api/system-preferences#systempreferencesistrustedaccessibilityclientprompt-macos); Apple explains [inter-application Apple events](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/HowMacScriptingWorks.html).

## What has actually been checked

Native fixtures use an actual shared core with an isolated transport to exercise offline edits, two-client conflicts, explicit sync and cache reopen. Browser fixtures use a real isolated Chromium window against an inert localhost site to exercise fill/click/capture, navigation/download/pop-up guards, cookie/bridge isolation and cancellation. They send no paid model calls and perform no real third-party application actions. A separate minimal saved DeepSeek request succeeded during this delivery. Real OpenAI/Anthropic/media accounts, Telegram/Slack/Discord callbacks, deployed HTTPS/two physical devices, and real Accessibility/Automation permissions remain separate account/device acceptance, not fixture passes.
