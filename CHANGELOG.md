# Changelog

All notable changes to Pantheon are documented in this file.

## Unreleased

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
