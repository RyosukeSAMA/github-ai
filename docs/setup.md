# Setup & Configuration Guide

This is the practical "how do I actually get Pantheon running" guide. If anything is unclear, please open an issue.

## 1. Requirements

- **Python 3.10+** (3.11 recommended)
- **pip** or **poetry** or **uv**
- **API keys** for at least one provider:
  - `OPENAI_API_KEY` (for Athena, Apollo by default)
  - `ANTHROPIC_API_KEY` (for Hermes, Hephaestus by default)
  - or a local **Ollama** install

## 2. Installation

### Option A: pip (simplest)

```bash
git clone https://github.com/RyosukeSAMA/github-ai.git
cd github-ai
pip install -e ".[dev]"
```

### Option B: poetry

```bash
poetry install
poetry shell
```

### Option C: uv (fast)

```bash
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
      model: claude-sonnet-4-20250514      # change if you want
      provider: anthropic
      temperature: 0.1                     # lower = more deterministic
    athena:
      model: gpt-4o
      provider: openai
      temperature: 0.3
```

You can:
- Change the **model** for any role (e.g. switch Hephaestus to `gpt-4o`).
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

# Start the Web UI
pantheon web
# Open http://127.0.0.1:8000
```

## 6. Common configuration scenarios

### "I only have an OpenAI key"

Edit `config/pantheon.yaml` to point Hermes and Hephaestus at OpenAI:

```yaml
pantheon:
  hermes:
    model: gpt-4o
    provider: openai
  roles:
    hephaestus:
      model: gpt-4o
      provider: openai
    athena:
      model: gpt-4o
      provider: openai
    apollo:
      model: gpt-4o
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

### "I want to mix: Anthropic for code, OpenAI for research, Suno for music"

Set each role's `provider` and `model` independently in `pantheon.yaml`. The framework doesn't care.

### "I want to add a custom base URL (e.g. Azure OpenAI, OpenRouter)"

```yaml
llm_providers:
  openai:
    api_key: ${OPENAI_API_KEY}
    base_url: https://my-proxy.example.com/v1
```

## 7. Troubleshooting

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

## 8. Running tests

```bash
pytest                          # all tests
pytest -v                       # verbose
pytest tests/test_roles.py -v   # one file
pytest --cov=pantheon           # with coverage
```

Tests do **not** require API keys (they use a mock LLM client).

## 9. What's next?

- Read [architecture.md](architecture.md) to understand how it all fits together.
- Read the role docs in [roles/](roles/) to understand each god.
- See [faq.md](faq.md) for common questions.
- Add your own role — see [CONTRIBUTING.md](../CONTRIBUTING.md).
