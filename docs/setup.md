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

Start with one provider. Pantheon can assign different providers to different agents later.

## 2. Check that your computer is supported

| System | Supported path | Python |
|---|---|---|
| macOS 13 or newer | Terminal and Homebrew | 3.11 or 3.12 recommended |
| Ubuntu 22.04 or 24.04 | Native Terminal | 3.10-3.12 |
| Windows 11 | WSL2 running Ubuntu 22.04 or 24.04 | Ubuntu's Python |
| Native Windows PowerShell | Not currently supported | — |

Pantheon CI tests Python 3.10, 3.11, and 3.12 on Ubuntu. Python 3.13 and newer may work, but are not yet part of the tested support range.

For a cloud provider, 4 GB RAM and about 1 GB of free disk space are sufficient for Pantheon and its Python environment. Local Ollama models need additional memory and disk; check the requirements of the model you plan to download.

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
   sudo apt install -y git python3 python3-venv python3-pip
   python3 --version
   git --version
   ```

Continue only when Python reports 3.10-3.12 and Git prints a version.

### Windows 11 with WSL2

Pantheon currently uses Linux commands on Windows. Do not run the later commands in PowerShell.

1. Open **PowerShell as Administrator**.
2. Install WSL2 and Ubuntu:

   ```powershell
   wsl --install -d Ubuntu
   ```

3. Restart Windows when requested.
4. Open **Ubuntu** from the Start menu and create the Linux username and password it requests. The password is not displayed while you type; this is normal.
5. In the Ubuntu window, run:

   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-venv python3-pip
   python3 --version
   git --version
   ```

Keep the project in the Linux home folder, such as `/home/your-name/github-ai`. Avoid `/mnt/c/...`, which is slower and can cause file-permission problems.

## 4. Download and install Pantheon

These commands are the same on macOS, Ubuntu, and the Ubuntu window in WSL.

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
pantheon 0.2.1
```

A newer version number is also valid. Do not use `sudo pip install`.

## 5. Start the Web UI

With `(.venv)` still visible, run:

```bash
pantheon web
```

A successful launch includes a line similar to:

```text
Uvicorn running on http://127.0.0.1:8000
```

Keep this terminal window open. Open <http://127.0.0.1:8000/> in a current version of Chrome, Edge, Firefox, or Safari.

`127.0.0.1` means only this computer can reach Pantheon. Do not change the host to `0.0.0.0` during initial setup.

## 6. Configure one provider in the browser

1. Open **Settings**.
2. Open **Setup**.
3. Select the provider for which you have an API key: DeepSeek, OpenAI, or Anthropic. Select Ollama only if it is already running locally.
4. Keep the official Base URL shown by Pantheon.
5. Paste the API key from that provider's official console.
6. Select a model.
7. Select **Test API**. This checks the values currently in the form, makes a small real request, and may incur a small provider charge.
8. When the test succeeds, select **Save local config**.
9. Select **Check setup**. This checks the saved local configuration; confirm that every enabled agent is ready.

Pantheon stores the key in the repository's local `.env` file and the provider/model choices in `config/pantheon.yaml`. Both are ignored by Git. Do not paste API keys into GitHub issues, screenshots, or chat messages.

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

The service uses the current repository and virtual environment. macOS uses a per-user LaunchAgent; Linux uses user systemd. WSL users should keep using the manual start command unless systemd is enabled in WSL.

## 10. Optional: use Ollama without a cloud API key

1. Install Ollama from its official website and start it.
2. Download a model:

   ```bash
   ollama pull llama3.1
   ollama list
   ```

3. Start Pantheon and open **Settings → Setup**.
4. Select **Ollama** and keep `http://localhost:11434` as the Base URL.
5. Select or enter the model ID shown by `ollama list`.
6. Run **Check setup**, **Test API**, and **Save local config**.

Ollama model downloads can be several gigabytes. Performance depends on the model and computer hardware.

## 11. Update Pantheon

Stop Pantheon with `Control-C`, then run:

```bash
cd ~/github-ai
source .venv/bin/activate
git pull --ff-only
python -m pip install -e .
pantheon --version
```

If an update changes backend configuration, start `pantheon web` again after updating.

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

Setup must configure every enabled chat agent, or the unused role must be disabled. Return to **Settings → Setup**, review the agent status list, and save a provider/model combination available to all enabled roles.

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

In the Web UI, open **Settings → Support → Copy diagnostics**. It masks saved API keys. For service installations, run `pantheon service logs`.

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

Pantheon refreshes configured official model catalogs in the background and caches results in `.pantheon/model_catalog.json`. Refreshing the list never changes a saved model automatically.

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
