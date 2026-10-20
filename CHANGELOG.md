# Changelog

All notable changes to Pantheon are documented in this file.

## [0.3.3] - 2026-10-20

### Fixed

- Return nonzero CLI exit codes for failed, partially failed and stopped tasks, including resumed tasks; do not display a successful completion for failed work.
- Serialize raw CLI steps as JSON objects and keep constructor/execution errors in a JSON envelope with explicit success, status and error fields.
- Share terminal outcome rules between task history, CLI, HTTP, SSE and webhooks. Validation failures emit failed stream steps; webhook `ok` reflects execution success.
- Detect unexpected Web stream EOF/network interruption, retain partial replies and task IDs, and query saved task status/results without automatically resubmitting work.
- Preserve custom model drafts, expanded controls, focus and text selection during catalog refresh, with drafts isolated by chat/settings scope, role and provider.
- Bind prompt enhancement responses and undo state to the initiating chat, draft revision and Hermes choice. Ignore stale responses after navigation, edits or model changes.

## [0.3.2] - 2026-10-19

### Fixed

- Include bounded history from the active Web chat in follow-up requests, planning, role execution and synthesis. Preserve it in task checkpoints and resumed work; keep workspace memory and other chats separate. History uses at most 16 messages / 24,000 characters without an extra model call.
- Enhance prompts with the current chat's Hermes provider/model and report the model used, without retargeting saved defaults or requiring unrelated role connections.
- Keep saved custom connection models assignable after catalog refresh; accept exact custom IDs for individual roles and bulk model assignment. Retain configured empty drafts on reload.
- Test specialist CLI connections through their actual `llm_client` rather than an absent role attribute.
- Record execution providers/models in results and stream events, and persist reply provenance across reloads and model changes. Older replies without recorded metadata show that their model was not recorded; adding optional metadata does not create transcript conflict copies.
- Correct the English and Chinese setup guides to use `pantheon backup <path>` and `pantheon restore <path>`.

## [0.3.1] - 2026-10-14

- Save provider connections independently of role models; keep legacy configuration and credential storage usable without a mandatory migration.
- Let all AI roles share one provider/model or mix providers per role, including Hermes. Separate current-chat choices from explicitly saved new-chat defaults.
- Keep existing chats pinned to their model assignments across default changes and reloads; show and test each selected role's actual connection.
- Preserve provider/key/endpoint drafts when initial settings or catalog requests return after editing begins.
- Resolve DeepSeek and OpenAI credentials/endpoints independently across Web, CLI, SDK and media. Additional provider keys are optional; test probes never imply access to all models.

## [0.3.0] - 2026-10-14

- Share Memory, Skills, plugins, MCP policy/approvals and scheduling between CLI, Web and SDK; serialize cross-process state writes.
- Separate configured keys, catalog visibility and time-limited API verification; add dismissible first-run onboarding and supported OS credential storage with explicit migration.
- Add atomic request/cost reservations, task/daily caps and media-operation estimates; unknown prices remain unknown and SDK retries are disabled for budget-managed calls.
- Install/update in a staged environment with health checks and rollback; add native Windows PowerShell installation, startup service and ConPTY terminal.
- Persist step checkpoints, reuse successful steps on resume, review uncertain external actions and download full result archives.
- Run safe independent steps concurrently (up to four) and repair failed instructions within the existing plan (up to two rounds).
- Understand images/PDFs through OpenAI or Anthropic; generate actual images through Apollo/OpenAI; transcribe audio and save private media artifacts across entry points.
- Verify Telegram, Slack and Discord callbacks with identity/destination allowlists, durable deduplication, bounded queues and optional replies. Do not replay uncertain deliveries or restored queues.
- Refresh installation, workflow and platform documentation and screenshots. Keep WSL checks manually runnable; native Windows/Linux/macOS checks remain automatic.

## [0.2.6] - 2026-10-12

### Added

- Source-labelled continuation summaries for long multi-agent outputs, while retaining original step results. Failed summaries use explicit excerpts; summary calls count as normal model usage.
- Hashed runtime dependency locks shared by installers and CI.
- Stable per-workspace data locations shared by CLI, Web and SDK, preserving existing project data and configuration. `pantheon --workspace <path> paths` shows the effective paths.
- Exclusive Web runtime ownership, durable task status, cross-process stop requests, and interrupted-owner recovery after a crash.
- Task results in Web Settings → Info and `pantheon tasks --show <id>`. Stored results are limited to 200,000 characters and mark excerpts explicitly.
- Offline backup and restore, SQLite snapshots, retained recovery copies, and rollback after a failed restore. Maintenance prevents new CLI tasks from starting while data is copied.

### Fixed

- Task identifiers are unique across process restarts and available during direct-mode Web execution.
- Explicit configuration paths are resolved against the selected workspace.

## [0.2.5] - 2026-10-10

### Changed

- The top bar shows the Pantheon server connection state and opens Models for the current chat. Full model IDs no longer repeat in the top bar.
- Agent navigation shows each role's responsibility. Setup shows provider and readiness, with saved model IDs and key variable names in a collapsed details section.
- Saved model details flag defaults absent from the latest account model list. Catalog updates continue to preserve saved defaults and per-chat selections.

## [0.2.4] - 2026-10-10

### Fixed

- OpenAI and Anthropic recommendations now sync from public official model documents every six hours, including when no API key is configured. Published recommendations remain distinct from account-listed models.
- Official account catalogs refresh hourly, retry failures every five minutes, and include saved provider keys even when another provider handles the current chat. Custom endpoint credentials are never sent to official endpoints.
- Open Web pages pick up changed model catalogs every minute and when refocused, preserving unsaved Setup fields and per-chat model choices. Refresh errors and last successful sync time are visible.
- Anthropic discovery reads every page, excludes retired models, and retains the previous cache when pagination fails. OpenAI discovery excludes models whose shutdown date has passed.
- Current Claude models omit unsupported sampling parameters.

### Added

- GPT-6.1 Sol, Claude Sonnet 5.5, Claude Haiku 5.5, and Claude Fable 5.1 to the startup recommendations. Saved execution models remain unchanged.

## [0.2.3] - 2026-10-10

### Fixed

- Per-conversation model overrides now use independent execution snapshots, including concurrent and non-streaming requests.
- Disconnected Web tasks stop before further role/tool calls or synthesis. Web tasks have a 10-minute budget; model requests have a 120-second timeout and at most one SDK retry. Already accepted requests may still complete and be billed.
- Failed dependencies skip downstream steps; independent work continues and final results explicitly report partial failure. Plans are limited to eight steps and prior-result context is bounded.
- Conversation deletion persists tombstones to prevent stale tabs from restoring deleted chats. Archive/restore, visible save errors, capacity notices, and conflict copies improve local chat management.
- Tool descriptions reflect actual connected capabilities instead of claiming built-in browsing or multimedia generation.
- Remote Web binds require authentication; Host and Origin checks protect local APIs. Remote terminal execution requires explicit server opt-in, and terminal disconnects kill the process group.
- The installer selects stable release tags and supports explicit versions, updates, and rollback. WSL CI tests the proposed commit.

### Added

- Web update notices based on the latest published GitHub Release, with a manual check in Settings → Info.
- Durable Web conversations with browser-history migration, JSON export/import, and a previous-snapshot backup.
- Local 30-day API call and provider-reported token usage statistics in Settings → Info.

- Claude Opus 5.5 (`claude-opus-5-5`) and DeepSeek V4.1 Flash (`deepseek-flash`)
  in the shared Setup and per-role model catalogs.
- A one-line installer for macOS, Ubuntu, and WSL Ubuntu that checks Git and Python,
  creates an isolated virtual environment, and leaves existing directories untouched.
- GPT-6 Sol (`gpt-6-sol`) and GPT-6 Luna (`gpt-6-luna`) in the shared OpenAI
  Setup and per-role model catalog, using the existing Responses API path.
- GPT-6 Astra (`gpt-6-astra`) in the shared OpenAI Setup and per-role catalog,
  with coverage for discovery, cached availability, and Responses API requests.
- Composer prompt enhancement powered by the configured Hermes model, with a
  review-before-send flow and one-click undo to restore the original draft.
- Structured Multi-role contracts with typed work, question, review, and revision
  steps, explicit dependencies, expected deliverables, and acceptance criteria.
- Hermes-mediated agent messages for handoffs, targeted questions, review or
  revision requests, and step results, all visible in Workspace Activity.

### Changed

- New DeepSeek configurations use `deepseek-flash`; Claude Opus 5.5 requests omit
  sampling parameters that its always-on adaptive thinking rejects.
- New OpenAI selections recommend GPT-6 Astra while preserving saved models and
  existing role defaults. Setup explains when an API key is needed to discover
  models and verify account access.
- Multi-role execution now passes structured collaboration context together with
  prior results while keeping Hermes in control of routing and final synthesis.

## [0.2.1] - 2026-08-14

### Added

- Runtime model discovery for OpenAI, Anthropic, DeepSeek, and Ollama, with a
  `Refresh models` control in local Setup and a per-key local cache.
- Background model-catalog refresh for configured official provider endpoints;
  stale catalogs are checked every 24 hours without changing the saved model.
- GPT-5.6 Sol, Terra, and Luna in the OpenAI recommendation catalog.
- Claude Opus 5 and Claude Sonnet 5 in the Anthropic model catalog.
- Per-user background service management for macOS LaunchAgent and Linux systemd:
  `pantheon service install|status|start|stop|restart|logs|uninstall`.
- Opt-in `pantheon provider-test --role <god> --live` diagnostics and a live pytest
  smoke test that never runs without explicit consent.
- Playwright end-to-end coverage for session/mode navigation, panel behavior, Files,
  and HTML Preview, plus a dedicated GitHub Actions job.

### Changed

- Setup and per-agent model selectors now share the backend model catalog instead
  of maintaining separate frontend and backend lists.
- Refreshing a catalog preserves the saved/current model; selecting and saving a
  different model remains an explicit user action.
- Future official OpenAI GPT major versions (GPT-5 and later) use the Responses API
  path instead of relying on a GPT-5-only name check.
- Anthropic-compatible custom base URLs remain available without adding separate
  provider entries to the Setup UI.
- Migrated the Web scheduler lifecycle from deprecated FastAPI event hooks to a
  lifespan context with deterministic Chronos cleanup.
- Background services remain loopback-only by default and preserve the install
  environment's command path for local tools and MCP servers.

### Fixed

- Pantheon Web can now restart automatically after user login instead of requiring
  a manual terminal launch after every computer restart.
- Multi-role steps now retain the complete original request instead of relying on
  abbreviated planner labels. Decisions that genuinely require confirmation use
  2-4 explicit choices, per-option guidance, and a recommended option.
- A reply containing only `1`, `2`, `3`, or `4` can now continue an immediately
  preceding numbered-choice answer with the relevant task and selection restored.

[0.2.1]: https://github.com/RyosukeSAMA/github-ai/releases/tag/v0.2.1

## [0.2.0] - 2026-07-27

### Added

- Multi-session Web UI with first-prompt titles and per-chat routing/model state.
- Real-time multi-agent Activity timeline, HTML Preview, file browser/editor, and terminal.
- Structured agent responses, artifacts, attachments, voice input, slash commands, and Markdown export.
- Persistent Chronos jobs and local SQLite memory with suggestions and role-scoped recall.
- Six built-in `SKILL.md` workflows plus local Skill and prompt-pack management.
- MCP stdio and Streamable HTTP connections with tool discovery, per-god policies, approvals, and execution traces.
- Token-protected Webhook channel and optional local UI login lock.
- Guided provider setup with local config saving, setup checks, and live API connection tests.

### Changed

- Reworked the Web UI into a responsive three-pane agent workspace with Light and Dark themes.
- Improved Auto and Multi-role routing visibility, model metadata, progress heartbeats, and cancellation.
- Unified package, backend, and UI versions at `0.2.0`.
- Removed retired DeepSeek model aliases from the setup and per-role model pickers.

### Fixed

- Fixed authenticated Streamable HTTP MCP connections for the current MCP SDK client API.
- Fixed stale running states, HTML link handling, preview controls, session restoration, and display settings.

### Security

- API keys and integration secrets stay in the local `.env`; registries retain environment variable names only.
- Workspace paths are confined to the configured root, previews are sandboxed, and risky MCP tools require approval by default.
- The Web UI still defaults to loopback-only access. Enable the local login lock before exposing it to another device.

[0.2.0]: https://github.com/RyosukeSAMA/github-ai/releases/tag/v0.2.0
