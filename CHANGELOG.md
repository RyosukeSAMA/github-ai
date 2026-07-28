# Changelog

All notable changes to Pantheon are documented in this file.

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
