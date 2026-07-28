# Setup & Configuration Guide

This is the practical "how do I actually get Pantheon running" guide. If anything is unclear, please open an issue.

## 1. Requirements

- **Python 3.10+** (3.11 recommended)
- **pip** or **uv**
- **API keys** for at least one provider:
  - `OPENAI_API_KEY` (for OpenAI-backed roles)
  - `ANTHROPIC_API_KEY` (for Claude-backed roles)
  - `DEEPSEEK_API_KEY` (for DeepSeek's OpenAI-compatible endpoint)
  - or a local **Ollama** install

## 2. Installation

### Option A: pip with a virtual environment (recommended)

```bash
git clone https://github.com/RyosukeSAMA/github-ai.git
cd github-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### Option B: uv (fast)

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## 3. Configure API keys

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OPENAI_API_KEY=sk-...your-real-key...
ANTHROPIC_API_KEY=sk-ant-...your-real-key...
```

The `.env` file is in `.gitignore` and will **not** be committed.

## 4. Configure roles

```bash
cp config/pantheon.example.yaml config/pantheon.yaml
```

Open `config/pantheon.yaml`. The interesting section is under `pantheon.roles`:

```yaml
pantheon:
  roles:
    hephaestus:
      model: claude-sonnet-4-6             # change if you want
      provider: anthropic
      temperature: 0.1                     # lower = more deterministic
    athena:
      model: gpt-5.5
      provider: openai
      temperature: 0.3
```

You can:
- Change the **model** for any role (e.g. switch everything to `deepseek-v4-flash`).
- Change the **provider** (e.g. use Anthropic for everything).
- Change the **temperature** (lower = more focused, higher = more creative).
- Set `enabled: false` to disable a role.

To use a role for which you don't have the right key, set its `enabled: false` to avoid noisy warnings.

## 5. Verify

```bash
# Quick CLI test (requires at least one provider's key)
pantheon ask --role hephaestus "Write a hello world in Python"

# List enabled roles
pantheon roles

# List built-in and local skills
pantheon skills

# Explicitly invoke one skill
pantheon ask --skill fix-and-verify "Fix the null handling bug and verify it"

# Start the Web UI
pantheon web
# Open http://127.0.0.1:8000
```

The default host is loopback-only. The Web UI includes file writing and terminal
execution, so enable `Settings -> Security` and restrict network access before
starting it with `--host 0.0.0.0` or exposing it through a remote server.

## 6. Skills

Pantheon loads six built-in `SKILL.md` workflows and any local skills stored in
`.pantheon/skills/`. In the Web UI, open `Settings -> Integrations -> Skills`,
then click `Use` or enter:

```text
/skill research-with-sources Compare the latest supported models
```

Role-specific Skills route directly to their assigned god in Auto mode.
Shared/council Skills remain available to Hermes for multi-role planning.
Built-ins are read-only but can be disabled. Skills created in the UI are local
folders and can be edited or deleted.

## 7. Common configuration scenarios

### "I only have an OpenAI key"

Edit `config/pantheon.yaml` to point Hermes and Hephaestus at OpenAI:

```yaml
pantheon:
  hermes:
    model: gpt-5.5
    provider: openai
  roles:
    hephaestus:
      model: gpt-5.5
      provider: openai
    athena:
      model: gpt-5.5
      provider: openai
    apollo:
      model: gpt-5.4-mini
      provider: openai
```

### "I want to run everything locally with Ollama"

1. Install [Ollama](https://ollama.com/) and pull a model:
   ```bash
   ollama pull llama3.1
   ```
2. Edit `config/pantheon.yaml`:
   ```yaml
   llm_providers:
     ollama:
       base_url: http://localhost:11434
       enabled: true

   pantheon:
     hermes:
       model: llama3.1
       provider: ollama
     roles:
       hephaestus:
         model: llama3.1
         provider: ollama
       # ... etc
   ```

### "I want different providers for different gods"

Set each role's registered `provider` and `model` independently in
`pantheon.yaml`. The provider must be one Pantheon currently supports: OpenAI,
Anthropic, DeepSeek through the OpenAI-compatible adapter, or Ollama.

Apollo can prepare creative direction, prompts, lyrics, and storyboards with a
chat model. Generating an actual image, audio track, or video requires a
separately configured MCP tool or other integration; Pantheon does not include
a built-in Suno provider.

### "I want to add a custom base URL (e.g. Azure OpenAI, OpenRouter)"

```yaml
llm_providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://my-proxy.example.com/v1
```

## 8. Troubleshooting

### "No API key for provider 'openai'"

You're calling a role whose `provider` is OpenAI but `OPENAI_API_KEY` isn't set in your shell or `.env`. Fix one of:

```bash
# Option 1: export in your shell
export OPENAI_API_KEY=sk-...

# Option 2: put in .env (recommended)
echo "OPENAI_API_KEY=sk-..." >> .env
```

### "Role 'X' wants provider 'Y' but it's not configured"

Either set the provider's API key, or change the role's `provider` in `pantheon.yaml`.

### "404 from API"

Wrong `base_url`, or the model name is wrong for your provider. Double-check.

### "Rate limit / 429"

Hit your provider's rate limit. Either slow down, upgrade your plan, or use a different provider for that role.

### CLI / Web can't find `pantheon`

You didn't install with `pip install -e .` (or equivalent). Re-run that step.

### Tests fail with "openai / anthropic not installed"

`pip install -e ".[dev]"` should pull these in. If not, `pip install openai anthropic`.

## 9. Running tests

```bash
pytest                          # all tests
pytest -v                       # verbose
pytest tests/test_roles.py -v   # one file
pytest --cov=pantheon           # with coverage
```

Tests do **not** require API keys (they use a mock LLM client).

## 10. What's next?

- Read [architecture.md](architecture.md) to understand how it all fits together.
- Read the role docs in [roles/](roles/) to understand each god.
- See [faq.md](faq.md) for common questions.
- Add your own role — see [CONTRIBUTING.md](../CONTRIBUTING.md).
