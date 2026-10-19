# Pantheon Beginner Setup Guide

**English** | [简体中文](setup.zh-CN.md)

This guide starts with a computer that does not yet have Python, Git, or Pantheon. Follow one operating-system path from top to bottom. Do not skip ahead when a version check fails.

You are finished when all four statements are true:

- `pantheon --version` prints a version.
- <http://127.0.0.1:8000/> opens in your browser.
- **Settings → Setup → Test API** succeeds for one provider.
- A New Chat returns a model response and Activity shows the task as complete.

## 1. Choose how Pantheon will run models

Pantheon itself is free and runs on your computer. Model execution needs one of these:

| Choice | What you need | Best for |
|---|---|---|
| Cloud provider | An API key from OpenAI, Anthropic, or DeepSeek | Easiest first installation |
| Local Ollama | Ollama plus enough memory and disk for the selected model | Users who want local inference |

An account or chat subscription is not necessarily an API account. In particular, a ChatGPT subscription does not include OpenAI API credits. Create and fund an API account in the official console of the provider you choose.

If you do not have an API key yet, use the provider's own instructions:

| Provider | Where to start |
|---|---|
| OpenAI | [API quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request) |
| Anthropic | [Claude API key instructions](https://platform.claude.com/docs/en/manage-claude/authentication) |
| DeepSeek | [DeepSeek Platform](https://platform.deepseek.com/) |
| Ollama | [Official download](https://ollama.com/download) (no cloud API key needed for a local model) |

Create a regular project or personal API key, copy it once, and paste it into Pantheon's **Settings → Setup** page in step 6. Provider billing and available models depend on that account.

Start with one provider. Pantheon can assign different providers to different agents later.

## 2. Check that your computer is supported

| System | Supported path | Python |
|---|---|---|
| macOS 13 or newer | Terminal and Homebrew | 3.11 or 3.12 recommended |
| Ubuntu 22.04 or 24.04 | Native Terminal | 3.10-3.12 |
| Windows 11 | Native PowerShell | 3.11 or 3.12 |
| Windows + WSL2 | Optional Ubuntu environment | 3.10–3.12 |

Pantheon CI tests Python 3.10, 3.11, and 3.12 on Ubuntu. Python 3.13 and newer may work, but are not yet part of the tested support range.

After preparing the prerequisites below, install with one command.

**macOS / Ubuntu:**

```bash
curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.sh | bash
```

**Native Windows 11 PowerShell:**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.ps1 | iex"
```

Open a new terminal after installation, run `pantheon web`, and continue at section 6. Windows needs neither WSL nor a virtual environment activation script. The default checkout is `%LOCALAPPDATA%\Pantheon\app` on Windows and `~/github-ai` on macOS/Ubuntu. The installer selects the latest stable release, prepares and verifies a separate permanent environment, then promotes the checkout and `.venv` entry point. It adds a launcher to the current user's PATH.


## 3. Prepare the operating system

Use only the section for your computer.

### macOS 13 or newer

1. Open **Terminal** from Applications → Utilities.
2. Install Apple's command-line tools:

   ```bash
   xcode-select --install
   ```

   A system window may open. Complete it before continuing. If macOS says the tools are already installed, continue.

3. Check whether Homebrew is installed:

   ```bash
   brew --version
   ```

4. If the command is not found, install Homebrew:

   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   Follow the final Homebrew instructions if it asks you to add `brew` to your shell path, then close and reopen Terminal.

5. Install Python and Git:

   ```bash
   brew install python@3.12 git
   python3.12 --version
   git --version
   ```

Continue only when `python3.12` reports Python 3.12 and Git prints a version.

### Ubuntu 22.04 or 24.04

1. Open **Terminal**.
2. Install Git, Python, pip, and virtual-environment support:

   ```bash
   sudo apt update
   sudo apt install -y git curl python3 python3-venv python3-pip
   python3 --version
   git --version
   ```

Continue only when Python reports 3.10-3.12 and Git prints a version.

### Windows 11 with native PowerShell

In a regular PowerShell window, prepare prerequisites:

```powershell
winget install --id Git.Git -e --source winget
winget install --id Python.Python.3.12 -e --scope user
```

Finish the installer prompts, open a new PowerShell window, and check:

```powershell
git --version
py -3.12 --version
```

Run the PowerShell installer in section 2, open a new window, and run `pantheon --version` and `pantheon web`. Continue at section 6. No `source .venv/bin/activate` is needed. If WinGet is missing, use [Git for Windows](https://git-scm.com/install/windows) and [Python for Windows](https://www.python.org/downloads/windows/), enabling the Python launcher.

### Windows with WSL2 (optional)

This optional path is for users choosing WSL. Run the Linux commands below in Ubuntu; native Windows users can use the PowerShell installation above.

1. Open **PowerShell as Administrator**.
2. Install WSL2 and Ubuntu:

   ```powershell
   wsl --install -d Ubuntu-24.04
   ```

3. Restart Windows when requested.
4. Open **Ubuntu 24.04** from the Start menu and create the Linux username and password it requests. The password is not displayed while you type; this is normal.
5. In the Ubuntu window, run:

   ```bash
   sudo apt update
   sudo apt install -y git curl python3 python3-venv python3-pip
   python3 --version
   git --version
   ```

Keep the project in the Linux home folder, such as `/home/your-name/github-ai`. Avoid `/mnt/c/...`, which is slower and can cause file-permission problems.

If PowerShell says `Ubuntu-24.04` is unavailable, run `wsl --list --online` and choose a listed Ubuntu 22.04 or 24.04 distribution. See [Microsoft's WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) for Windows-specific errors.

## 4. Download and install Pantheon

This manual source path applies to macOS, Ubuntu and WSL. One-line installer users have already installed dependencies and can continue at section 5.

1. Go to your home folder and download the repository:

   ```bash
   cd ~
   git clone https://github.com/RyosukeSAMA/github-ai.git
   cd github-ai
   ```

2. Create an isolated Python environment.

   On macOS:

   ```bash
   python3.12 -m venv .venv
   ```

   On Ubuntu or WSL:

   ```bash
   python3 -m venv .venv
   ```

   Then activate the environment:

   ```bash
   source .venv/bin/activate
   ```

   Your prompt should now begin with `(.venv)`. This keeps Pantheon's packages separate from the rest of the computer.

3. Install Pantheon:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e .
   pantheon --version
   ```

Expected result:

```text
pantheon 0.3.1
```

A newer version number is also valid. Do not use `sudo pip install`.

## 5. Start the Web UI

One-line installer users can open a new terminal; manual source users should keep `(.venv)` active. Run:

```bash
pantheon web
```

A successful launch includes a line similar to:

```text
Uvicorn running on http://127.0.0.1:8000
```

Keep this terminal window open. Open <http://127.0.0.1:8000/> in a current version of Chrome, Edge, Firefox, or Safari.

`127.0.0.1` means only this computer can reach Pantheon. Do not change the host to `0.0.0.0` during initial setup.

## 6. Configure a provider and assign role models

1. Open **Settings → Setup**. Select DeepSeek, OpenAI, Anthropic, or a locally running Ollama.
2. Enter that provider's key and keep the official Base URL. Choose a model for the connection test.
3. Click **Test API**. This sends one short request and may incur a charge. **API connected** confirms that exact key, endpoint and model combination.
4. Choose private `.env` or available **System credential storage**, then **Save provider connection**. This does not change any role's model or make another API call.
5. Open **Models → New chat defaults**. Under **Use one model for all AI roles**, select the same provider and model, then **Apply to all AI roles → Save new chat defaults**.
6. Create **New Chat**. All four AI roles can use this single connection; Chronos needs no model.

Multiple providers are optional. Add each provider independently in Setup, then assign providers/models per role in Models. **Current chat only** saves choices automatically for that conversation. **New chat defaults** requires an explicit save and affects future chats; existing chats retain their assignments. Role skills are independent of the chosen provider. Costs depend on prices, tokens and calls, not simply the number of connected providers. Review usage and budgets in Info.

Use **Test this role** to verify the role's selected model. Testing one model does not establish access to all models at that provider. Evidence expires after 24 hours. Catalog visibility is separate from API verification. Check setup validates local configuration only.

Setup shows the actual config and credential paths. Existing source installations keep local `.env` and `config/pantheon.yaml`; new workspaces default to user application data. System credential storage uses a supported OS keyring; `pantheon credentials --migrate` explicitly migrates saved API keys and channel tokens, verifies them, then removes dotenv values. Do not paste secrets into issues, screenshots, or chat messages.

If the test fails, do not save yet. Use the matching troubleshooting entry below.

## 7. Complete the first task

1. Select **New Chat**.
2. Leave **Auto** selected.
3. Send:

   ```text
   Write a Python hello world example and explain how to run it.
   ```

The installation is working when:

- a model answer appears;
- Activity shows Hermes and the selected agent;
- the run reaches a completed state without an API error.

Press `Control-C` in the terminal to stop Pantheon.

## 8. Start Pantheon on another day

Open Terminal (or Ubuntu on Windows) and run:

```bash
cd ~/github-ai
source .venv/bin/activate
pantheon web
```

Then open <http://127.0.0.1:8000/>. If you cloned the repository somewhere else, use that path after `cd`.

## 9. Optional: start automatically after login

First complete one successful manual launch. Then macOS and native Linux users can run:

```bash
pantheon service install
pantheon service status
```

Maintenance commands:

```bash
pantheon service restart
pantheon service logs
pantheon service stop
pantheon service uninstall
```

The service uses your selected workspace and installation. macOS uses a LaunchAgent, Linux uses user systemd, and Windows uses a current-user Startup shortcut and windowless runner, without administrator rights. Windows jobs run after login; WSL needs systemd for background service management. Stop a manually running Web instance before installing the service.

## 10. Optional: use Ollama without a cloud API key

1. [Install Ollama](https://ollama.com/download) and start it. On WSL, install the Linux version inside the same Ubuntu environment where Pantheon runs.
2. Download a model:

   ```bash
   ollama pull llama3.1
   ollama list
   ```

3. Start Pantheon and open **Settings → Setup**.
4. Select **Ollama** and keep `http://localhost:11434` as the Base URL.
5. Select or enter the model ID shown by `ollama list`.
6. Run **Test API → Save provider connection**. In **Models → New chat defaults**, select Ollama and the downloaded model, then **Apply to all AI roles → Save new chat defaults**. Create a new chat to use it.

Ollama model downloads can be several gigabytes. Performance depends on the model and computer hardware.

## 11. Update Pantheon

Wait for active tasks to finish and stop a manually running Web instance, then run:

```text
pantheon update
pantheon update --rollback
```

Use the second command only when restoring the previous installation. Updates prepare and verify a new environment, create an offline data backup, and then promote code. A background service belonging to this installation is paused and restarted. If startup or health verification fails, the previous code and environment are restored. Active tasks and uncommitted source changes block promotion. Config and current workspace data are preserved. Rollback switches program versions; it does not silently revert data formats. Use the offline backup if downgrading across incompatible formats.

Older versions without `update` can use this on macOS/Ubuntu:

```bash
curl -fsSL https://raw.githubusercontent.com/RyosukeSAMA/github-ai/main/scripts/install.sh | PANTHEON_UPDATE=1 bash
```

On Windows set `$env:PANTHEON_UPDATE='1'` before running the native installer. Development source checkouts can continue to use `git pull --ff-only` and `python -m pip install -e .`; do not apply release updates to uncommitted development work.

The Web UI checks published GitHub Releases about every six hours and displays an upgrade banner. Settings → Info includes Check now, a Release link and the update command. Merged code without a Release does not trigger an alert; the page never installs a version automatically.

`pantheon doctor` shows real workspace, state, config and credential paths. `pantheon backup /path/to/backup.zip` exports an offline workspace backup after stopping the service and waiting for CLI tasks. `pantheon restore /path/to/backup.zip` restores it and retains a rollback copy. System keyring secrets are not in ordinary backups; configure credentials again on another computer. Info's Export backup/Import backup controls export conversation JSON, not the entire workspace.

Info's API usage shows provider-reported tokens. Budgets limit task and rolling 24-hour attempts and output tokens; 0 disables a limit. Optional model rates enable local cost estimates; unpriced calls have unknown cost. CLI uses `pantheon budgets` and SDK uses `p.services.budget`. Estimates are not provider invoices.

## 12. Troubleshooting

### `python3: command not found`

Return to the operating-system preparation section. Install Python, close the terminal, and reopen it. On macOS check `python3.12 --version`; on Ubuntu or WSL check `python3 --version`.

### Python is older than 3.10

Do not continue with that interpreter. On macOS, run `brew install python@3.12`. On Ubuntu, use Ubuntu 22.04/24.04 or install a supported Python before creating `.venv`.

### `No module named venv` or virtual-environment creation fails on Ubuntu

```bash
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
```

### `source: no such file or directory: .venv/bin/activate`

Make sure you are inside the repository. On macOS, recreate the environment with:

```bash
cd ~/github-ai
python3.12 -m venv .venv
source .venv/bin/activate
```

On Ubuntu or WSL, use:

```bash
cd ~/github-ai
python3 -m venv .venv
source .venv/bin/activate
```

### `pantheon: command not found`

Activate the environment and install the package again:

```bash
cd ~/github-ai
source .venv/bin/activate
python -m pip install -e .
pantheon --version
```

### Port 8000 is already in use

Start on another port:

```bash
pantheon web --port 8001
```

Then open <http://127.0.0.1:8001/>.

### The browser cannot open Pantheon

Confirm the terminal is still running and shows no traceback. Use the exact URL printed by Uvicorn. On WSL, current Windows versions normally forward `127.0.0.1`; if they do not, run `wsl --shutdown` in PowerShell, reopen Ubuntu, and start Pantheon again.

### `401`, `authentication`, or `invalid API key`

The API key is missing, expired, copied incorrectly, or belongs to a different provider. Create a key in the selected provider's official API console, paste it again, and rerun **Test API**. A consumer chat subscription is not an API key.

### `404` or `model not found`

The model is unavailable to the account or does not match the selected provider. Select **Refresh models**, choose an available model, and rerun **Test API**. Keep the official Base URL unless you intentionally use a compatible gateway.

### `429`, rate limit, or quota error

The provider rejected the request because of account quota, billing, or rate limits. Check that provider's API console or select another configured provider.

### The Web UI opens, but a task says another agent has no key

Open **Models** and review the affected role. Add its provider key in **Setup**, or use **Apply to all AI roles** to assign your existing provider/model to every AI role. Saving a connection alone does not change role assignments.

### Reset the local setup

Stop Pantheon and back up the files first. Then rename them:

```bash
cd ~/github-ai
mv .env .env.backup 2>/dev/null || true
mv config/pantheon.yaml config/pantheon.yaml.backup 2>/dev/null || true
pantheon web
```

Open Setup and configure the provider again.

### Get useful diagnostics

In the Web UI, open **Settings → Info → Copy diagnostics**. It masks saved API keys. For service installations, run `pantheon service logs`.

If the problem remains, open a GitHub issue and include the operating system, `python3 --version`, `pantheon --version`, the exact failing command, and the sanitized error. Never include an API key.

## 13. Uninstall

Stop and remove the optional service first:

```bash
cd ~/github-ai
source .venv/bin/activate
pantheon service uninstall
```

Back up `.env`, `config/pantheon.yaml`, and `.pantheon/` if you need their settings, schedules, or memory. Then leave the folder and delete it using the file manager. Deleting the repository also deletes the local virtual environment and Pantheon data stored inside it.

## 14. Advanced manual configuration

The browser Setup flow is recommended for new users. To configure files manually:

```bash
cd ~/github-ai
cp .env.example .env
cp config/pantheon.example.yaml config/pantheon.yaml
```

Add keys to `.env`, then set matching providers, models, and Base URLs in `config/pantheon.yaml`. Never commit either file.

Pantheon refreshes configured official model catalogs in the background and caches results in `.pantheon/model_catalog.json`. After a successful refresh, the model menus show only models returned for that API key. A saved model that is absent from the list remains visible with a warning so you can test or change it; refreshing never rewrites your saved configuration. A model-list result alone does not prove that a generation request will succeed, so use **Test API** before saving a new choice. If refresh fails, Pantheon keeps the cached list or the built-in recommendations.

Official account catalogs synchronize at startup and hourly, with failed attempts retried every five minutes. Open pages pick up changes every minute and when refocused, preserving Setup drafts. Without OpenAI or Anthropic keys, public official recommendations still synchronize every six hours; these do not claim account access. Add the matching API key to query the account catalog. Setup shows sync time and failures. Set `PANTHEON_MODEL_DOCS_SYNC=0` to disable public-document synchronization for offline use.

## 15. Contributor installation

Regular users should install only `-e .`. Contributors can add development or browser-test dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[e2e]"
playwright install chromium
pytest
pytest e2e --browser chromium
```

Normal automated tests use mock clients and do not require API keys. Live provider diagnostics are opt-in and can incur a provider charge.

### Remote access and terminal permissions

Start locally and enable **Settings → Security** before binding with `--host 0.0.0.0`. Remote binds refuse to start without a configured login. Set `PANTHEON_ALLOWED_HOSTS` to a comma-separated list of the IP addresses or domain names used in your browser. Cross-origin UI requests are rejected. Remote terminal execution defaults to disabled; enable it only when intended with `PANTHEON_TERMINAL_ENABLED=true` before startup. Set the same variable to `false` to disable terminal execution locally. Restart after changing these server settings.

Stopping a Web task prevents later agent/tool calls and synthesis. A synchronous model request already accepted by the provider may finish and be billed. Model requests have a 120-second timeout; budget-managed clients disable SDK retries. Web execution has a 10-minute budget. Plans have at most eight steps, bounded recovery is configurable, and long context is summarized with an explicit excerpt fallback. Large tasks may need to be split into smaller requests.


After installation, see [media, budgets and task recovery](workflows.md) and [chat platform setup](channels.md).
