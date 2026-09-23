#!/usr/bin/env bash
# Install Pantheon from its public repository into an isolated local venv.
set -euo pipefail

say_error() {
  printf 'Pantheon installer: %s\n' "$1" >&2
  exit 1
}

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) say_error 'Use macOS, Linux, or Ubuntu inside WSL2. Native Windows is not supported.' ;;
esac

if [ "$(id -u)" -eq 0 ]; then
  say_error 'Run this as your normal user, without sudo.'
fi

if ! command -v git >/dev/null 2>&1 || ! git --version >/dev/null 2>&1; then
  if [ "$(uname -s)" = Darwin ]; then
    say_error 'Git is required. Run xcode-select --install, finish the prompt, then retry.'
  fi
  say_error 'Git is required. On Ubuntu run: sudo apt update && sudo apt install -y git'
fi

python_cmd=''
for candidate in python3.12 python3.11 python3.10 python3; do
  if command -v "$candidate" >/dev/null 2>&1 &&
    "$candidate" -c 'import sys; raise SystemExit(not ((3, 10) <= sys.version_info[:2] <= (3, 12)))' >/dev/null 2>&1; then
    python_cmd="$candidate"
    break
  fi
done

if [ -z "$python_cmd" ]; then
  if [ "$(uname -s)" = Darwin ]; then
    say_error 'Python 3.10-3.12 is required. Install Homebrew, run brew install python@3.12, then retry.'
  fi
  say_error 'Python 3.10-3.12 is required. On Ubuntu run: sudo apt update && sudo apt install -y python3 python3-venv python3-pip'
fi

install_dir="${PANTHEON_INSTALL_DIR:-$HOME/github-ai}"
repo_url="${PANTHEON_REPO_URL:-https://github.com/RyosukeSAMA/github-ai.git}"
case "$install_dir" in
  /*) ;;
  *) say_error 'PANTHEON_INSTALL_DIR must be an absolute path.' ;;
esac
if [ -e "$install_dir" ]; then
  say_error "Destination already exists: $install_dir. Existing files were left untouched."
fi
if [ ! -d "$(dirname "$install_dir")" ]; then
  say_error "Parent directory does not exist: $(dirname "$install_dir")"
fi

printf 'Installing Pantheon into %s with %s...\n' "$install_dir" "$python_cmd"
git clone --depth 1 "$repo_url" "$install_dir"
if ! "$python_cmd" -m venv "$install_dir/.venv"; then
  say_error 'Could not create the virtual environment. On Ubuntu install python3-venv, then remove the incomplete destination and retry.'
fi
"$install_dir/.venv/bin/python" -m pip install --upgrade pip
"$install_dir/.venv/bin/python" -m pip install -e "$install_dir"
"$install_dir/.venv/bin/pantheon" --version

printf '\nInstallation complete. Start the local Web UI with:\n  cd %q && .venv/bin/pantheon web\n' "$install_dir"
printf 'Then open http://127.0.0.1:8000/ and configure a model provider in Settings → Setup.\n'
