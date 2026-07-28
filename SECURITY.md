# Security Policy

Pantheon is a local-first, alpha-stage multi-agent workspace. It can store API
credentials and, when explicitly enabled, operate files, run terminal commands,
connect to MCP servers, and accept webhook requests. Treat every enabled
integration as code with the same access as the local Pantheon process.

## Supported Versions

| Version | Supported |
|---|---|
| `0.2.x` | Yes |
| `0.1.x` and earlier | No |

Security fixes are applied to the latest release line. Please reproduce a
report against the latest release before submitting it when possible.

## Reporting a Vulnerability

Do not open a public Issue or Discussion for a suspected vulnerability.
Use [GitHub private vulnerability reporting](https://github.com/RyosukeSAMA/github-ai/security/advisories/new)
so the report and any proof of concept remain private.

Include:

- the affected Pantheon version and commit, if known;
- operating system and Python version;
- the minimum steps needed to reproduce the issue;
- the security impact and the boundary that was crossed;
- sanitized logs or a proof of concept.

Remove API keys, webhook tokens, session cookies, private prompts, local paths,
and personal data before attaching logs. The maintainer will acknowledge valid
reports on a best-effort basis and coordinate a fix and disclosure timeline with
the reporter.

## Security-Sensitive Areas

Reports are especially useful when they involve:

- API key, webhook token, or session secret disclosure;
- authentication or authorization bypass;
- access to files outside the configured workspace;
- unintended command execution or command-confirmation bypass;
- unsafe MCP tool authorization, credential handling, or network access;
- HTML Preview sandbox escape or script execution in the Pantheon UI;
- cross-site request forgery, server-side request forgery, or webhook spoofing.

## Deployment Boundaries

- Keep the Web UI bound to `127.0.0.1` unless remote access is intentional.
- Enable the local login lock before allowing another device to reach the UI.
- Put remote deployments behind TLS, network access controls, and a trusted
  reverse proxy. The local login lock is not a multi-user security boundary.
- Keep `.env`, `.pantheon/`, generated workspaces, and logs out of version
  control. Never paste live credentials into Issues or Discussions.
- Review MCP servers and Skills before enabling them, restrict them to the gods
  that need them, and keep approval enabled for risky tools.
- Run Pantheon as a non-privileged user inside a dedicated workspace.

Model output quality, commands a user intentionally approves, and exposure
caused by disabling the documented local-only safeguards are not considered
security vulnerabilities by themselves.
